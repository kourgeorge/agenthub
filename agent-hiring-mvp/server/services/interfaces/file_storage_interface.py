"""Interface for file storage operations."""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from fastapi import UploadFile

from ...models.temporary_file import TemporaryFile


class FileStorageInterface(ABC):
    """Abstract interface for file storage operations."""
    
    @abstractmethod
    async def upload_file(
        self, 
        file: UploadFile, 
        user_id: int, 
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expiry_hours: Optional[int] = None
    ) -> TemporaryFile:
        """Upload a file and create a temporary file record."""
        pass
    
    @abstractmethod
    async def get_file(self, file_id: str, user_id: int) -> Optional[TemporaryFile]:
        """Get a temporary file by ID, ensuring user has access."""
        pass
    
    @abstractmethod
    async def get_user_files(
        self, 
        user_id: int, 
        include_expired: bool = False
    ) -> List[TemporaryFile]:
        """Get all files for a user."""
        pass
    
    @abstractmethod
    async def download_file(
        self, 
        file_id: str, 
        access_token: str
    ) -> Optional[Tuple[Path, str]]:
        """Download a file using access token, returns (file_path, original_filename)."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str, user_id: int) -> bool:
        """Delete a file (soft delete)."""
        pass
    
    @abstractmethod
    async def extend_file_expiry(
        self, 
        file_id: str, 
        user_id: int, 
        additional_hours: int
    ) -> bool:
        """Extend the expiry time of a file."""
        pass
    
    @abstractmethod
    async def cleanup_expired_files(self) -> int:
        """Clean up expired files from storage and database."""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass
    
    @abstractmethod
    async def validate_file_references(
        self, 
        file_references: List[str], 
        user_id: int
    ) -> Dict[str, Any]:
        """Validate file references for agent execution."""
        pass
