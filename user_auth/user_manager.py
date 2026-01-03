"""
User Manager for FitFact

Handles all user-related database operations:
- Create/update users from Google OAuth
- Manage user preferences
- Track query history
- Handle saved responses
"""

import os
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


@dataclass
class User:
    """User model"""
    user_id: int
    google_id: str
    email: str
    display_name: str
    profile_picture_url: Optional[str] = None
    account_type: str = 'free'
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    total_queries: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        return cls(
            user_id=data.get('user_id'),
            google_id=data.get('google_id'),
            email=data.get('email'),
            display_name=data.get('display_name'),
            profile_picture_url=data.get('profile_picture_url'),
            account_type=data.get('account_type', 'free'),
            is_active=data.get('is_active', True),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            total_queries=data.get('total_queries', 0),
        )
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'google_id': self.google_id,
            'email': self.email,
            'display_name': self.display_name,
            'profile_picture_url': self.profile_picture_url,
            'account_type': self.account_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'total_queries': self.total_queries,
        }


@dataclass
class UserPreferences:
    """User preferences model"""
    user_id: int
    fitness_goals: List[str] = field(default_factory=list)
    experience_level: str = 'intermediate'
    preferred_topics: List[str] = field(default_factory=list)
    response_style: str = 'balanced'
    show_citations: bool = True
    show_study_details: bool = False
    theme: str = 'dark'
    language: str = 'en'
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreferences':
        return cls(
            user_id=data.get('user_id'),
            fitness_goals=data.get('fitness_goals') or [],
            experience_level=data.get('experience_level', 'intermediate'),
            preferred_topics=data.get('preferred_topics') or [],
            response_style=data.get('response_style', 'balanced'),
            show_citations=data.get('show_citations', True),
            show_study_details=data.get('show_study_details', False),
            theme=data.get('theme', 'dark'),
            language=data.get('language', 'en'),
        )
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'fitness_goals': self.fitness_goals,
            'experience_level': self.experience_level,
            'preferred_topics': self.preferred_topics,
            'response_style': self.response_style,
            'show_citations': self.show_citations,
            'show_study_details': self.show_study_details,
            'theme': self.theme,
            'language': self.language,
        }


@dataclass
class QueryHistoryItem:
    """Query history item"""
    history_id: int
    user_id: int
    query_text: str
    response_text: Optional[str]
    papers_used: int
    response_time_ms: int
    was_cached: bool
    created_at: datetime
    is_saved: bool = False
    is_favorite: bool = False


class UserManager:
    """
    Manage user data in PostgreSQL.
    
    Usage:
        manager = UserManager()
        
        # Create or get user from Google OAuth
        user = manager.get_or_create_user(google_user_info)
        
        # Get user preferences
        prefs = manager.get_preferences(user.user_id)
        
        # Update preferences
        manager.update_preferences(user.user_id, {'theme': 'light'})
    """
    
    def __init__(self, connection=None):
        """
        Initialize UserManager.
        
        Args:
            connection: Existing psycopg2 connection, or None to create new
        """
        self._conn = connection
        self._owns_connection = connection is None
    
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
    
    # ==================== USER OPERATIONS ====================
    
    def get_or_create_user(self, google_id: str, email: str, 
                           display_name: str, profile_picture_url: str = None,
                           ip_address: str = None) -> User:
        """
        Get existing user or create new one from Google OAuth data.
        
        Returns:
            User object (existing or newly created)
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Try to find existing user
                cur.execute("""
                    SELECT * FROM users WHERE google_id = %s
                """, (google_id,))
                
                existing = cur.fetchone()
                
                if existing:
                    # Update last login
                    cur.execute("""
                        UPDATE users 
                        SET last_login = CURRENT_TIMESTAMP,
                            login_count = login_count + 1,
                            display_name = COALESCE(%s, display_name),
                            profile_picture_url = COALESCE(%s, profile_picture_url),
                            last_ip_address = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        RETURNING *
                    """, (display_name, profile_picture_url, ip_address, existing['user_id']))
                    
                    updated = cur.fetchone()
                    conn.commit()
                    
                    # Log the login
                    self._log_auth_event(existing['user_id'], 'login_success', ip_address)
                    
                    return User.from_dict(updated)
                
                else:
                    # Create new user
                    cur.execute("""
                        INSERT INTO users (google_id, email, display_name, profile_picture_url, last_ip_address)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *
                    """, (google_id, email, display_name, profile_picture_url, ip_address))
                    
                    new_user = cur.fetchone()
                    
                    # Create default preferences
                    cur.execute("""
                        INSERT INTO user_preferences (user_id)
                        VALUES (%s)
                    """, (new_user['user_id'],))
                    
                    # Create rate limit entry
                    cur.execute("""
                        INSERT INTO user_rate_limits (user_id)
                        VALUES (%s)
                    """, (new_user['user_id'],))
                    
                    conn.commit()
                    
                    # Log account creation
                    self._log_auth_event(new_user['user_id'], 'account_created', ip_address)
                    
                    return User.from_dict(new_user)
                    
        except Exception as e:
            conn.rollback()
            raise e
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            
            if row:
                return User.from_dict(row)
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            
            if row:
                return User.from_dict(row)
            return None
    
    # ==================== PREFERENCES ====================
    
    def get_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM user_preferences WHERE user_id = %s
            """, (user_id,))
            
            row = cur.fetchone()
            if row:
                return UserPreferences.from_dict(row)
            return None
    
    def update_preferences(self, user_id: int, updates: Dict) -> UserPreferences:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            updates: Dict of fields to update
            
        Returns:
            Updated UserPreferences
        """
        conn = self._get_connection()
        
        # Build dynamic update query
        allowed_fields = [
            'fitness_goals', 'experience_level', 'preferred_topics',
            'response_style', 'show_citations', 'show_study_details',
            'theme', 'language', 'age_range', 'weight_unit', 'height_unit'
        ]
        
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = %s")
                values.append(value)
        
        if not set_clauses:
            return self.get_preferences(user_id)
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        
        query = f"""
            UPDATE user_preferences
            SET {', '.join(set_clauses)}
            WHERE user_id = %s
            RETURNING *
        """
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, values)
                row = cur.fetchone()
                conn.commit()
                
                return UserPreferences.from_dict(row)
        except Exception as e:
            conn.rollback()
            raise e
    
    # ==================== QUERY HISTORY ====================
    
    def add_to_history(self, user_id: int, query_text: str, response_text: str,
                       papers_used: int = 0, response_time_ms: int = 0,
                       was_cached: bool = False) -> int:
        """
        Add a query to user's history.
        
        Returns:
            history_id of the new entry
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_query_history 
                    (user_id, query_text, response_text, papers_used, response_time_ms, was_cached)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING history_id
                """, (user_id, query_text, response_text, papers_used, response_time_ms, was_cached))
                
                history_id = cur.fetchone()[0]
                
                # Increment user query count
                cur.execute("SELECT increment_user_queries(%s)", (user_id,))
                
                conn.commit()
                return history_id
                
        except Exception as e:
            conn.rollback()
            raise e
    
    def get_history(self, user_id: int, limit: int = 50, 
                    offset: int = 0) -> List[QueryHistoryItem]:
        """Get user's query history"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT h.*, 
                       s.saved_id IS NOT NULL as is_saved,
                       COALESCE(s.is_favorite, FALSE) as is_favorite
                FROM user_query_history h
                LEFT JOIN user_saved_responses s ON h.history_id = s.history_id
                WHERE h.user_id = %s
                ORDER BY h.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            rows = cur.fetchall()
            return [QueryHistoryItem(**row) for row in rows]
    
    # ==================== SAVED RESPONSES ====================
    
    def save_response(self, user_id: int, history_id: int, 
                      title: str = None, notes: str = None,
                      tags: List[str] = None, is_favorite: bool = False) -> int:
        """Save a response to user's bookmarks"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_saved_responses 
                    (user_id, history_id, title, notes, tags, is_favorite)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, history_id) 
                    DO UPDATE SET 
                        title = COALESCE(EXCLUDED.title, user_saved_responses.title),
                        notes = COALESCE(EXCLUDED.notes, user_saved_responses.notes),
                        tags = COALESCE(EXCLUDED.tags, user_saved_responses.tags),
                        is_favorite = EXCLUDED.is_favorite
                    RETURNING saved_id
                """, (user_id, history_id, title, notes, tags, is_favorite))
                
                saved_id = cur.fetchone()[0]
                conn.commit()
                return saved_id
                
        except Exception as e:
            conn.rollback()
            raise e
    
    def get_saved_responses(self, user_id: int, favorites_only: bool = False) -> List[Dict]:
        """Get user's saved responses"""
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT s.*, h.query_text, h.response_text, h.created_at as query_date
                FROM user_saved_responses s
                JOIN user_query_history h ON s.history_id = h.history_id
                WHERE s.user_id = %s
            """
            
            if favorites_only:
                query += " AND s.is_favorite = TRUE"
            
            query += " ORDER BY s.saved_at DESC"
            
            cur.execute(query, (user_id,))
            return cur.fetchall()
    
    def unsave_response(self, user_id: int, history_id: int) -> bool:
        """Remove a response from saved"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_saved_responses
                    WHERE user_id = %s AND history_id = %s
                """, (user_id, history_id))
                
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
                
        except Exception as e:
            conn.rollback()
            raise e
    
    # ==================== RATE LIMITS ====================
    
    def check_rate_limit(self, user_id: int) -> Dict:
        """
        Check if user is within rate limits.
        
        Returns:
            {'allowed': bool, 'remaining': int, 'reset_time': datetime}
        """
        conn = self._get_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM check_rate_limit(%s)", (user_id,))
            result = cur.fetchone()
            
            return {
                'allowed': result['allowed'],
                'remaining': result['remaining'],
                'reset_time': result['reset_time']
            }
    
    # ==================== AUTH LOGGING ====================
    
    def _log_auth_event(self, user_id: int, event_type: str, 
                        ip_address: str = None, details: Dict = None):
        """Log authentication event"""
        conn = self._get_connection()
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO auth_logs (user_id, event_type, ip_address, details)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, event_type, ip_address, 
                      psycopg2.extras.Json(details) if details else None))
                conn.commit()
        except:
            pass  # Don't fail on logging errors
    
    def log_logout(self, user_id: int, ip_address: str = None):
        """Log user logout"""
        self._log_auth_event(user_id, 'logout', ip_address)


# Quick test
if __name__ == "__main__":
    print("User Manager Test")
    print("=" * 50)
    
    try:
        manager = UserManager()
        
        # Test getting guest user
        guest = manager.get_user_by_email('guest@fitfact.local')
        if guest:
            print(f"✅ Found guest user: {guest.display_name}")
        else:
            print("❌ Guest user not found (run user_schema.sql first)")
        
        manager.close()
        print("\n✅ UserManager connection test passed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. user_schema.sql has been applied")
        print("3. DB credentials in .env are correct")
