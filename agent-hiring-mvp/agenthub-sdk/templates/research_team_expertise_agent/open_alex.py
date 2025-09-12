import os
import requests
from urllib.parse import quote
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Author:
    """Data class representing an author from OpenAlex."""
    id: str
    display_name: str
    orcid: Optional[str]
    works_count: Optional[int]
    cited_by_count: Optional[int]
    last_known_institution: Optional[Dict[str, Any]]
    h_index: Optional[int]
    i10_index: Optional[int]


@dataclass
class Publication:
    """Data class representing a publication from OpenAlex."""
    id: str
    doi: Optional[str]
    title: str
    year: Optional[int]
    cited_by_count: int
    venue: Optional[Dict[str, Any]]
    authors: List[str]
    abstract: Optional[str]
    type: Optional[str]


@dataclass
class AuthorWorksSummary:
    """Data class representing a summary of an author's works."""
    author: Author
    total_citations: int
    works: List[Publication]
    works_count: int


@dataclass
class AuthorMetrics:
    """Data class representing comprehensive author metrics from OpenAlex."""
    id: str
    display_name: str
    orcid: Optional[str]
    works_count: int
    cited_by_count: int
    h_index: Optional[int]
    i10_index: Optional[int]
    impact_factor: Optional[float]


class OpenAlexError(Exception):
    """Custom exception for OpenAlex API errors."""
    pass


class OpenAlexClient:
    """
    A well-designed client for interacting with the OpenAlex API.
    
    Provides methods to search for authors, get publication information,
    and retrieve citation data with proper error handling and rate limiting.
    """
    
    BASE_URL = "https://api.openalex.org"
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the OpenAlex client.
        
        Args:
            email: Contact email for the "polite pool" (required for production use)
            api_key: Optional API key for premium features
        """
        self.email = email or os.getenv("OPENALEX_EMAIL", "kourgeorge@gmail.com")
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        
        if not self.email:
            logger.warning("No email provided. This may result in rate limiting.")
        
        self.headers = {
            "User-Agent": f"OpenAlexClient/1.0 (mailto:{self.email})",
            "Accept": "application/json",
        }
        
        logger.info(f"OpenAlex client initialized with email: {self.email}")
    
    def _get_common_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add common parameters to all API requests."""
        common_params = dict(params or {})
        common_params["mailto"] = self.email
        
        if self.api_key:
            common_params["api_key"] = self.api_key
            
        return common_params
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the OpenAlex API with proper error handling.
        
        Args:
            endpoint: API endpoint (e.g., "/authors", "/works")
            params: Query parameters
            
        Returns:
            JSON response from the API
            
        Raises:
            OpenAlexError: If the API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.get(
                url,
                params=self._get_common_params(params),
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            if response.status_code == 403:
                raise OpenAlexError(
                    f"Access denied (403). Ensure your email is properly configured "
                    f"and you're following OpenAlex 'polite pool' guidelines."
                ) from e
            elif response.status_code == 429:
                raise OpenAlexError("Rate limit exceeded. Please wait before making more requests.") from e
            else:
                raise OpenAlexError(f"HTTP {response.status_code} error: {e}") from e
                
        except requests.RequestException as e:
            raise OpenAlexError(f"Request failed: {e}") from e

    def _lookup_institution_id(self, institution_name: str) -> Optional[str]:
        """
        Find an OpenAlex institution ID by display name.
        Tries exact case-insensitive match first; else picks the most 'prominent' (by works_count).
        Returns an OpenAlex institution ID like 'I71267560', or None if not found.
        """
        # Use display_name.search for broad matching
        params = {
            "search": institution_name,
            "per_page": 25,  # search a reasonable set
            "sort": "works_count:desc"
        }
        data = self._make_request("/institutions", params) or {}
        results = data.get("results", [])
        if not results:
            return None

        # Try exact (case-insensitive) match on display_name
        lowered = institution_name.strip().lower()
        exact = next((r for r in results if r.get("display_name", "").strip().lower() == lowered), None)
        picked = exact or results[0]

        # OpenAlex IDs look like "https://openalex.org/I71267560" and also appear as "id": "I71267560" in many libs.
        # Handle both forms defensively.
        raw_id = picked.get("id")
        if isinstance(raw_id, str):
            if raw_id.startswith("I"):
                return raw_id
            # extract terminal ID if URL form
            if raw_id.rsplit("/", 1)[-1].startswith("I"):
                return raw_id.rsplit("/", 1)[-1]

        # Also check 'ids' map if present
        ids_map = picked.get("ids") or {}
        openalex_url = ids_map.get("openalex")
        if isinstance(openalex_url, str) and openalex_url.rsplit("/", 1)[-1].startswith("I"):
            return openalex_url.rsplit("/", 1)[-1]

        return None

    def _query_authors(self, filters: List[str], per_page: int) -> List[Dict[str, Any]]:
        params = {"filter": ",".join(filters), "per_page": per_page}
        try:
            data = self._make_request("/authors", params) or {}
            return data.get("results", []) or []
        except OpenAlexError as e:
            logger.error(f"Failed to query authors: {e}")
            return []

    def search_authors(self, name: str, institution: Optional[str] = None, per_page: int = 25) -> List["Author"]:
        """
        Search authors by name with cascading institution logic (non-deprecated fields):
          1) last_known_institutions.id
          2) affiliations.institution.id
          3) name-only
        """
        per_page = max(1, min(per_page, 200))
        name_filter = f"display_name.search:{name}"

        # If no institution provided, go straight to name-only.
        if not institution:
            results = self._query_authors([name_filter], per_page)
            return [self._parse_author(a) for a in results]

        # Resolve institution to OpenAlex ID (e.g., "I71267560")
        inst_id = self._lookup_institution_id(institution)

        # 1) Try last_known_institutions.id (replacement for deprecated last_known_institution)
        if inst_id:
            results = self._query_authors(
                [name_filter, f"last_known_institutions.id:{inst_id}"],
                per_page,
            )
            if results:
                return [self._parse_author(a) for a in results]

            # 2) Fallback: any historical affiliation with the institution
            results = self._query_authors(
                [name_filter, f"affiliations.institution.id:{inst_id}"],
                per_page,
            )
            if results:
                return [self._parse_author(a) for a in results]

        # 3) Final fallback: name-only
        results = self._query_authors([name_filter], per_page)
        return [self._parse_author(a) for a in results]

    
    def get_author_by_id(self, author_id: str) -> Optional[Author]:
        """
        Get detailed information about an author by their OpenAlex ID.
        
        Args:
            author_id: OpenAlex author ID (can be full URL or just the ID part)
            
        Returns:
            Author object if found, None otherwise
        """
        try:
            # Extract the ID part if a full URL is provided
            author_key = author_id.split("/")[-1]
            data = self._make_request(f"/authors/{quote(author_key)}")
            return self._parse_author(data)
        except OpenAlexError as e:
            logger.error(f"Failed to get author by ID {author_id}: {e}")
            return None
    
    def get_author_works(self, author: Author, page_size: int = 20) -> Iterator[Publication]:
        """
        Get all works for an author with pagination support.
        
        Args:
            author: Author object
            page_size: Number of works per page
            
        Yields:
            Publication objects for each work
        """
        author_key = author.id.split("/")[-1]
        url = "/works"
        params = {
            "filter": f"author.id:{author_key}",
            "per_page": page_size,
            "select": "id,doi,title,publication_year,cited_by_count"
        }
        
        page = 1
        total = None
        
        while True:
            response = self._make_request(url, {**params, "page": page})
            
            if total is None:
                total = response["meta"]["count"]
            
            works = response.get("results", [])
            if not works:
                break
                
            for work_data in works:
                yield self._parse_publication(work_data)
            
            if page * page_size >= total:
                break
            page += 1
    
    def get_author_works_by_id(self, author_id: str, page_size: int = 20) -> Iterator[Publication]:
        """
        Get all works for an author by their OpenAlex ID with pagination support.
        
        Args:
            author_id: OpenAlex author ID (can be full URL or just the ID part)
            page_size: Number of works per page
            
        Yields:
            Publication objects for each work
            
        Raises:
            OpenAlexError: If the API request fails
        """
        try:
            # Extract the ID part if a full URL is provided
            author_key = author_id.split("/")[-1]
            url = "/works"
            params = {
                "filter": f"author.id:{author_key}",
                "per_page": page_size,
                "select": "id,doi,title,publication_year,cited_by_count,authorships,type"
            }
            
            page = 1
            total = None
            
            while True:
                response = self._make_request(url, {**params, "page": page})
                
                if total is None:
                    total = response["meta"]["count"]
                
                works = response.get("results", [])
                if not works:
                    break
                    
                for work_data in works:
                    yield self._parse_publication(work_data)
                
                if page * page_size >= total:
                    break
                page += 1
                
        except OpenAlexError as e:
            logger.error(f"Failed to get works for author ID {author_id}: {e}")
            raise
    
    def get_author_works_list_by_id(self, author_id: str, page_size: int = 20, max_works: Optional[int] = None) -> List[Publication]:
        # Get all works for an author by their OpenAlex ID as a list.

        works = []
        count = 0
        
        for work in self.get_author_works_by_id(author_id, page_size):
            works.append(work)
            count += 1
            if max_works and count >= max_works:
                break
                
        return works
    
    def get_author_citations_summary(self, name: str, affiliation: Optional[str] = None) -> Optional[AuthorWorksSummary]:
        """
        Get a comprehensive summary of an author's works and citations.
        
        Args:
            name: Author name to search for
            affiliation: Optional institution name to filter by
            
        Returns:
            AuthorWorksSummary object if author found, None otherwise
        """
        # First, find the author
        authors = self.search_authors(name, affiliation, per_page=1)
        if not authors:
            logger.warning(f"No author found for name '{name}'")
            return None
        
        author = authors[0]
        
        # Get detailed author information
        full_author = self.get_author_by_id(author.id)
        if not full_author:
            return None
        
        # Collect all works
        works_list = []
        total_citations = 0
        
        for work in self.get_author_works(full_author):
            works_list.append(work)
            total_citations += work.cited_by_count
        
        return AuthorWorksSummary(
            author=full_author,
            total_citations=total_citations,
            works=works_list,
            works_count=len(works_list)
        )
    
    def search_publications(self, title: str, per_page: int = 10) -> List[Publication]:
        """
        Search for publications by title.
        
        Args:
            title: Publication title to search for
            per_page: Number of results per page
            
        Returns:
            List of Publication objects matching the search criteria
        """
        params = {
            "search": title,
            "per_page": per_page,
            "sort": "relevance_score:desc"
        }
        
        data = self._make_request("/works", params)
        results = data.get("results", [])
        
        return [self._parse_publication(pub_data) for pub_data in results]
    
    def get_publication_by_title(self, title: str) -> Optional[Publication]:
        """
        Get the best matching publication by title.
        
        Args:
            title: Publication title to search for
            
        Returns:
            Publication object if found, None otherwise
        """
        publications = self.search_publications(title, per_page=1)
        return publications[0] if publications and publications[0].title.lower == title.lower() else None
    
    def get_publication_citations(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get citation information for a publication by title.
        
        Args:
            title: Publication title to search for
            
        Returns:
            Dictionary with citation information or None if not found
        """
        publication = self.get_publication_by_title(title)
        if not publication:
            return None
        
        return {
            "id": publication.id,
            "doi": publication.doi,
            "title": publication.title,
            "year": publication.year,
            "cited_by_count": publication.cited_by_count,
            "authors": publication.authors,
            "venue": publication.venue.get("display_name") if publication.venue else None,
        }
    
    def get_author_metrics(self, name: str, institution:Optional[str]) -> Optional[AuthorMetrics]:
        """
        Extract comprehensive author metrics including h-index, i10-index, and other academic metrics.
        
        This method retrieves detailed author information from OpenAlex including:
        - Basic metrics: works_count, cited_by_count
        - H-index variants: h_index, h_index_5_years, h_index_10_years
        - I-index variants: i10_index, i100_index (and time-based variants)
        - G-index variants: g_index (and time-based variants)
        - Career breakdown and impact metrics
        
        Args:
            name: Author name to search for
            include_works: Whether to include top works in the response
            include_concepts: Whether to include top concepts in the response
            
        Returns:
            AuthorMetrics object with comprehensive metrics if author found, None otherwise
            
        Raises:
            OpenAlexError: If the API request fails
        """
        # First, find the author
        authors = self.search_authors(name, institution, per_page=5)
        if not authors:
            logger.warning(f"No author found for name '{name}'")
            return None
        
        author = authors[0]
        
        # Get detailed author information with all metrics
        try:
            # Extract the ID part if a full URL is provided
            author_key = author.id.split("/")[-1]
            
            # Request comprehensive author data including all metrics
            params = {
                "select": "id,display_name,orcid,works_count,cited_by_count,summary_stats"
            }

            data = self._make_request(f"/authors/{quote(author_key)}", params)
            
            # Parse the comprehensive metrics
            return self._parse_author_metrics(data)
            
        except OpenAlexError as e:
            logger.error(f"Failed to get author metrics for '{name}': {e}")
            return None
    
    def get_author_metrics_by_id(self, author_id: str, include_works: bool = True,
                                include_concepts: bool = True) -> Optional[AuthorMetrics]:
        """
        Get comprehensive author metrics by OpenAlex author ID.
        
        Args:
            author_id: OpenAlex author ID (can be full URL or just the ID part)
            include_works: Whether to include top works in the response
            include_concepts: Whether to include top concepts in the response
            
        Returns:
            AuthorMetrics object with comprehensive metrics if author found, None otherwise
        """
        try:
            # Extract the ID part if a full URL is provided
            author_key = author_id.split("/")[-1]
            
            # Request comprehensive author data including all metrics
            params = {
                "select": "id,display_name,orcid,works_count,cited_by_count,summary_stats,last_known_institution"
            }
            
            if include_concepts:
                params["select"] += ",x_concepts"
            
            if include_works:
                params["select"] += ",top_works"
            
            data = self._make_request(f"/authors/{quote(author_key)}", params)
            
            # Parse the comprehensive metrics
            return self._parse_author_metrics(data)
            
        except OpenAlexError as e:
            logger.error(f"Failed to get author metrics by ID {author_id}: {e}")
            return None
    
    def _parse_author(self, author_data: Dict[str, Any]) -> Author:
        """Parse raw author data into an Author object."""
        return Author(
            id=author_data.get("id", ""),
            display_name=author_data.get("display_name", ""),
            orcid=author_data.get("orcid"),
            works_count=author_data.get("works_count"),
            cited_by_count=author_data.get("cited_by_count"),
            last_known_institution=author_data.get("last_known_institution"),
            h_index=author_data.get("summary_stats", {}).get("h_index"),
            i10_index=author_data.get("summary_stats", {}).get("i10_index")
        )
    
    def _parse_publication(self, pub_data: Dict[str, Any]) -> Publication:
        """Parse raw publication data into a Publication object."""
        return Publication(
            id=pub_data.get("id", ""),
            doi=pub_data.get("doi"),
            title=pub_data.get("title", ""),
            year=pub_data.get("publication_year"),
            cited_by_count=pub_data.get("cited_by_count", 0),
            venue=pub_data.get("host_venue"),
            authors=[a["author"]["display_name"] for a in pub_data.get("authorships", [])],
            abstract=pub_data.get("abstract_inverted_index"),
            type=pub_data.get("type")
        )
    
    def _parse_author_metrics(self, author_data: Dict[str, Any]) -> AuthorMetrics:
        """Parse raw author data into a comprehensive AuthorMetrics object."""
        summary_stats = author_data.get("summary_stats", {})


        
        # Calculate impact factor (citations per work)
        works_count = author_data.get("works_count", 0)
        cited_by_count = author_data.get("cited_by_count", 0)
        impact_factor = cited_by_count / works_count if works_count > 0 else None
        
        return AuthorMetrics(
            id=author_data.get("id", ""),
            display_name=author_data.get("display_name", ""),
            orcid=author_data.get("orcid"),
            works_count=works_count,
            cited_by_count=cited_by_count,
            h_index=summary_stats.get("h_index"),
            i10_index=summary_stats.get("i10_index"),
            impact_factor=impact_factor
        )


# Convenience functions for backward compatibility
def get_author_works_by_id(author_id: str, page_size: int = 20):
    """Backward compatibility function to get author works by ID."""
    client = OpenAlexClient()
    return client.get_author_works_by_id(author_id, page_size)


def get_author_works_list_by_id(author_id: str, page_size: int = 20, max_works: Optional[int] = None):
    """Backward compatibility function to get author works by ID as a list."""
    client = OpenAlexClient()
    return client.get_author_works_list_by_id(author_id, page_size, max_works)


# Example usage and testing
if __name__ == "__main__":
    # Create a client instance
    client = OpenAlexClient()
    
    # Example 1: Search for a publication
    print("=== Publication Search Example ===")
    pub = client.get_publication_by_title("Language Models are Few-Shot Learners")
    if pub:
        print(f"Title: {pub.title}")
        print(f"Year: {pub.year}")
        print(f"Citations: {pub.cited_by_count}")
        print(f"Authors: {', '.join(pub.authors[:5])}...")
    else:
        print("No publication found")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Get author information and works
    print("=== Author Search Example ===")
    summary = client.get_author_citations_summary("George Kour")
    if summary:
        print(f"Author: {summary.author.display_name}")
        print(f"ORCID: {summary.author.orcid}")
        print(f"OpenAlex author-level cited_by_count: {summary.author.cited_by_count}")
        print(f"Sum over fetched works: {summary.total_citations}")
        print(f"Publications fetched: {summary.works_count}")
        
        # Print first few publications
        for work in summary.works[:5]:
            print(f"- ({work.year}) {work.title} — cites={work.cited_by_count}")
    else:
        print("No author found")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Search for multiple authors
    print("=== Multiple Authors Search Example ===")
    authors = client.search_authors("John Smith", per_page=5)
    print(f"Found {len(authors)} authors named 'John Smith':")
    for i, author in enumerate(authors[:3], 1):
        print(f"{i}. {author.display_name} (Works: {author.works_count}, Citations: {author.cited_by_count})")
    
    print("\n" + "="*50 + "\n")
    
    # Example 4: Get comprehensive author metrics
    print("=== Author Metrics Example ===")
    metrics = client.get_author_metrics("George Kour")
    print(metrics)
    
    print("\n" + "="*50 + "\n")
    
    # Example 5: Get author works by ID
    print("=== Author Works by ID Example ===")
    # First get an author ID
    authors = client.search_authors("George Kour", per_page=1)
    if authors:
        author_id = authors[0].id
        print(f"Getting works for author ID: {author_id}")
        
        # Get first 5 works as a list
        works = client.get_author_works_list_by_id(author_id, max_works=5)
        print(f"Found {len(works)} works:")
        for i, work in enumerate(works, 1):
            print(f"{i}. ({work.year}) {work.title} — {work.cited_by_count} citations")
    else:
        print("No author found for testing")
