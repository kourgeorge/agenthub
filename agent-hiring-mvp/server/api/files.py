"""File management API endpoints for temporary file storage."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from ..database.config import get_session_dependency
from ..models.user import User
from ..services.file_storage_service import (
    FileStorageService, 
    FileUploadRequest, 
    FileUploadResponse, 
    FileInfoResponse, 
    FileListResponse, 
    FileStatsResponse
)
from ..middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    expiry_hours: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Upload a temporary file for agent execution."""
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No file provided"
        )
    
    # Parse tags from JSON string
    parsed_tags = None
    if tags:
        try:
            import json
            parsed_tags = json.loads(tags)
            if not isinstance(parsed_tags, list):
                raise ValueError("Tags must be a list")
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid tags format. Expected JSON array."
            )
    
    # Validate expiry hours
    if expiry_hours is not None:
        if expiry_hours < 1 or expiry_hours > 168:  # 1 hour to 1 week
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Expiry hours must be between 1 and 168 (1 week)"
            )
    
    try:
        file_service = FileStorageService(db)
        temp_file = file_service.upload_file(
            file=file,
            user_id=current_user.id,
            description=description,
            tags=parsed_tags,
            expiry_hours=expiry_hours
        )
        
        return FileUploadResponse(
            file_id=temp_file.id,
            original_filename=temp_file.original_filename,
            file_size=temp_file.file_size,
            file_type=temp_file.file_type,
            expires_at=temp_file.expires_at.isoformat(),
            access_token=temp_file.access_token,
            access_url=f"/api/v1/files/{temp_file.id}/download?token={temp_file.access_token}",
            server_host=os.getenv("AGENTHUB_HOSTNAME", "host.docker.internal"),
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.get("/", response_model=FileListResponse)
async def list_files(
    include_expired: bool = Query(False, description="Include expired files"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """List all temporary files for the current user."""
    
    try:
        file_service = FileStorageService(db)
        files = file_service.get_user_files(
            user_id=current_user.id,
            include_expired=include_expired
        )
        
        file_responses = [
            FileInfoResponse(
                id=file.id,
                original_filename=file.original_filename,
                stored_filename=file.stored_filename,
                file_size=file.file_size,
                file_type=file.file_type,
                file_extension=file.file_extension,
                description=file.description,
                tags=file.tags,
                expires_at=file.expires_at.isoformat(),
                download_count=file.download_count,
                last_accessed_at=file.last_accessed_at.isoformat() if file.last_accessed_at else None,
                created_at=file.created_at.isoformat(),
                access_url=f"/api/v1/files/{file.id}/download?token={file.access_token}"
            )
            for file in files
        ]
        
        return FileListResponse(
            files=file_responses,
            total=len(files)
        )
        
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.get("/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get information about a specific temporary file."""
    
    try:
        file_service = FileStorageService(db)
        temp_file = file_service.get_file(file_id, current_user.id)
        
        if not temp_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="File not found"
            )
        
        return FileInfoResponse(
            id=temp_file.id,
            original_filename=temp_file.original_filename,
            stored_filename=temp_file.stored_filename,
            file_size=temp_file.file_size,
            file_type=temp_file.file_type,
            file_extension=temp_file.file_extension,
            description=temp_file.description,
            tags=temp_file.tags,
            expires_at=temp_file.expires_at.isoformat(),
            download_count=temp_file.download_count,
            last_accessed_at=temp_file.last_accessed_at.isoformat() if temp_file.last_accessed_at else None,
            created_at=temp_file.created_at.isoformat(),
            access_url=f"/api/v1/files/{temp_file.id}/download?token={temp_file.access_token}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    token: str = Query(..., description="Access token for the file"),
    include_metadata: bool = Query(False, description="Include file metadata in response headers"),
    db: Session = Depends(get_session_dependency)
):
    """Download a temporary file using access token."""
    
    try:
        file_service = FileStorageService(db)
        result = file_service.download_file(file_id, token)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="File not found or access denied"
            )
        
        file_path, original_filename = result
        
        # Create response with file content
        response = FileResponse(
            path=file_path,
            filename=original_filename,
            media_type='application/octet-stream'
        )
        
        # Add metadata to response headers if requested
        if include_metadata:
            # Get additional file metadata
            temp_file = file_service.get_file_by_token(file_id, token)
            if temp_file:
                response.headers["X-File-Name"] = temp_file.original_filename
                response.headers["X-File-Type"] = temp_file.file_type or "application/octet-stream"
                response.headers["X-File-Extension"] = temp_file.file_extension or ""
                response.headers["X-File-Size"] = str(temp_file.file_size)
                response.headers["X-File-Description"] = temp_file.description or ""
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Delete a temporary file."""
    
    try:
        file_service = FileStorageService(db)
        success = file_service.delete_file(file_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="File not found"
            )
        
        return {
            "message": "File deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.post("/{file_id}/extend")
async def extend_file_expiry(
    file_id: str,
    additional_hours: int = Form(..., description="Additional hours to extend expiry"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Extend the expiry time of a temporary file."""
    
    if additional_hours < 1 or additional_hours > 168:  # 1 hour to 1 week
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Additional hours must be between 1 and 168"
        )
    
    try:
        file_service = FileStorageService(db)
        success = file_service.extend_file_expiry(file_id, current_user.id, additional_hours)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="File not found"
            )
        
        return {
            "message": f"File expiry extended by {additional_hours} hours"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend file expiry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.get("/stats/overview", response_model=FileStatsResponse)
async def get_storage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get storage statistics for the current user."""
    
    try:
        file_service = FileStorageService(db)
        
        # Get user's files
        user_files = file_service.get_user_files(current_user.id, include_expired=False)
        expired_files = file_service.get_user_files(current_user.id, include_expired=True)
        
        # Calculate user-specific stats
        total_size = sum(file.file_size for file in user_files)
        
        return FileStatsResponse(
            user_stats={
                "active_files": len(user_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "expired_files": len(expired_files) - len(user_files)
            },
            system_limits={
                "max_file_size_mb": file_service.max_file_size_mb,
                "default_expiry_hours": file_service.default_expiry_hours,
                "allowed_file_types": file_service.allowed_file_types
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get storage stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.post("/validate-references")
async def validate_file_references(
    file_references: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Validate file references for agent execution."""
    
    try:
        file_service = FileStorageService(db)
        validation_result = file_service.validate_file_references(
            file_references, 
            current_user.id
        )
        
        return {
            "validation": validation_result
        }
        
    except Exception as e:
        logger.error(f"Failed to validate file references: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


# Admin endpoints (for system maintenance)
@router.get("/admin/stats", include_in_schema=False)
async def get_system_storage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get system-wide storage statistics (admin only)."""
    
    # TODO: Add admin role check
    if current_user.id != 1:  # Temporary admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin access required"
        )
    
    try:
        file_service = FileStorageService(db)
        stats = file_service.get_storage_stats()
        
        return {
            "system_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get system storage stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )


@router.post("/admin/cleanup", include_in_schema=False)
async def cleanup_expired_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Clean up expired files (admin only)."""
    
    # TODO: Add admin role check
    if current_user.id != 1:  # Temporary admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin access required"
        )
    
    try:
        file_service = FileStorageService(db)
        cleaned_count = file_service.cleanup_expired_files()
        
        return {
            "message": f"Cleanup completed",
            "files_removed": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error"
        )
