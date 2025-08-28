"""File storage manager for handling file I/O operations."""

import os
import shutil
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile

from ..config.file_storage_config import FileStorageConfig

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Custom exception for file storage operations."""
    pass


class FileStorageManager:
    """Manages file storage operations on the filesystem."""
    
    def __init__(self, config: FileStorageConfig):
        self.config = config
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist."""
        try:
            # Create main upload directory
            Path(self.config.upload_dir).mkdir(parents=True, exist_ok=True)
            
            # Create user uploads subdirectory
            Path(self.config.upload_path).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"File storage directories initialized: {self.config.upload_path}")
            
        except Exception as e:
            logger.error(f"Failed to create storage directories: {str(e)}")
            raise FileStorageError(f"Storage initialization failed: {str(e)}")
    
    def store_file(
        self, 
        file: UploadFile, 
        user_id: int,
        stored_filename: str
    ) -> Tuple[Path, int]:
        """
        Store a file on the filesystem.
        
        Returns:
            Tuple of (file_path, file_size)
        """
        try:
            # Create user-specific directory
            user_dir = Path(self.config.upload_path) / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Full file path
            file_path = user_dir / stored_filename
            
            # Save file to disk using chunks for memory efficiency
            file_size = 0
            with open(file_path, "wb") as buffer:
                while chunk := file.file.read(self.config.chunk_size):
                    buffer.write(chunk)
                    file_size += len(chunk)
            
            # Verify file was written correctly
            if not file_path.exists() or file_path.stat().st_size != file_size:
                raise FileStorageError("File write verification failed")
            
            logger.debug(f"File stored successfully: {file_path} (size: {file_size} bytes)")
            return file_path, file_size
            
        except Exception as e:
            logger.error(f"Failed to store file {file.filename}: {str(e)}")
            # Clean up any partial file
            self._cleanup_partial_file(file_path)
            raise FileStorageError(f"File storage failed: {str(e)}")
    
    def retrieve_file(self, file_path: str) -> Optional[Path]:
        """Retrieve a file from storage."""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found on disk: {file_path}")
                return None
            
            return path
            
        except Exception as e:
            logger.error(f"Failed to retrieve file {file_path}: {str(e)}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.debug(f"File deleted from disk: {file_path}")
                return True
            else:
                logger.debug(f"File not found on disk for deletion: {file_path}")
                return True  # Consider it "deleted" if it doesn't exist
                
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    def generate_stored_filename(self, original_filename: str) -> str:
        """Generate a unique filename for storage."""
        # Generate UUID-based filename
        unique_id = str(uuid.uuid4())
        
        # Get original extension
        ext = Path(original_filename).suffix
        
        # Create stored filename: {uuid}{extension}
        stored_filename = f"{unique_id}{ext}" if ext else unique_id
        
        return stored_filename
    
    def get_file_path(self, user_id: int, stored_filename: str) -> Path:
        """Get the full file path for a stored file."""
        return Path(self.config.upload_path) / str(user_id) / stored_filename
    
    def get_storage_info(self) -> dict:
        """Get information about the storage system."""
        try:
            upload_path = Path(self.config.upload_path)
            
            # Calculate storage usage
            total_size = 0
            file_count = 0
            
            if upload_path.exists():
                for file_path in upload_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            return {
                "upload_directory": str(self.config.upload_dir),
                "user_uploads_path": str(self.config.upload_path),
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_file_size_mb": self.config.max_file_size_mb,
                "chunk_size": self.config.chunk_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage info: {str(e)}")
            return {
                "error": str(e),
                "upload_directory": str(self.config.upload_dir)
            }
    
    def cleanup_user_directory(self, user_id: int) -> int:
        """Clean up all files for a specific user."""
        try:
            user_dir = Path(self.config.upload_path) / str(user_id)
            if not user_dir.exists():
                return 0
            
            deleted_count = 0
            for file_path in user_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Cleaned up user file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup user file {file_path}: {str(e)}")
            
            # Remove empty user directory
            try:
                user_dir.rmdir()
                logger.debug(f"Removed empty user directory: {user_dir}")
            except OSError:
                # Directory not empty, which is fine
                pass
            
            logger.info(f"Cleaned up {deleted_count} files for user {user_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup user directory for user {user_id}: {str(e)}")
            return 0
    
    def _cleanup_partial_file(self, file_path: Optional[Path]):
        """Clean up a partial file if it exists."""
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up partial file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup partial file {file_path}: {str(e)}")
    
    def validate_storage_path(self, file_path: str) -> bool:
        """Validate that a file path is within the allowed storage directory."""
        try:
            path = Path(file_path).resolve()
            upload_path = Path(self.config.upload_path).resolve()
            
            # Check if the path is within the upload directory
            return upload_path in path.parents or path == upload_path
            
        except Exception:
            return False
