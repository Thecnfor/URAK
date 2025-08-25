"""Security utilities for authentication and authorization."""

import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

import jwt
import bcrypt
from passlib.context import CryptContext
from passlib.hash import pbkdf2_sha256
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityConfig:
    """Security configuration manager."""
    
    def __init__(self, config_path: str = "../docs/authentic/security_config.json"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load security configuration from JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback configuration
            return {
                "jwt": {
                    "secret_key": "fallback-secret-key-change-in-production",
                    "algorithm": "HS256",
                    "access_token_expire_minutes": 30,
                    "refresh_token_expire_hours": 48
                },
                "security_policies": {
                    "max_login_attempts": 5,
                    "lockout_duration_minutes": 30,
                    "session_timeout_hours": 48
                }
            }
    
    @property
    def jwt_secret_key(self) -> str:
        return self._config["jwt"]["secret_key"]
    
    @property
    def jwt_algorithm(self) -> str:
        return self._config["jwt"]["algorithm"]
    
    @property
    def access_token_expire_minutes(self) -> int:
        return self._config["jwt"]["access_token_expire_minutes"]
    
    @property
    def refresh_token_expire_hours(self) -> int:
        return self._config["jwt"]["refresh_token_expire_hours"]
    
    @property
    def max_login_attempts(self) -> int:
        return self._config["security_policies"]["max_login_attempts"]
    
    @property
    def lockout_duration_minutes(self) -> int:
        return self._config["security_policies"]["lockout_duration_minutes"]

# Global security config instance
security_config = SecurityConfig()

class PasswordManager:
    """Advanced password management with multiple hashing algorithms."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def hash_password_pbkdf2(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """Hash password using PBKDF2-SHA256."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # PBKDF2 with SHA-256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode('utf-8'))
        
        # Return base64 encoded hash and salt
        return base64.b64encode(key).decode('utf-8'), base64.b64encode(salt).decode('utf-8')
    
    @staticmethod
    def verify_password_pbkdf2(password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against PBKDF2 hash."""
        try:
            salt_bytes = base64.b64decode(salt.encode('utf-8'))
            expected_hash = base64.b64decode(hashed_password.encode('utf-8'))
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )
            kdf.verify(password.encode('utf-8'), expected_hash)
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a random salt."""
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')

class JWTManager:
    """JWT token management."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=security_config.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
            "iss": "URAK-AUTH-SERVICE",
            "aud": "URAK-USERS"
        })
        
        return jwt.encode(to_encode, security_config.jwt_secret_key, algorithm=security_config.jwt_algorithm)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(hours=security_config.refresh_token_expire_hours)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "iss": "URAK-AUTH-SERVICE",
            "aud": "URAK-USERS"
        })
        
        return jwt.encode(to_encode, security_config.jwt_secret_key, algorithm=security_config.jwt_algorithm)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, 
                security_config.jwt_secret_key, 
                algorithms=[security_config.jwt_algorithm],
                audience="URAK-USERS",
                issuer="URAK-AUTH-SERVICE"
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None

class CSRFManager:
    """CSRF token management."""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token: str, expected_token: str) -> bool:
        """Verify CSRF token."""
        return secrets.compare_digest(token, expected_token)

class DataEncryption:
    """Data encryption utilities."""
    
    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            # Generate key from password
            password = b"your-encryption-password-change-in-production"
            salt = b"stable-salt-for-key-derivation-change-in-prod"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        return self.cipher.encrypt(data.encode('utf-8')).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.cipher.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data."""
        json_str = json.dumps(data, ensure_ascii=False)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data."""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)

class SecurityValidator:
    """Security validation utilities."""
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, List[str]]:
        """Validate password strength according to security policies."""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: List[str]) -> bool:
        """Check if redirect URL is safe."""
        if not url:
            return False
        
        # Check for absolute URLs
        if url.startswith(('http://', 'https://')):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc in allowed_hosts
        
        # Relative URLs are generally safe
        return url.startswith('/')

# Global instances
password_manager = PasswordManager()
jwt_manager = JWTManager()
csrf_manager = CSRFManager()
data_encryption = DataEncryption()
security_validator = SecurityValidator()

# Convenience functions for backward compatibility
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return password_manager.verify_password(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return password_manager.hash_password(password)