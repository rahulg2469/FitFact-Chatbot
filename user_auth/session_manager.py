"""
Session Manager for FitFact

Handles JWT-based session management:
- Create sessions after OAuth login
- Validate session tokens
- Refresh tokens
- Clean up expired sessions
"""

import os
import secrets
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Session:
    """Session model"""
    session_id: int
    user_id: int
    session_token: str
    expires_at: datetime
    created_at: datetime
    last_activity: datetime
    is_valid: bool = True
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'is_valid': self.is_valid and not self.is_expired,
        }


class SessionManager:
    """
    Manage user sessions with JWT tokens.
    
    Usage:
        session_mgr = SessionManager()
        
        # Create session after login
        session = session_mgr.create_session(user_id, ip_address)
        
        # Validate token on each request
        user_id = session_mgr.validate_token(token)
        
        # Refresh session
        new_session = session_mgr.refresh_session(old_token)
        
        # Logout
        session_mgr.invalidate_session(token)
    """
    
    # Session configuration
    SESSION_DURATION_HOURS = 24 * 7  # 1 week
    REFRESH_THRESHOLD_HOURS = 24  # Refresh if less than 1 day left
    
    def __init__(self, connection=None):
        self._conn = connection
        self._owns_connection = connection is None
        self._secret_key = os.getenv('JWT_SECRET_KEY', self._generate_secret())
    
    def _generate_secret(self) -> str:
        """Generate a secret key if not configured"""
        # In production, this should be a fixed env variable
        return secrets.token_hex(32)
    
    def _get_connection(self):
        """Get or create database connection"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'fitfact_db'),
                user=os.getenv('DB_USER', 'satya'),
                password=os.getenv('DB_PASSWORD', ''),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
        return self._conn
    
    def close(self):
        """Close connection if we own it"""
        if self._owns_connection and self._conn and not self._conn.closed:
            self._conn.close()
    
    def create_session(self, user_id: int, ip_address: str = None,
                       user_agent: str = None, device_type: str = None) -> Session:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            ip_address: Client IP
            user_agent: Browser user agent
            device_type: 'web', 'mobile', etc.
            
        Returns:
            Session object with token
        """
        conn = self._get_connection()
        
        expires_at = datetime.now() + timedelta(hours=self.SESSION_DURATION_HOURS)
        
        # Generate JWT token
        token_payload = {
            'user_id': user_id,
            'exp': expires_at,
            'iat': datetime.now(),
            'jti': secrets.token_hex(16),  # Unique token ID
        }
        
        session_token = jwt.encode(token_payload, self._secret_key, algorithm='HS256')
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(64)
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO user_sessions 
                    (user_id, session_token, refresh_token, ip_address, user_agent, device_type, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (user_id, session_token, refresh_token, ip_address, 
                      user_agent, device_type, expires_at))
                
                row = cur.fetchone()
                conn.commit()
                
                return Session(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    session_token=row['session_token'],
                    expires_at=row['expires_at'],
                    created_at=row['created_at'],
                    last_activity=row['last_activity'],
                    is_valid=row['is_valid']
                )
                
        except Exception as e:
            conn.rollback()
            raise e
    
    def validate_token(self, token: str, update_activity: bool = True) -> Optional[int]:
        """
        Validate a session token.
        
        Args:
            token: JWT session token
            update_activity: Whether to update last_activity timestamp
            
        Returns:
            user_id if valid, None otherwise
        """
        # First validate JWT structure and signature
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        
        # Check database for valid session
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT user_id, expires_at, is_valid
                FROM user_sessions
                WHERE session_token = %s
            """, (token,))
            
            row = cur.fetchone()
            
            if not row:
                return None
            
            if not row['is_valid']:
                return None
            
            if row['expires_at'] < datetime.now():
                return None
            
            # Update last activity
            if update_activity:
                cur.execute("""
                    UPDATE user_sessions
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE session_token = %s
                """, (token,))
                conn.commit()
            
            return row['user_id']
    
    def get_session(self, token: str) -> Optional[Session]:
        """Get full session object"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM user_sessions WHERE session_token = %s
            """, (token,))
            
            row = cur.fetchone()
            
            if row:
                return Session(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    session_token=row['session_token'],
                    expires_at=row['expires_at'],
                    created_at=row['created_at'],
                    last_activity=row['last_activity'],
                    is_valid=row['is_valid']
                )
            return None
    
    def refresh_session(self, token: str) -> Optional[Session]:
        """
        Refresh a session if it's close to expiring.
        
        Returns:
            New Session if refreshed, None if token invalid
        """
        session = self.get_session(token)
        
        if not session or not session.is_valid or session.is_expired:
            return None
        
        # Check if refresh is needed
        time_left = session.expires_at - datetime.now()
        if time_left > timedelta(hours=self.REFRESH_THRESHOLD_HOURS):
            return session  # No refresh needed
        
        conn = self._get_connection()
        
        # Invalidate old session
        self.invalidate_session(token)
        
        # Create new session
        return self.create_session(session.user_id)
    
    def invalidate_session(self, token: str) -> bool:
        """
        Invalidate a session (logout).
        
        Returns:
            True if session was invalidated
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_sessions
                    SET is_valid = FALSE
                    WHERE session_token = %s
                """, (token,))
                
                invalidated = cur.rowcount > 0
                conn.commit()
                return invalidated
                
        except Exception as e:
            conn.rollback()
            raise e
    
    def invalidate_all_sessions(self, user_id: int) -> int:
        """
        Invalidate all sessions for a user (logout everywhere).
        
        Returns:
            Number of sessions invalidated
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_sessions
                    SET is_valid = FALSE
                    WHERE user_id = %s AND is_valid = TRUE
                """, (user_id,))
                
                count = cur.rowcount
                conn.commit()
                return count
                
        except Exception as e:
            conn.rollback()
            raise e
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions from database.
        
        Returns:
            Number of sessions deleted
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT cleanup_expired_sessions()")
                count = cur.fetchone()[0]
                conn.commit()
                return count
        except:
            conn.rollback()
            return 0
    
    def get_active_sessions(self, user_id: int) -> list:
        """Get all active sessions for a user"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT session_id, created_at, last_activity, 
                       ip_address, user_agent, device_type
                FROM user_sessions
                WHERE user_id = %s AND is_valid = TRUE AND expires_at > CURRENT_TIMESTAMP
                ORDER BY last_activity DESC
            """, (user_id,))
            
            return cur.fetchall()


# Quick test
if __name__ == "__main__":
    print("Session Manager Test")
    print("=" * 50)
    
    try:
        session_mgr = SessionManager()
        
        # Test JWT encoding/decoding
        test_payload = {'user_id': 1, 'test': True}
        token = jwt.encode(test_payload, session_mgr._secret_key, algorithm='HS256')
        decoded = jwt.decode(token, session_mgr._secret_key, algorithms=['HS256'])
        
        print(f"✅ JWT encoding/decoding works")
        print(f"   Token length: {len(token)} chars")
        
        session_mgr.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
