# Authentication System Documentation

## Overview
This document describes the authentication system implemented for the AgentHub project. The system provides comprehensive user authentication including registration, login, password management, and email verification.

## Features

### Core Authentication
- **User Registration**: Secure user account creation with email verification
- **User Login**: JWT-based authentication with access and refresh tokens
- **Password Management**: Secure password hashing using bcrypt
- **Password Reset**: Secure password reset via email tokens
- **Email Verification**: Email verification for new accounts
- **Token Refresh**: Automatic token refresh using refresh tokens
- **User Logout**: Secure logout with token invalidation

### Security Features
- **Password Hashing**: Bcrypt with configurable rounds
- **JWT Tokens**: Secure token-based authentication
- **Token Expiration**: Configurable token lifetimes
- **Rate Limiting**: Built-in protection against brute force attacks
- **Secure Headers**: CORS and security middleware

## Database Initialization

### Concurrent Access Handling
The database initialization system has been enhanced to handle concurrent access scenarios that commonly occur when running multiple Uvicorn workers:

- **Safe Initialization**: `safe_init_database()` function prevents race conditions
- **Duplicate Check**: `is_database_initialized()` verifies database state before initialization
- **Error Handling**: Gracefully handles "table already exists" errors
- **Worker Safety**: Multiple workers can safely initialize the database simultaneously

### Key Functions
- `init_database()`: Main initialization function (calls safe_init_database)
- `safe_init_database()`: Thread-safe database initialization
- `is_database_initialized()`: Check if database is already initialized
- `get_current_session()`: Get a fresh database session
- `reset_database()`: Safely reset and recreate database schema

## API Endpoints

### Authentication Endpoints
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/request-password-reset` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `POST /api/v1/auth/verify-email` - Verify email address
- `POST /api/v1/auth/resend-verification` - Resend verification email

### Protected Endpoints
- `GET /api/v1/auth/me` - Get current user info
- `PUT /api/v1/auth/profile` - Update user profile

## Configuration

### Environment Variables
```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Configuration
PASSWORD_MIN_LENGTH=8
BCRYPT_ROUNDS=12

# Email Configuration (placeholder)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
```

## Usage Examples

### User Registration
```python
from server.services.auth_service import AuthService

# Create a new user
user_data = {
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
}

auth_service = AuthService()
user = auth_service.create_user(user_data)
```

### User Authentication
```python
from server.services.auth_service import AuthService

# Authenticate user
auth_service = AuthService()
user = auth_service.authenticate_user("user@example.com", "securepassword123")
```

## Testing

### Run Authentication Tests
```bash
cd agent-hiring-mvp
python test_auth.py
```

### Test Database Initialization
```bash
cd agent-hiring-mvp
python test_db_init.py
```

## Troubleshooting

### Common Issues
1. **Database Connection Errors**: Ensure database file exists and is writable
2. **JWT Token Errors**: Verify JWT_SECRET_KEY is set correctly
3. **Password Hashing Errors**: Check bcrypt installation and configuration
4. **Concurrent Access Errors**: The system now handles this automatically

### Database Initialization Issues
If you encounter "table already exists" errors:
- The system now handles this automatically
- Multiple workers can safely initialize the database
- Use `safe_init_database()` for concurrent scenarios
- Check logs for initialization status

## Security Considerations

### Production Deployment
- Use strong, unique JWT_SECRET_KEY
- Enable HTTPS in production
- Configure proper CORS origins
- Implement rate limiting
- Use secure database connections
- Regular security audits

### Password Security
- Passwords are hashed using bcrypt
- Configurable hash rounds for performance/security balance
- Password reset tokens have limited lifetime
- Email verification required for account activation

## Future Enhancements

### Planned Features
- Two-factor authentication (2FA)
- OAuth integration (Google, GitHub, etc.)
- Role-based access control (RBAC)
- Session management
- Audit logging
- Account lockout after failed attempts

### Integration Points
- Email service integration (SMTP/SendGrid)
- Redis for token storage
- Database connection pooling
- Monitoring and alerting
