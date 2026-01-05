# User Authentication Module
# Google OAuth + User Management for FitFact

from .google_oauth import GoogleOAuth, OAuthConfig
from .user_manager import UserManager, User, UserPreferences
from .session_manager import SessionManager, Session

__all__ = [
    'GoogleOAuth',
    'OAuthConfig', 
    'UserManager',
    'User',
    'UserPreferences',
    'SessionManager',
    'Session',
]
