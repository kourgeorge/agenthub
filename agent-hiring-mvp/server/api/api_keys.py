"""API endpoints for managing user API keys."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from ..database.config import get_session_dependency
from ..middleware.auth import get_current_user
from ..models.user import User
from ..models.user_api_key import UserApiKey
from ..services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class CreateApiKeyRequest(BaseModel):
    """Request model for creating an API key."""
    name: str
    expires_in_days: Optional[int] = None
    permissions: Optional[str] = None


class ToggleApiKeyStatusRequest(BaseModel):
    """Request model for toggling API key status."""
    is_active: bool


class ApiKeyResponse(BaseModel):
    """Response model for API key data."""
    id: int
    name: str
    key_prefix: str
    is_active: bool
    permissions: Optional[str]
    last_used_at: Optional[str]
    usage_count: int
    expires_at: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True
    
    @field_validator('created_at', 'updated_at', 'last_used_at', 'expires_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        if v is None:
            # For optional fields, return None when None
            return None
        if isinstance(v, str):
            return v
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return str(v)


class CreateApiKeyResponse(BaseModel):
    """Response model for newly created API key."""
    api_key: ApiKeyResponse
    full_key: str  # Only shown once upon creation


@router.post("/", response_model=CreateApiKeyResponse)
def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Create a new API key for the current user."""
    print(f"DEBUG: Creating API key for user {current_user.id} with name '{request.name}'")
    print(f"DEBUG: Request data: {request}")
    print(f"DEBUG: Database session: {db}")
    
    try:
        print("DEBUG: About to call ApiKeyService.create_api_key")
        api_key, full_key = ApiKeyService.create_api_key(
            db=db,
            user_id=current_user.id,
            name=request.name,
            expires_in_days=request.expires_in_days,
            permissions=request.permissions
        )
        print(f"DEBUG: Successfully created API key with ID {api_key.id}")
        
        return CreateApiKeyResponse(
            api_key=ApiKeyResponse.model_validate(api_key),
            full_key=full_key
        )
    except Exception as e:
        print(f"DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/", response_model=List[ApiKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """List all API keys for the current user."""
    print(f"DEBUG: Listing API keys for user {current_user.id}")
    print(f"DEBUG: Database session: {db}")
    
    try:
        print("DEBUG: About to call ApiKeyService.get_user_api_keys")
        api_keys = ApiKeyService.get_user_api_keys(db, current_user.id)
        print(f"DEBUG: Successfully fetched {len(api_keys)} API keys")
        return [ApiKeyResponse.model_validate(key) for key in api_keys]
    except Exception as e:
        print(f"DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.get("/{key_id}", response_model=ApiKeyResponse)
def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get a specific API key by ID."""
    try:
        api_keys = ApiKeyService.get_user_api_keys(db, current_user.id)
        api_key = next((key for key in api_keys if key.id == key_id), None)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return ApiKeyResponse.model_validate(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key: {str(e)}"
        )


@router.put("/{key_id}", response_model=ApiKeyResponse)
def update_api_key(
    key_id: int,
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Update an API key."""
    try:
        api_key = ApiKeyService.update_api_key(
            db=db,
            user_id=current_user.id,
            key_id=key_id,
            name=request.name,
            permissions=request.permissions
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return ApiKeyResponse.model_validate(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API key: {str(e)}"
        )


@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Delete an API key."""
    try:
        success = ApiKeyService.delete_api_key(db, current_user.id, key_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(e)}"
        )


@router.post("/{key_id}/deactivate")
def deactivate_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Deactivate an API key (soft delete)."""
    try:
        success = ApiKeyService.deactivate_api_key(db, current_user.id, key_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate API key: {str(e)}"
        )


@router.patch("/{key_id}/toggle-status", response_model=ApiKeyResponse)
def toggle_api_key_status(
    key_id: int,
    request: ToggleApiKeyStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Toggle API key active/inactive status."""
    try:
        api_key = ApiKeyService.update_api_key(
            db=db,
            user_id=current_user.id,
            key_id=key_id,
            is_active=request.is_active
        )
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return ApiKeyResponse.model_validate(api_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle API key status: {str(e)}"
        )
