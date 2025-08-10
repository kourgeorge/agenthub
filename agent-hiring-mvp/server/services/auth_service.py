"""Authentication service for user management."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import EmailStr

from ..models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Service for authentication-related operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
        """Authenticate a user with username/email and password."""
        # Try to find user by username or email
        user = db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        if not user:
            return None
        if not AuthService.verify_password(password, user.password):
            return None
        return user
    
    @staticmethod
    def create_user(
        db: Session, 
        email: str, 
        password: str, 
        username: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> User:
        """Create a new user with hashed password."""
        # Auto-generate username from email if not provided
        if not username:
            # Extract username part from email (before @)
            email_username = email.split('@')[0]
            # Ensure uniqueness by adding random suffix if needed
            base_username = email_username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    raise ValueError("Unable to generate unique username")
            username = base_username if counter == 1 else username
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                raise ValueError("Username already registered")
            else:
                raise ValueError("Email already registered")
        
        # Create new user
        hashed_password = AuthService.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_user_password(db: Session, user_id: int, new_password: str) -> bool:
        """Update a user's password."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.password = AuthService.get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    
    @staticmethod
    def update_last_login(db: Session, user_id: int) -> None:
        """Update the user's last login timestamp."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
                    user.last_login_at = datetime.now(timezone.utc)
        db.commit()
    
    @staticmethod
    def verify_email(db: Session, user_id: int) -> bool:
        """Mark a user's email as verified."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """Deactivate a user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
    
    @staticmethod
    def activate_user(db: Session, user_id: int) -> bool:
        """Activate a user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = True
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        return True
