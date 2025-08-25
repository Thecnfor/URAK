"""Authentication service layer."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.models.user import User, UserRepository, user_repository
from app.core.security import (
    jwt_manager,
    csrf_manager,
    security_config,
    security_validator
)

@dataclass
class LoginRequest:
    """Login request data."""
    username: str
    password: str
    ip_address: str
    user_agent: str
    csrf_token: Optional[str] = None

@dataclass
class LoginResponse:
    """Login response data."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    csrf_token: Optional[str] = None
    error_message: Optional[str] = None
    expires_in: Optional[int] = None

@dataclass
class TokenValidationResult:
    """Token validation result."""
    valid: bool
    user: Optional[User] = None
    session_id: Optional[str] = None
    error_message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

@dataclass
class RefreshTokenRequest:
    """Refresh token request."""
    refresh_token: str
    ip_address: str
    user_agent: str

@dataclass
class RefreshTokenResponse:
    """Refresh token response."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    error_message: Optional[str] = None

class AuthenticationService:
    """Authentication service for handling login, logout, and token management."""
    
    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or user_repository
        self._active_tokens: Dict[str, Dict[str, Any]] = {}  # In-memory token blacklist
    
    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user and create session."""
        try:
            # Authenticate user
            user = await self.user_repo.authenticate_user(
                request.username,
                request.password,
                request.ip_address,
                request.user_agent
            )
            
            if not user:
                return LoginResponse(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Create session
            session = await self.user_repo.create_session(
                user,
                request.ip_address,
                request.user_agent
            )
            
            # Generate tokens
            token_data = {
                "sub": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions,
                "session_id": session.session_id
            }
            
            access_token = jwt_manager.create_access_token(token_data)
            refresh_token = jwt_manager.create_refresh_token({"sub": user.id, "session_id": session.session_id})
            
            # Generate CSRF token
            csrf_token = csrf_manager.generate_csrf_token()
            session.csrf_token = csrf_token
            
            # Update user with session info
            await self.user_repo.update_user(user)
            
            # Store token info for tracking
            self._active_tokens[access_token] = {
                "user_id": user.id,
                "session_id": session.session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "ip_address": request.ip_address,
                "user_agent": request.user_agent
            }
            
            # Prepare user info (exclude sensitive data)
            user_info = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions,
                "last_login": user.last_login,
                "status": user.status
            }
            
            return LoginResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                user_info=user_info,
                session_id=session.session_id,
                csrf_token=csrf_token,
                expires_in=security_config.access_token_expire_minutes * 60
            )
            
        except Exception as e:
            return LoginResponse(
                success=False,
                error_message=f"Login failed: {str(e)}"
            )
    
    async def validate_token(self, token: str, require_csrf: bool = False, csrf_token: str = None) -> TokenValidationResult:
        """Validate access token and return user information."""
        try:
            # Check if token is blacklisted
            if token in self._active_tokens and self._active_tokens[token].get("blacklisted"):
                return TokenValidationResult(
                    valid=False,
                    error_message="Token has been revoked"
                )
            
            # Verify JWT token
            payload = jwt_manager.verify_token(token, "access")
            if not payload:
                return TokenValidationResult(
                    valid=False,
                    error_message="Invalid or expired token"
                )
            
            # Get user
            user = await self.user_repo.get_user_by_id(payload["sub"])
            if not user:
                return TokenValidationResult(
                    valid=False,
                    error_message="User not found"
                )
            
            # Check user status
            can_login, reason = user.can_login()
            if not can_login:
                return TokenValidationResult(
                    valid=False,
                    error_message=reason
                )
            
            # Validate session
            session_id = payload.get("session_id")
            if session_id:
                session = await self.user_repo.get_session(session_id)
                if not session or not session.is_active:
                    return TokenValidationResult(
                        valid=False,
                        error_message="Session is invalid or expired"
                    )
                
                # Update session activity
                session.last_activity = datetime.now(timezone.utc)
                await self.user_repo.update_session(session)
                
                # Validate CSRF token if required
                if require_csrf:
                    if not csrf_token or not session.csrf_token:
                        return TokenValidationResult(
                            valid=False,
                            error_message="CSRF token required"
                        )
                    
                    if not csrf_manager.verify_csrf_token(csrf_token, session.csrf_token):
                        return TokenValidationResult(
                            valid=False,
                            error_message="Invalid CSRF token"
                        )
            
            return TokenValidationResult(
                valid=True,
                user=user,
                session_id=session_id,
                payload=payload
            )
            
        except Exception as e:
            return TokenValidationResult(
                valid=False,
                error_message=f"Token validation failed: {str(e)}"
            )
    
    def refresh_token(self, request: RefreshTokenRequest) -> RefreshTokenResponse:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = jwt_manager.verify_token(request.refresh_token, "refresh")
            if not payload:
                return RefreshTokenResponse(
                    success=False,
                    error_message="Invalid or expired refresh token"
                )
            
            # Get user
            user = self.user_repo.get_user_by_id(payload["sub"])
            if not user:
                return RefreshTokenResponse(
                    success=False,
                    error_message="User not found"
                )
            
            # Check user status
            can_login, reason = user.can_login()
            if not can_login:
                return RefreshTokenResponse(
                    success=False,
                    error_message=reason
                )
            
            # Validate session
            session_id = payload.get("session_id")
            if session_id:
                session = user.get_session(session_id)
                if not session or not session.is_active:
                    return RefreshTokenResponse(
                        success=False,
                        error_message="Session is invalid or expired"
                    )
                
                # Update session activity
                session.last_activity = datetime.now(timezone.utc).isoformat()
                session.ip_address = request.ip_address
                session.user_agent = request.user_agent
            
            # Generate new tokens
            token_data = {
                "sub": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "permissions": user.permissions,
                "session_id": session_id
            }
            
            new_access_token = jwt_manager.create_access_token(token_data)
            new_refresh_token = jwt_manager.create_refresh_token({"sub": user.id, "session_id": session_id})
            
            # Update user
            self.user_repo.update_user(user)
            
            # Store new token info
            self._active_tokens[new_access_token] = {
                "user_id": user.id,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "ip_address": request.ip_address,
                "user_agent": request.user_agent
            }
            
            return RefreshTokenResponse(
                success=True,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=security_config.access_token_expire_minutes * 60
            )
            
        except Exception as e:
            return RefreshTokenResponse(
                success=False,
                error_message=f"Token refresh failed: {str(e)}"
            )
    
    async def logout(self, token: str, session_id: Optional[str] = None) -> bool:
        """Logout user and invalidate session."""
        try:
            # Validate token to get user info
            validation_result = await self.validate_token(token)
            if not validation_result.valid:
                return False
            
            user = validation_result.user
            target_session_id = session_id or validation_result.session_id
            
            # Invalidate session
            if target_session_id:
                user.invalidate_session(target_session_id)
                self.user_repo.update_user(user)
            
            # Blacklist token
            if token in self._active_tokens:
                self._active_tokens[token]["blacklisted"] = True
                self._active_tokens[token]["blacklisted_at"] = datetime.now(timezone.utc).isoformat()
            
            return True
            
        except Exception as e:
            print(f"Logout failed: {e}")
            return False
    
    def logout_all_sessions(self, user_id: str) -> bool:
        """Logout user from all sessions."""
        try:
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return False
            
            # Invalidate all sessions
            user.invalidate_all_sessions()
            self.user_repo.update_user(user)
            
            # Blacklist all tokens for this user
            for token, token_info in self._active_tokens.items():
                if token_info["user_id"] == user_id and not token_info.get("blacklisted"):
                    token_info["blacklisted"] = True
                    token_info["blacklisted_at"] = datetime.now(timezone.utc).isoformat()
            
            return True
            
        except Exception as e:
            print(f"Logout all sessions failed: {e}")
            return False
    
    def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            return []
        
        # Clean up expired sessions first
        user.cleanup_expired_sessions()
        self.user_repo.update_user(user)
        
        # Return active sessions (exclude sensitive data)
        sessions = []
        for session in user.active_sessions:
            if session.is_active:
                sessions.append({
                    "session_id": session.session_id,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent
                })
        
        return sessions
    
    def cleanup_expired_tokens(self):
        """Clean up expired tokens from memory."""
        current_time = datetime.now(timezone.utc)
        expired_tokens = []
        
        for token, token_info in self._active_tokens.items():
            created_at = datetime.fromisoformat(token_info["created_at"].replace('Z', '+00:00'))
            # Remove tokens older than 48 hours
            if current_time - created_at > timedelta(hours=48):
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self._active_tokens[token]
    
    def get_csrf_token(self, session_id: str) -> Optional[str]:
        """Get CSRF token for a session."""
        # Find user with this session
        for user in self.user_repo.get_all_users():
            session = user.get_session(session_id)
            if session and session.is_active:
                return session.csrf_token
        return None
    
    def validate_password_strength(self, password: str) -> Tuple[bool, list]:
        """Validate password strength."""
        return security_validator.validate_password_strength(password)
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password."""
        try:
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Verify old password
            from app.core.security import password_manager
            if not password_manager.verify_password_pbkdf2(old_password, user.password_hash, user.salt):
                return False, "Current password is incorrect"
            
            # Validate new password strength
            is_strong, errors = self.validate_password_strength(new_password)
            if not is_strong:
                return False, "; ".join(errors)
            
            # Hash new password
            new_hash, new_salt = password_manager.hash_password_pbkdf2(new_password)
            
            # Update user
            user.password_hash = new_hash
            user.salt = new_salt
            user.password_changed_at = datetime.now(timezone.utc).isoformat()
            
            # Invalidate all sessions (force re-login)
            user.invalidate_all_sessions()
            
            self.user_repo.update_user(user)
            
            return True, "Password changed successfully"
            
        except Exception as e:
            return False, f"Password change failed: {str(e)}"

# Global authentication service instance
auth_service = AuthenticationService()


# FastAPI Dependencies
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    # Validate token
    validation_result = await auth_service.validate_token(token)
    
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation_result.error_message or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not validation_result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return validation_result.user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin role for the current user."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None