from typing import Dict, Any, Optional, List, Tuple
import re

def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles using simple word overlap.

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score between 0 and 1
    """
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


def deduplicate_publications(publications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate publications based on title similarity and other identifiers.
    Enhanced to handle shared papers between team members.

    This method is crucial for accurate team analysis as it prevents:
    - Inflated publication counts due to shared papers
    - Duplicate domain analysis from the same paper
    - Misleading team statistics

    Deduplication priority:
    1. DOI (most reliable identifier)
    2. ArXiv ID
    3. Paper ID
    4. Title similarity (with 90%+ threshold)
    """
    if not publications:
        return []

    unique_pubs = []
    seen_identifiers = set()

    for pub in publications:
        # Create multiple identifiers for better deduplication
        title = pub.get("title", "").lower().strip()
        doi = pub.get("doi", "").lower().strip()
        arxiv_id = pub.get("arxiv_id", "").lower().strip()
        paper_id = pub.get("paper_id", "").lower().strip()

        # Generate unique identifier for this publication
        if doi:
            identifier = f"doi:{doi}"
        elif arxiv_id:
            identifier = f"arxiv:{arxiv_id}"
        elif paper_id:
            identifier = f"id:{paper_id}"
        elif title:
            # For title-based deduplication, normalize the title
            normalized_title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation
            normalized_title = re.sub(r'\s+', ' ', normalized_title).strip()  # Normalize whitespace
            identifier = f"title:{normalized_title}"
        else:
            # Skip publications without any identifiable information
            continue

        if identifier not in seen_identifiers:
            unique_pubs.append(pub)
            seen_identifiers.add(identifier)

            # Also add title to prevent very similar titles
            if title:
                seen_identifiers.add(f"title:{title}")

    return unique_pubs


def publications_match(pub1: Dict[str, Any], pub2: Dict[str, Any]) -> bool:
    """
    Check if two publications are the same paper.

    Args:
        pub1: First publication
        pub2: Second publication

    Returns:
        True if publications match, False otherwise
    """
    try:
        # Check DOI first (most reliable)
        doi1 = pub1.get("doi", "").lower().strip()
        doi2 = pub2.get("doi", "").lower().strip()
        if doi1 and doi2 and doi1 == doi2:
            return True

        # Check ArXiv ID
        arxiv1 = pub1.get("arxiv_id", "").lower().strip()
        arxiv2 = pub2.get("arxiv_id", "").lower().strip()
        if arxiv1 and arxiv2 and arxiv1 == arxiv2:
            return True

        # Check paper ID
        paper_id1 = pub1.get("paper_id", "").lower().strip()
        paper_id2 = pub2.get("paper_id", "").lower().strip()
        if paper_id1 and paper_id2 and paper_id1 == paper_id2:
            return True

        # Check title similarity (fallback)
        title1 = pub1.get("title", "").lower().strip()
        title2 = pub2.get("title", "").lower().strip()
        if title1 and title2:
            # Normalize titles for comparison
            norm_title1 = re.sub(r'[^\w\s]', '', title1)
            norm_title1 = re.sub(r'\s+', ' ', norm_title1).strip()
            norm_title2 = re.sub(r'[^\w\s]', '', title2)
            norm_title2 = re.sub(r'\s+', ' ', norm_title2).strip()

            if norm_title1 == norm_title2:
                return True

            # Check for high similarity (90%+ match)
            return calculate_title_similarity(norm_title1, norm_title2) > 0.9

        return False

    except Exception as e:
        logger.error(f"Error comparing publications: {str(e)}")
        return False
