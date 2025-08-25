"""Authentication API endpoints."""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from app.services.auth import (
    auth_service,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenValidationResult
)
from app.services.audit import audit_logger
from app.models.user import User, UserRole
from app.core.security import csrf_manager, security_validator

# Security scheme
security = HTTPBearer()

# Router
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Request/Response models
class LoginRequestModel(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    csrf_token: Optional[str] = None

class LoginResponseModel(BaseModel):
    """Login response model."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    csrf_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: Optional[str] = None

class RefreshRequestModel(BaseModel):
    """Refresh token request model."""
    refresh_token: str

class RefreshResponseModel(BaseModel):
    """Refresh token response model."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: Optional[str] = None

class ChangePasswordRequestModel(BaseModel):
    """Change password request model."""
    old_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    csrf_token: str

class UserInfoResponseModel(BaseModel):
    """User info response model."""
    id: str
    username: str
    email: str
    role: str
    permissions: list
    last_login: Optional[str] = None
    status: str

class CSRFTokenResponseModel(BaseModel):
    """CSRF token response model."""
    csrf_token: str
    expires_in: int

# Helper functions
def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and User-Agent from request."""
    # Get real IP address (considering proxies)
    ip_address = (
        request.headers.get("X-Forwarded-For", "")
        or request.headers.get("X-Real-IP", "")
        or request.client.host
        or "unknown"
    )
    
    # Handle comma-separated IPs from X-Forwarded-For
    if "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "unknown")
    
    return ip_address, user_agent

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None) -> User:
    """Get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token
    validation_result = auth_service.validate_token(credentials.credentials)
    
    if not validation_result.valid:
        # Log failed authentication attempt
        if request:
            ip_address, user_agent = get_client_info(request)
            audit_logger.log_event(
                event_type=audit_logger.AuditEventType.ACCESS_DENIED,
                severity=audit_logger.AuditSeverity.MEDIUM,
                action="token_validation",
                result="failed",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"error": validation_result.error_message}
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation_result.error_message or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return validation_result.user

async def get_current_user_with_csrf(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None) -> User:
    """Get current authenticated user with CSRF validation."""
    user = await get_current_user(credentials, request)
    
    # Get CSRF token from header
    csrf_token = request.headers.get("X-CSRF-Token") if request else None
    
    # Validate CSRF token
    validation_result = auth_service.validate_token(
        credentials.credentials, 
        require_csrf=True, 
        csrf_token=csrf_token
    )
    
    if not validation_result.valid:
        ip_address, user_agent = get_client_info(request)
        audit_logger.log_csrf_attack(ip_address, user_agent, {
            "error": validation_result.error_message,
            "provided_token": csrf_token is not None
        })
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed"
        )
    
    return user

# API endpoints
@router.post("/login", response_model=LoginResponseModel)
async def login(request: Request, login_data: LoginRequestModel):
    """User login endpoint."""
    ip_address, user_agent = get_client_info(request)
    
    # Create login request
    login_request = LoginRequest(
        username=login_data.username,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
        csrf_token=login_data.csrf_token
    )
    
    # Attempt login
    login_response = auth_service.login(login_request)
    
    if login_response.success:
        # Log successful login
        audit_logger.log_login_success(
            user_id=login_response.user_info["id"],
            username=login_response.user_info["username"],
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=login_response.session_id
        )
        
        return LoginResponseModel(
            success=True,
            access_token=login_response.access_token,
            refresh_token=login_response.refresh_token,
            user_info=login_response.user_info,
            session_id=login_response.session_id,
            csrf_token=login_response.csrf_token,
            expires_in=login_response.expires_in,
            message="Login successful"
        )
    else:
        # Log failed login
        audit_logger.log_login_failed(
            username=login_data.username,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=login_response.error_message
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=login_response.error_message or "Login failed"
        )

@router.post("/refresh", response_model=RefreshResponseModel)
async def refresh_token(request: Request, refresh_data: RefreshRequestModel):
    """Refresh access token endpoint."""
    ip_address, user_agent = get_client_info(request)
    
    # Create refresh request
    refresh_request = RefreshTokenRequest(
        refresh_token=refresh_data.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # Attempt token refresh
    refresh_response = auth_service.refresh_token(refresh_request)
    
    if refresh_response.success:
        # Log token refresh
        audit_logger.log_event(
            event_type=audit_logger.AuditEventType.TOKEN_REFRESH,
            severity=audit_logger.AuditSeverity.LOW,
            action="token_refresh",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return RefreshResponseModel(
            success=True,
            access_token=refresh_response.access_token,
            refresh_token=refresh_response.refresh_token,
            expires_in=refresh_response.expires_in,
            message="Token refreshed successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=refresh_response.error_message or "Token refresh failed"
        )

@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user_with_csrf)):
    """User logout endpoint."""
    ip_address, user_agent = get_client_info(request)
    
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        
        # Logout user
        success = auth_service.logout(token)
        
        if success:
            # Log logout
            audit_logger.log_logout(
                user_id=current_user.id,
                username=current_user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id="unknown"  # We could extract this from token if needed
            )
            
            return {"success": True, "message": "Logout successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization header"
        )

@router.post("/logout-all")
async def logout_all_sessions(request: Request, current_user: User = Depends(get_current_user_with_csrf)):
    """Logout from all sessions endpoint."""
    ip_address, user_agent = get_client_info(request)
    
    # Logout from all sessions
    success = auth_service.logout_all_sessions(current_user.id)
    
    if success:
        # Log logout all
        audit_logger.log_event(
            event_type=audit_logger.AuditEventType.LOGOUT,
            severity=audit_logger.AuditSeverity.MEDIUM,
            action="logout_all_sessions",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=current_user.id,
            username=current_user.username
        )
        
        return {"success": True, "message": "Logged out from all sessions"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout from all sessions failed"
        )

@router.get("/me", response_model=UserInfoResponseModel)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserInfoResponseModel(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        permissions=current_user.permissions,
        last_login=current_user.last_login,
        status=current_user.status.value
    )

@router.get("/csrf-token", response_model=CSRFTokenResponseModel)
async def get_csrf_token():
    """Get CSRF token for forms."""
    csrf_token = csrf_manager.generate_csrf_token()
    
    return CSRFTokenResponseModel(
        csrf_token=csrf_token,
        expires_in=3600  # 1 hour
    )

@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequestModel,
    current_user: User = Depends(get_current_user_with_csrf)
):
    """Change user password."""
    ip_address, user_agent = get_client_info(request)
    
    # Change password
    success, message = auth_service.change_password(
        current_user.id,
        password_data.old_password,
        password_data.new_password
    )
    
    # Log password change attempt
    audit_logger.log_password_change(
        user_id=current_user.id,
        username=current_user.username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success
    )
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

@router.get("/sessions")
async def get_user_sessions(current_user: User = Depends(get_current_user)):
    """Get user's active sessions."""
    sessions = auth_service.get_user_sessions(current_user.id)
    
    return {
        "success": True,
        "sessions": sessions,
        "total": len(sessions)
    }

@router.get("/validate")
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate current token."""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value
    }

# Admin-only endpoints
@router.get("/audit/summary")
async def get_audit_summary(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get security audit summary (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    summary = audit_logger.get_security_summary(hours)
    
    return {
        "success": True,
        "summary": summary
    }

@router.get("/audit/events")
async def get_audit_events(
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get audit events (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    if user_id:
        events = audit_logger.get_events_by_user(user_id, limit)
    elif event_type:
        try:
            event_type_enum = audit_logger.AuditEventType(event_type)
            events = audit_logger.get_events_by_type(event_type_enum, limit)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event_type}"
            )
    else:
        # Get recent events
        events = audit_logger._events[-limit:] if len(audit_logger._events) > limit else audit_logger._events
        events = [event.to_dict() for event in reversed(events)]
    
    return {
        "success": True,
        "events": events,
        "total": len(events)
    }