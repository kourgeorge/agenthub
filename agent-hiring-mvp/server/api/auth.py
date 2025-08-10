"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
import sys
import os

# Add the project root to Python path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import (
    JWT_TOKEN_TYPE,
    ALLOWED_PROFILE_FIELDS,
    AUTH_VERIFY_EMAIL_PATH,
    AUTH_RESET_PASSWORD_PATH
)
from server.database.config import get_session_dependency
from server.models.user import User
from server.middleware.auth import (
    create_access_token, 
    create_refresh_token,
    get_current_user,
    get_current_active_user,
    require_verified_user
)
from server.services.auth_service import AuthService
from server.services.email_service import EmailService
from server.services.token_service import TokenService

router = APIRouter(prefix="/auth", tags=["authentication"])

# Request/Response Models
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    username: str
    email: str
    is_verified: bool

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class RegisterResponse(BaseModel):
    user_id: int
    username: str
    email: str
    message: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_verified: bool
    avatar_url: Optional[str]
    bio: Optional[str]
    website: Optional[str]
    last_login_at: Optional[str]
    created_at: str

@router.post("/register", response_model=RegisterResponse)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_session_dependency)
):
    """Register a new user account."""
    try:
        user = AuthService.create_user(
            db=db,
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name
        )
        
        # Generate verification token and send verification email
        verification_token = TokenService.store_verification_token(register_data.email, user.id)
        verification_url = f"{AUTH_VERIFY_EMAIL_PATH}?token={verification_token}"
        EmailService.send_verification_email(register_data.email, verification_token, verification_url)
        
        # Send welcome email
        EmailService.send_welcome_email(register_data.email, user.username)
        
        return RegisterResponse(
            user_id=user.id,
            username=user.username,
            email=register_data.email,
            message="User registered successfully. Please check your email for verification."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_session_dependency)
):
    """Login with username and password to get JWT tokens."""
    # Authenticate user
    user = AuthService.authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Update last login
    AuthService.update_last_login(db, user.id)
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=JWT_TOKEN_TYPE,
        user_id=user.id,
        username=user.username,
        email=user.email,
        is_verified=user.is_verified
    )

@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_session_dependency)
):
    """Refresh access token using refresh token."""
    from server.middleware.auth import verify_refresh_token
    
    payload = verify_refresh_token(refresh_data.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": user.id})
    
    return RefreshTokenResponse(
        access_token=access_token,
        token_type=JWT_TOKEN_TYPE
    )

@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Change user password."""
    # Verify current password
    if not AuthService.verify_password(password_data.current_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    success = AuthService.update_user_password(db, current_user.id, password_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    return {"message": "Password updated successfully"}

@router.post("/request-password-reset")
def request_password_reset(
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_session_dependency)
):
    """Request a password reset."""
    user = db.query(User).filter(User.email == reset_data.email).first()
    if user:
        # Generate reset token
        reset_token = TokenService.store_reset_token(reset_data.email, user.id)
        
        # Send reset email
        reset_url = f"{AUTH_RESET_PASSWORD_PATH}?token={reset_token}"
        EmailService.send_password_reset_email(reset_data.email, reset_token, reset_url)
        
        # Clean up expired tokens
        TokenService.cleanup_expired_tokens()
    
    # Always return the same message for security
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
def reset_password(
    reset_data: PasswordResetConfirmRequest,
    db: Session = Depends(get_session_dependency)
):
    """Reset password using reset token."""
    # Validate reset token
    token_data = TokenService.validate_reset_token(reset_data.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Update password
    success = AuthService.update_user_password(db, user.id, reset_data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    # Mark token as used
    TokenService.mark_reset_token_used(reset_data.token)
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=UserProfileResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        website=current_user.website,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        created_at=current_user.created_at.isoformat()
    )

@router.put("/profile")
def update_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Update user profile information."""
    # Update allowed fields
    allowed_fields = ALLOWED_PROFILE_FIELDS
    
    for field, value in profile_data.items():
        if field in allowed_fields and hasattr(current_user, field):
            setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Profile updated successfully"}

@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Logout user and invalidate their token."""
    # Blacklist the token to prevent its reuse
    TokenService.blacklist_token(credentials.credentials)
    
    return {"message": "Logged out successfully"}

@router.post("/resend-verification")
def resend_verification_email(
    email: str = Query(..., description="Email to resend verification to"),
    db: Session = Depends(get_session_dependency)
):
    """Resend email verification email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Always return success for security
        return {"message": "If the email exists, a verification email has been sent"}
    
    if user.is_verified:
        return {"message": "Email is already verified"}
    
    # Generate new verification token
    verification_token = TokenService.store_verification_token(email, user.id)
    verification_url = f"{AUTH_VERIFY_EMAIL_PATH}?token={verification_token}"
    EmailService.send_verification_email(email, verification_token, verification_url)
    
    # Clean up expired tokens
    TokenService.cleanup_expired_tokens()
    
    return {"message": "Verification email sent successfully"}

@router.post("/verify-email")
def verify_email(
    token: str = Query(..., description="Email verification token"),
    db: Session = Depends(get_session_dependency)
):
    """Verify user email using verification token."""
    # Validate verification token
    token_data = TokenService.validate_verification_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Mark user as verified
    success = AuthService.verify_email(db, user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )
    
    # Mark token as used
    TokenService.mark_verification_token_used(token)
    
    return {"message": "Email verified successfully"}
