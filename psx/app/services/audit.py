"""Audit logging service for security events."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

class AuditEventType(str, Enum):
    """Audit event types."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_ESCALATION = "permission_escalation"
    
    # Data events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    
    # Security events
    CSRF_ATTACK_DETECTED = "csrf_attack_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIGURATION_CHANGE = "configuration_change"
    ERROR_OCCURRED = "error_occurred"

class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Audit event data structure."""
    id: str
    timestamp: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    username: Optional[str]
    ip_address: str
    user_agent: str
    resource: Optional[str]
    action: str
    result: str  # success, failed, denied
    details: Dict[str, Any]
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary."""
        if 'event_type' in data:
            data['event_type'] = AuditEventType(data['event_type'])
        if 'severity' in data:
            data['severity'] = AuditSeverity(data['severity'])
        return cls(**data)

class AuditLogger:
    """Audit logging service."""
    
    def __init__(self, log_path: str = "../docs/authentic/audit_logs.json"):
        self.log_path = Path(log_path)
        self._events: List[AuditEvent] = []
        self._load_events()
        
        # Security thresholds
        self.failed_login_threshold = 5
        self.suspicious_activity_threshold = 10
        
    def _load_events(self):
        """Load existing audit events."""
        try:
            if self.log_path.exists():
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for event_data in data.get('events', []):
                    event = AuditEvent.from_dict(event_data)
                    self._events.append(event)
                    
        except Exception as e:
            print(f"Error loading audit events: {e}")
    
    def _save_events(self):
        """Save audit events to file."""
        try:
            # Ensure directory exists
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only last 10000 events to prevent file from growing too large
            events_to_save = self._events[-10000:] if len(self._events) > 10000 else self._events
            
            data = {
                "events": [event.to_dict() for event in events_to_save],
                "metadata": {
                    "total_events": len(events_to_save),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0"
                }
            }
            
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving audit events: {e}")
    
    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        result: str,
        ip_address: str,
        user_agent: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log an audit event."""
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            session_id=session_id,
            request_id=request_id
        )
        
        self._events.append(event)
        self._save_events()
        
        # Check for suspicious patterns
        self._analyze_security_patterns(event)
    
    def log_login_success(self, user_id: str, username: str, ip_address: str, user_agent: str, session_id: str):
        """Log successful login."""
        self.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            action="user_login",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            username=username,
            session_id=session_id,
            details={
                "login_method": "password",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_login_failed(self, username: str, ip_address: str, user_agent: str, reason: str):
        """Log failed login attempt."""
        self.log_event(
            event_type=AuditEventType.LOGIN_FAILED,
            severity=AuditSeverity.MEDIUM,
            action="user_login",
            result="failed",
            ip_address=ip_address,
            user_agent=user_agent,
            username=username,
            details={
                "failure_reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_logout(self, user_id: str, username: str, ip_address: str, user_agent: str, session_id: str):
        """Log user logout."""
        self.log_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.LOW,
            action="user_logout",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            username=username,
            session_id=session_id
        )
    
    def log_access_denied(self, user_id: str, username: str, resource: str, ip_address: str, user_agent: str, reason: str):
        """Log access denied event."""
        self.log_event(
            event_type=AuditEventType.ACCESS_DENIED,
            severity=AuditSeverity.MEDIUM,
            action="access_attempt",
            result="denied",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            username=username,
            resource=resource,
            details={
                "denial_reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_csrf_attack(self, ip_address: str, user_agent: str, details: Dict[str, Any]):
        """Log CSRF attack attempt."""
        self.log_event(
            event_type=AuditEventType.CSRF_ATTACK_DETECTED,
            severity=AuditSeverity.HIGH,
            action="csrf_attack",
            result="blocked",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
    
    def log_rate_limit_exceeded(self, ip_address: str, user_agent: str, endpoint: str):
        """Log rate limit exceeded."""
        self.log_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.MEDIUM,
            action="rate_limit_check",
            result="exceeded",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=endpoint,
            details={
                "endpoint": endpoint,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_password_change(self, user_id: str, username: str, ip_address: str, user_agent: str, success: bool):
        """Log password change attempt."""
        self.log_event(
            event_type=AuditEventType.PASSWORD_CHANGE,
            severity=AuditSeverity.MEDIUM,
            action="password_change",
            result="success" if success else "failed",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            username=username
        )
    
    def log_account_locked(self, user_id: str, username: str, ip_address: str, reason: str):
        """Log account lockout."""
        self.log_event(
            event_type=AuditEventType.ACCOUNT_LOCKED,
            severity=AuditSeverity.HIGH,
            action="account_lockout",
            result="locked",
            ip_address=ip_address,
            user_agent="system",
            user_id=user_id,
            username=username,
            details={
                "lockout_reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_data_access(self, user_id: str, username: str, resource: str, ip_address: str, user_agent: str):
        """Log data access."""
        self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.LOW,
            action="data_access",
            result="success",
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            username=username,
            resource=resource
        )
    
    def log_security_violation(self, ip_address: str, user_agent: str, violation_type: str, details: Dict[str, Any]):
        """Log security violation."""
        self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity.CRITICAL,
            action="security_check",
            result="violation",
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "violation_type": violation_type,
                **details
            }
        )
    
    def _analyze_security_patterns(self, event: AuditEvent):
        """Analyze events for suspicious patterns."""
        # Check for multiple failed logins from same IP
        if event.event_type == AuditEventType.LOGIN_FAILED:
            recent_failures = self._get_recent_events_by_ip(
                event.ip_address, 
                AuditEventType.LOGIN_FAILED, 
                minutes=30
            )
            
            if len(recent_failures) >= self.failed_login_threshold:
                self.log_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    severity=AuditSeverity.HIGH,
                    action="pattern_analysis",
                    result="detected",
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    details={
                        "pattern_type": "multiple_failed_logins",
                        "failure_count": len(recent_failures),
                        "time_window_minutes": 30
                    }
                )
    
    def _get_recent_events_by_ip(self, ip_address: str, event_type: AuditEventType, minutes: int) -> List[AuditEvent]:
        """Get recent events from specific IP."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        recent_events = []
        for event in reversed(self._events):  # Start from most recent
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            
            if event_time < cutoff_time:
                break
                
            if event.ip_address == ip_address and event.event_type == event_type:
                recent_events.append(event)
        
        return recent_events
    
    def get_events_by_user(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit events for a specific user."""
        user_events = []
        for event in reversed(self._events):
            if event.user_id == user_id:
                user_events.append(event.to_dict())
                if len(user_events) >= limit:
                    break
        
        return user_events
    
    def get_events_by_type(self, event_type: AuditEventType, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit events by type."""
        type_events = []
        for event in reversed(self._events):
            if event.event_type == event_type:
                type_events.append(event.to_dict())
                if len(type_events) >= limit:
                    break
        
        return type_events
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the last N hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        summary = {
            "time_period_hours": hours,
            "total_events": 0,
            "login_attempts": {"success": 0, "failed": 0},
            "access_denied": 0,
            "security_violations": 0,
            "suspicious_activities": 0,
            "top_ips": {},
            "event_types": {}
        }
        
        for event in reversed(self._events):
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            
            if event_time < cutoff_time:
                break
            
            summary["total_events"] += 1
            
            # Count by event type
            event_type_str = event.event_type.value
            summary["event_types"][event_type_str] = summary["event_types"].get(event_type_str, 0) + 1
            
            # Count login attempts
            if event.event_type == AuditEventType.LOGIN_SUCCESS:
                summary["login_attempts"]["success"] += 1
            elif event.event_type == AuditEventType.LOGIN_FAILED:
                summary["login_attempts"]["failed"] += 1
            
            # Count access denied
            if event.event_type == AuditEventType.ACCESS_DENIED:
                summary["access_denied"] += 1
            
            # Count security violations
            if event.event_type == AuditEventType.SECURITY_VIOLATION:
                summary["security_violations"] += 1
            
            # Count suspicious activities
            if event.event_type == AuditEventType.SUSPICIOUS_ACTIVITY:
                summary["suspicious_activities"] += 1
            
            # Count by IP
            ip = event.ip_address
            summary["top_ips"][ip] = summary["top_ips"].get(ip, 0) + 1
        
        # Sort top IPs
        summary["top_ips"] = dict(sorted(summary["top_ips"].items(), key=lambda x: x[1], reverse=True)[:10])
        
        return summary
    
    def cleanup_old_events(self, days: int = 90):
        """Remove events older than specified days."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        filtered_events = []
        for event in self._events:
            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            if event_time >= cutoff_time:
                filtered_events.append(event)
        
        self._events = filtered_events
        self._save_events()
        
        return len(self._events)

# Global audit logger instance
audit_logger = AuditLogger()