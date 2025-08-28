"""Configuration for file storage service."""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class FileStorageConfig(BaseSettings):
    """Configuration for file storage service."""
    
    # Storage paths
    upload_dir: str = "./temp_uploads"
    user_uploads_subdir: str = "users"
    
    # File size limits
    max_file_size_mb: int = 10
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB default
    
    # File lifecycle
    default_expiry_hours: int = 24
    min_expiry_hours: int = 1
    max_expiry_hours: int = 168  # 1 week
    
    # File type restrictions
    allowed_file_types: str = "pdf,doc,docx,txt,png,jpg,jpeg,csv,json,xml,yaml,yml"
    blocked_file_types: str = "exe,bat,cmd,com,scr,pif,vbs,js,jar,msi"
    
    # Security settings
    access_token_length: int = 64
    enable_file_scanning: bool = False
    max_files_per_user: int = 100
    
    # Cleanup settings
    cleanup_interval_hours: int = 1
    enable_auto_cleanup: bool = True
    
    # Performance settings
    chunk_size: int = 8192  # 8KB chunks for file operations
    max_concurrent_uploads: int = 5
    
    @field_validator('max_file_size_bytes', mode='before')
    @classmethod
    def set_max_file_size_bytes(cls, v, info):
        """Calculate max file size in bytes from MB setting."""
        if 'max_file_size_mb' in info.data:
            return info.data['max_file_size_mb'] * 1024 * 1024
        return v
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list."""
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",") if ext.strip()]
    
    @property
    def blocked_file_types_list(self) -> List[str]:
        """Get blocked file types as a list."""
        return [ext.strip().lower() for ext in self.blocked_file_types.split(",") if ext.strip()]
    
    @property
    def upload_path(self):
        """Get the full upload path."""
        return os.path.join(self.upload_dir, self.user_uploads_subdir)
    
    class Config:
        env_prefix = "FILE_STORAGE_"
        case_sensitive = False
