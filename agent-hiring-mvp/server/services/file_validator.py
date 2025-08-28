"""File validation service for checking file types, sizes, and security."""

import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from fastapi import UploadFile, HTTPException

from ..config.file_storage_config import FileStorageConfig

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


class FileValidator:
    """Service for validating file uploads."""
    
    def __init__(self, config: FileStorageConfig):
        self.config = config
        self._setup_mimetypes()
    
    def _setup_mimetypes(self):
        """Setup MIME type detection for common file types."""
        # Add custom MIME types for better detection
        mimetypes.add_type("application/json", ".json")
        mimetypes.add_type("text/yaml", ".yaml")
        mimetypes.add_type("text/yaml", ".yml")
        mimetypes.add_type("text/csv", ".csv")
        mimetypes.add_type("text/xml", ".xml")
    
    def validate_file(
        self, 
        file: UploadFile, 
        user_id: int
    ) -> Tuple[str, str, Optional[str]]:
        """
        Validate a file upload.
        
        Returns:
            Tuple of (file_extension, mime_type, error_message)
        """
        try:
            # Basic file checks
            if not file.filename:
                raise FileValidationError("No filename provided")
            
            if not file.size:
                raise FileValidationError("File size could not be determined")
            
            # Get file extension and MIME type
            file_extension = self._get_file_extension(file.filename)
            mime_type = self._detect_mime_type(file.filename, file.content_type)
            
            # Validate file size
            self._validate_file_size(file.size)
            
            # Validate file type
            self._validate_file_type(file_extension)
            
            # Security checks
            self._validate_file_security(file_extension, mime_type)
            
            logger.info(f"File validation passed for user {user_id}: {file.filename}")
            return file_extension, mime_type, None
            
        except FileValidationError as e:
            logger.warning(f"File validation failed for user {user_id}: {file.filename} - {str(e)}")
            return "", "", str(e)
        except Exception as e:
            logger.error(f"Unexpected error during file validation for user {user_id}: {file.filename} - {str(e)}")
            return "", "", f"Validation error: {str(e)}"
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if not filename:
            return ""
        
        ext = Path(filename).suffix
        return ext[1:].lower() if ext else ""
    
    def _detect_mime_type(self, filename: str, content_type: Optional[str]) -> str:
        """Detect MIME type from filename and content type."""
        # Try to get MIME type from filename
        mime_type, _ = mimetypes.guess_type(filename)
        
        # Fall back to content type if available
        if not mime_type and content_type:
            mime_type = content_type
        
        # Default to application/octet-stream if still unknown
        return mime_type or "application/octet-stream"
    
    def _validate_file_size(self, file_size: int):
        """Validate file size against configured limits."""
        if file_size > self.config.max_file_size_bytes:
            max_size_mb = self.config.max_file_size_mb
            raise FileValidationError(
                f"File too large. Maximum size is {max_size_mb}MB "
                f"({file_size} bytes received)"
            )
        
        if file_size <= 0:
            raise FileValidationError("File size must be greater than 0")
    
    def _validate_file_type(self, file_extension: str):
        """Validate file extension against allowed types."""
        if not file_extension:
            raise FileValidationError("File must have a valid extension")
        
        if file_extension.lower() not in self.config.allowed_file_types_list:
            allowed_types = ", ".join(self.config.allowed_file_types_list)
            raise FileValidationError(
                f"File type '{file_extension}' not allowed. "
                f"Allowed types: {allowed_types}"
            )
    
    def _validate_file_security(self, file_extension: str, mime_type: str):
        """Perform security validation on file."""
        # Check for blocked file types
        if file_extension.lower() in self.config.blocked_file_types_list:
            raise FileValidationError(
                f"File type '{file_extension}' is blocked for security reasons"
            )
        
        # Check for potentially dangerous MIME types
        dangerous_mimes = [
            "application/x-executable",
            "application/x-msdownload",
            "application/x-msi",
            "application/x-ms-shortcut",
            "application/x-ms-shortcut",
            "text/javascript",
            "application/javascript"
        ]
        
        if mime_type.lower() in dangerous_mimes:
            raise FileValidationError(
                f"MIME type '{mime_type}' is not allowed for security reasons"
            )
    
    def validate_expiry_hours(self, expiry_hours: Optional[int]) -> int:
        """Validate and normalize expiry hours."""
        if expiry_hours is None:
            return self.config.default_expiry_hours
        
        if not isinstance(expiry_hours, int):
            raise FileValidationError("Expiry hours must be an integer")
        
        if expiry_hours < self.config.min_expiry_hours:
            raise FileValidationError(
                f"Expiry hours must be at least {self.config.min_expiry_hours}"
            )
        
        if expiry_hours > self.config.max_expiry_hours:
            raise FileValidationError(
                f"Expiry hours cannot exceed {self.config.max_expiry_hours}"
            )
        
        return expiry_hours
    
    def validate_tags(self, tags: Optional[List[str]]) -> Optional[str]:
        """Validate and normalize tags."""
        if not tags:
            return None
        
        if not isinstance(tags, list):
            raise FileValidationError("Tags must be a list")
        
        # Validate individual tags
        validated_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                raise FileValidationError("All tags must be strings")
            
            tag = tag.strip()
            if not tag:
                continue
            
            if len(tag) > 50:  # Limit tag length
                raise FileValidationError("Tags cannot exceed 50 characters")
            
            validated_tags.append(tag)
        
        return ",".join(validated_tags) if validated_tags else None
    
    def get_file_info(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Get comprehensive file information for logging and metadata."""
        file_extension = self._get_file_extension(filename)
        mime_type = self._detect_mime_type(filename, None)
        
        return {
            "filename": filename,
            "extension": file_extension,
            "mime_type": mime_type,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "is_allowed_type": file_extension.lower() in self.config.allowed_file_types_list,
            "is_blocked_type": file_extension.lower() in self.config.blocked_file_types_list
        }
