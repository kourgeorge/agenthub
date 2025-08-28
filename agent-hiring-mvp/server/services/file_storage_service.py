"""Refactored file storage service with better separation of concerns."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from pathlib import Path

from ..models.temporary_file import TemporaryFile
from ..config.file_storage_config import FileStorageConfig
from .interfaces.file_storage_interface import FileStorageInterface
from .file_validator import FileValidator, FileValidationError
from .file_storage_manager import FileStorageManager, FileStorageError

logger = logging.getLogger(__name__)


class FileStorageService(FileStorageInterface):
    """Service for managing temporary file storage and lifecycle."""
    
    def __init__(self, db: Session, config: Optional[FileStorageConfig] = None):
        self.db = db
        self.config = config or FileStorageConfig()
        self.validator = FileValidator(self.config)
        self.storage_manager = FileStorageManager(self.config)
        
        logger.info(f"FileStorageService initialized with config: {self.config.upload_dir}")
    
    async def upload_file(
        self, 
        file: UploadFile, 
        user_id: int, 
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expiry_hours: Optional[int] = None
    ) -> TemporaryFile:
        """Upload a file and create a temporary file record."""
        
        logger.info(f"Starting file upload for user {user_id}: {file.filename}")
        
        try:
            # Validate file
            file_extension, mime_type, error = self.validator.validate_file(file, user_id)
            if error:
                raise HTTPException(status_code=400, detail=error)
            
            # Validate and normalize parameters
            normalized_expiry = self.validator.validate_expiry_hours(expiry_hours)
            normalized_tags = self.validator.validate_tags(tags)
            
            # Check user file limits
            await self._check_user_file_limits(user_id)
            
            # Generate storage filename
            stored_filename = self.storage_manager.generate_stored_filename(file.filename)
            
            # Store file on filesystem
            file_path, file_size = self.storage_manager.store_file(
                file, user_id, stored_filename
            )
            
            # Create database record
            temp_file = await self._create_file_record(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=str(file_path),
                file_size=file_size,
                file_type=mime_type,
                file_extension=file_extension,
                description=description,
                tags=normalized_tags,
                user_id=user_id,
                expiry_hours=normalized_expiry
            )
            
            logger.info(f"File uploaded successfully: {file.filename} -> {stored_filename}")
            return temp_file
            
        except HTTPException:
            raise
        except FileValidationError as e:
            logger.warning(f"File validation failed for user {user_id}: {file.filename} - {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except FileStorageError as e:
            logger.error(f"File storage failed for user {user_id}: {file.filename} - {str(e)}")
            raise HTTPException(status_code=500, detail="File storage failed")
        except Exception as e:
            logger.error(f"Unexpected error during file upload for user {user_id}: {file.filename} - {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_file(self, file_id: str, user_id: int) -> Optional[TemporaryFile]:
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
            await self._mark_file_expired(temp_file)
            return None
        
        logger.debug(f"File {file_id} retrieved successfully for user {user_id}")
        return temp_file
    
    async def get_user_files(
        self, 
        user_id: int, 
        include_expired: bool = False
    ) -> List[TemporaryFile]:
        """Get all files for a user."""
        query = self.db.query(TemporaryFile).filter(
            TemporaryFile.user_id == user_id,
            TemporaryFile.is_deleted == False
        )
        
        if not include_expired:
            query = query.filter(TemporaryFile.expires_at > datetime.utcnow())
        
        return query.order_by(TemporaryFile.created_at.desc()).all()
    
    async def download_file(
        self, 
        file_id: str, 
        access_token: str
    ) -> Optional[Tuple[Path, str]]:
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
            await self._mark_file_expired(temp_file)
            return None
        
        # Retrieve file from storage
        file_path = self.storage_manager.retrieve_file(temp_file.file_path)
        if not file_path:
            logger.error(f"File {file_id} not found on disk: {temp_file.file_path}")
            return None
        
        # Mark as accessed
        await self._mark_file_accessed(temp_file)
        
        logger.info(f"File {file_id} downloaded successfully: {temp_file.original_filename}")
        return file_path, temp_file.original_filename
    
    async def delete_file(self, file_id: str, user_id: int) -> bool:
        """Delete a file (soft delete)."""
        temp_file = await self.get_file(file_id, user_id)
        if not temp_file:
            return False
        
        # Soft delete in database
        temp_file.is_deleted = True
        self.db.commit()
        
        # Optionally remove from filesystem (could be configurable)
        if self.config.enable_auto_cleanup:
            self.storage_manager.delete_file(temp_file.file_path)
        
        logger.info(f"File {file_id} marked as deleted")
        return True
    
    async def extend_file_expiry(
        self, 
        file_id: str, 
        user_id: int, 
        additional_hours: int
    ) -> bool:
        """Extend the expiry time of a file."""
        # Validate additional hours
        try:
            self.validator.validate_expiry_hours(additional_hours)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        temp_file = await self.get_file(file_id, user_id)
        if not temp_file:
            return False
        
        # Extend expiry
        temp_file.expires_at += timedelta(hours=additional_hours)
        self.db.commit()
        
        logger.info(f"File {file_id} expiry extended by {additional_hours} hours")
        return True
    
    async def cleanup_expired_files(self) -> int:
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
                # Remove from filesystem
                self.storage_manager.delete_file(temp_file.file_path)
                
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
    
    async def get_storage_stats(self) -> Dict[str, Any]:
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
        
        # Get filesystem stats
        fs_stats = self.storage_manager.get_storage_info()
        
        return {
            "database_stats": {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "expired_files": expired_files
            },
            "filesystem_stats": fs_stats,
            "configuration": {
                "max_file_size_mb": self.config.max_file_size_mb,
                "default_expiry_hours": self.config.default_expiry_hours,
                "allowed_file_types": self.config.allowed_file_types_list,
                "blocked_file_types": self.config.blocked_file_types_list
            }
        }
    
    async def validate_file_references(
        self, 
        file_references: List[str], 
        user_id: int
    ) -> Dict[str, Any]:
        """Validate file references for agent execution."""
        if not file_references:
            return {"valid": True, "files": [], "errors": []}
        
        logger.info(f"Validating {len(file_references)} file references for user {user_id}")
        
        valid_files = []
        errors = []
        
        for file_id in file_references:
            try:
                temp_file = await self.get_file(file_id, user_id)
                if temp_file:
                    valid_files.append({
                        "file_id": file_id,
                        "filename": temp_file.original_filename,
                        "size": temp_file.file_size,
                        "type": temp_file.file_type,
                        "expires_at": temp_file.expires_at.isoformat()
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
    
    async def _create_file_record(
        self,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        file_type: str,
        file_extension: str,
        description: Optional[str],
        tags: Optional[str],
        user_id: int,
        expiry_hours: int
    ) -> TemporaryFile:
        """Create a temporary file database record."""
        temp_file = TemporaryFile.create_with_expiry(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            file_extension=file_extension,
            description=description,
            tags=tags,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        self.db.add(temp_file)
        self.db.commit()
        
        return temp_file
    
    async def _check_user_file_limits(self, user_id: int):
        """Check if user has reached file limits."""
        if self.config.max_files_per_user <= 0:
            return
        
        active_files = self.db.query(TemporaryFile).filter(
            TemporaryFile.user_id == user_id,
            TemporaryFile.is_deleted == False,
            TemporaryFile.expires_at > datetime.utcnow()
        ).count()
        
        if active_files >= self.config.max_files_per_user:
            raise HTTPException(
                status_code=429,
                detail=f"File limit reached. Maximum {self.config.max_files_per_user} active files allowed."
            )
    
    async def _mark_file_expired(self, temp_file: TemporaryFile):
        """Mark a file as expired."""
        temp_file.is_deleted = True
        self.db.commit()
    
    async def _mark_file_accessed(self, temp_file: TemporaryFile):
        """Mark a file as accessed."""
        temp_file.mark_accessed()
        self.db.commit()
