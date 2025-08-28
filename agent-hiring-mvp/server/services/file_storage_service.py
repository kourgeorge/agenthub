"""File storage service for managing temporary file uploads and storage."""

import os
import shutil
import logging
import mimetypes
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import json

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel

from ..models.temporary_file import TemporaryFile
from ..models.user import User

logger = logging.getLogger(__name__)


class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    expiry_hours: Optional[int] = None


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str
    original_filename: str
    file_size: int
    file_type: Optional[str]
    expires_at: str
    access_token: str
    access_url: str
    message: str


class FileInfoResponse(BaseModel):
    """Response model for file information."""
    id: str
    original_filename: str
    stored_filename: str
    file_size: int
    file_type: Optional[str]
    file_extension: Optional[str]
    description: Optional[str]
    tags: Optional[str]
    expires_at: str
    download_count: int
    last_accessed_at: Optional[str]
    created_at: str
    access_url: str
    server_host: Optional[str] = None


class FileListResponse(BaseModel):
    """Response model for file listing."""
    files: List[FileInfoResponse]
    total: int


class FileStatsResponse(BaseModel):
    """Response model for file statistics."""
    user_stats: Dict[str, Any]
    system_limits: Dict[str, Any]


class FileStorageService:
    """Service for managing temporary file storage and lifecycle."""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Get configuration from environment
        self.upload_dir = os.getenv("UPLOAD_DIR", "./temp_uploads")
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        self.default_expiry_hours = int(os.getenv("DEFAULT_EXPIRY_HOURS", "24"))
        self.allowed_file_types = os.getenv("ALLOWED_FILE_TYPES", "pdf,doc,docx,txt,png,jpg,jpeg,csv,json,xml,yaml,yml").split(",")
        
        # Ensure upload directory exists
        self.upload_dir = Path(self.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Create user-specific subdirectories
        self.user_uploads_dir = self.upload_dir / "users"
        self.user_uploads_dir.mkdir(exist_ok=True)
        
        logger.info(f"File storage service initialized with upload dir: {self.upload_dir}")
        logger.info(f"Max file size: {self.max_file_size_mb}MB, Default expiry: {self.default_expiry_hours}h")
    
    def upload_file(
        self, 
        file: UploadFile, 
        user_id: int, 
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expiry_hours: Optional[int] = None
    ) -> TemporaryFile:
        """Upload a file and create a temporary file record."""
        
        logger.info(f"Starting file upload for user {user_id}: {file.filename}")
        
        # Validate file size
        if file.size and file.size > (self.max_file_size_mb * 1024 * 1024):
            logger.warning(f"File upload rejected for user {user_id}: file too large ({file.size} bytes)")
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {self.max_file_size_mb}MB"
            )
        
        # Validate file type
        file_extension = self._get_file_extension(file.filename)
        if file_extension and file_extension.lower() not in [ext.lower() for ext in self.allowed_file_types]:
            logger.warning(f"File upload rejected for user {user_id}: invalid file type {file_extension}")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(self.allowed_file_types)}"
            )
        
        # Generate unique filename
        stored_filename = self._generate_stored_filename(file.filename)
        
        # Create user-specific directory
        user_dir = self.user_uploads_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        
        # Full file path
        file_path = user_dir / stored_filename
        
        try:
            # Save file to disk
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file.filename)
            
            # Create database record
            temp_file = TemporaryFile.create_with_expiry(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=str(file_path),
                file_size=file_size,
                file_type=mime_type,
                file_extension=file_extension,
                description=description,
                tags=json.dumps(tags) if tags else None,
                user_id=user_id,
                expires_at=datetime.utcnow() + timedelta(hours=expiry_hours or self.default_expiry_hours)
            )
            
            self.db.add(temp_file)
            self.db.commit()
            
            logger.info(f"File uploaded successfully: {file.filename} -> {stored_filename} (size: {file_size} bytes)")
            return temp_file
            
        except Exception as e:
            # Clean up file if database operation fails
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"Cleaned up failed upload file: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup failed upload file {file_path}: {cleanup_error}")
            
            logger.error(f"Failed to upload file {file.filename} for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    def get_file(self, file_id: str, user_id: int) -> Optional[TemporaryFile]:
        """Get a temporary file by ID, ensuring user has access."""
        logger.debug(f"Getting file {file_id} for user {user_id}")
        
        temp_file = self.db.query(TemporaryFile).filter(
            TemporaryFile.id == file_id,
            TemporaryFile.user_id == user_id,
            TemporaryFile.is_deleted == False
        ).first()
        
        if not temp_file:
            logger.debug(f"File {file_id} not found for user {user_id}")
            return None
        
        # Check if file has expired
        if temp_file.is_expired():
            logger.warning(f"File {file_id} has expired, marking for deletion")
            temp_file.is_deleted = True
            self.db.commit()
            return None
        
        logger.debug(f"File {file_id} retrieved successfully for user {user_id}")
        return temp_file
    
    def get_user_files(self, user_id: int, include_expired: bool = False) -> List[TemporaryFile]:
        """Get all files for a user."""
        query = self.db.query(TemporaryFile).filter(
            TemporaryFile.user_id == user_id,
            TemporaryFile.is_deleted == False
        )
        
        if not include_expired:
            query = query.filter(TemporaryFile.expires_at > datetime.utcnow())
        
        return query.order_by(TemporaryFile.created_at.desc()).all()
    
    def download_file(self, file_id: str, access_token: str) -> Optional[Tuple[Path, str]]:
        """Download a file using access token, returns (file_path, original_filename)."""
        logger.debug(f"Downloading file {file_id} with access token")
        
        temp_file = self.db.query(TemporaryFile).filter(
            TemporaryFile.id == file_id,
            TemporaryFile.access_token == access_token,
            TemporaryFile.is_deleted == False
        ).first()
        
        if not temp_file:
            logger.warning(f"File {file_id} not found or access denied for download")
            return None
        
        # Check if file has expired
        if temp_file.is_expired():
            logger.warning(f"File {file_id} has expired during download")
            return None
        
        # Check if file exists on disk
        file_path = Path(temp_file.file_path)
        if not file_path.exists():
            logger.error(f"File {file_id} not found on disk: {temp_file.file_path}")
            return None
        
        # Mark as accessed
        temp_file.mark_accessed()
        self.db.commit()
        
        logger.info(f"File {file_id} downloaded successfully: {temp_file.original_filename}")
        return file_path, temp_file.original_filename
    
    def get_file_by_token(self, file_id: str, access_token: str) -> Optional[TemporaryFile]:
        """Get a temporary file by ID and access token (for metadata access)."""
        logger.debug(f"Getting file metadata for {file_id} with access token")
        
        temp_file = self.db.query(TemporaryFile).filter(
            TemporaryFile.id == file_id,
            TemporaryFile.access_token == access_token,
            TemporaryFile.is_deleted == False
        ).first()
        
        if not temp_file:
            logger.warning(f"File {file_id} not found or access denied for metadata access")
            return None
        
        # Check if file has expired
        if temp_file.is_expired():
            logger.warning(f"File {file_id} has expired during metadata access")
            return None
        
        logger.debug(f"File metadata retrieved successfully: {temp_file.original_filename}")
        return temp_file
    
    def delete_file(self, file_id: str, user_id: int) -> bool:
        """Delete a file (soft delete)."""
        temp_file = self.get_file(file_id, user_id)
        if not temp_file:
            return False
        
        # Soft delete
        temp_file.is_deleted = True
        self.db.commit()
        
        logger.info(f"File {file_id} marked as deleted")
        return True
    
    def extend_file_expiry(self, file_id: str, user_id: int, additional_hours: int) -> bool:
        """Extend the expiry time of a file."""
        temp_file = self.get_file(file_id, user_id)
        if not temp_file:
            return False
        
        # Extend expiry
        temp_file.expires_at += timedelta(hours=additional_hours)
        self.db.commit()
        
        logger.info(f"File {file_id} expiry extended by {additional_hours} hours")
        return True
    
    def cleanup_expired_files(self) -> int:
        """Clean up expired files from storage and database."""
        logger.info("Starting cleanup of expired files")
        
        expired_files = self.db.query(TemporaryFile).filter(
            TemporaryFile.expires_at < datetime.utcnow(),
            TemporaryFile.is_deleted == False
        ).all()
        
        logger.info(f"Found {len(expired_files)} expired files to cleanup")
        cleaned_count = 0
        
        for temp_file in expired_files:
            try:
                # Remove file from disk
                file_path = Path(temp_file.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Removed expired file from disk: {temp_file.file_path}")
                else:
                    logger.debug(f"Expired file not found on disk: {temp_file.file_path}")
                
                # Mark as deleted in database
                temp_file.is_deleted = True
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Failed to cleanup expired file {temp_file.id}: {str(e)}")
        
        if cleaned_count > 0:
            self.db.commit()
            logger.info(f"Successfully cleaned up {cleaned_count} expired files")
        else:
            logger.info("No expired files to cleanup")
        
        return cleaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_files = self.db.query(TemporaryFile).filter(
            TemporaryFile.is_deleted == False
        ).count()
        
        total_size = self.db.query(TemporaryFile).filter(
            TemporaryFile.is_deleted == False
        ).with_entities(
            self.db.func.sum(TemporaryFile.file_size)
        ).scalar() or 0
        
        expired_files = self.db.query(TemporaryFile).filter(
            TemporaryFile.expires_at < datetime.utcnow(),
            TemporaryFile.is_deleted == False
        ).count()
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "expired_files": expired_files,
            "upload_directory": str(self.upload_dir)
        }
    
    def _get_file_extension(self, filename: str) -> Optional[str]:
        """Extract file extension from filename."""
        if not filename:
            return None
        
        # Get the extension without the dot
        ext = Path(filename).suffix
        return ext[1:] if ext else None
    
    def _generate_stored_filename(self, original_filename: str) -> str:
        """Generate a unique filename for storage."""
        # Generate UUID-based filename
        unique_id = str(uuid.uuid4())
        
        # Get original extension
        ext = Path(original_filename).suffix
        
        # Create stored filename: {uuid}{extension}
        stored_filename = f"{unique_id}{ext}" if ext else unique_id
        
        return stored_filename
    
    def validate_file_references(self, file_references: List[str], user_id: int) -> Dict[str, Any]:
        """Validate file references for agent execution.
        
        Args:
            file_references: List of file IDs to validate
            user_id: ID of the user making the request
            
        Returns:
            Dict with validation results and file information
        """
        if not file_references:
            return {"valid": True, "files": [], "errors": []}
        
        logger.info(f"Validating {len(file_references)} file references for user {user_id}")
        
        valid_files = []
        errors = []
        
        for file_id in file_references:
            try:
                temp_file = self.get_file(file_id, user_id)
                if temp_file:
                    valid_files.append({
                        "file_id": file_id,
                        "filename": temp_file.original_filename,
                        "size": temp_file.file_size,
                        "type": temp_file.file_type
                    })
                    logger.debug(f"File reference {file_id} validated successfully")
                else:
                    errors.append(f"File {file_id} not found or access denied")
                    logger.warning(f"File reference {file_id} validation failed for user {user_id}")
            except Exception as e:
                errors.append(f"Error validating file {file_id}: {str(e)}")
                logger.error(f"Error validating file reference {file_id}: {str(e)}")
        
        validation_result = {
            "valid": len(errors) == 0,
            "files": valid_files,
            "errors": errors,
            "total_files": len(file_references),
            "valid_files": len(valid_files),
            "invalid_files": len(errors)
        }
        
        logger.info(f"File validation completed: {len(valid_files)} valid, {len(errors)} errors")
        return validation_result
