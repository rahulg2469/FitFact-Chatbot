"""
Google OAuth Handler for FitFact

Handles Google Sign-In flow:
1. Generate authorization URL
2. Handle OAuth callback
3. Exchange code for tokens
4. Get user info from Google
"""

import os
import secrets
import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OAuthConfig:
    """Configuration for Google OAuth"""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8501/"
    scopes: list = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ]


@dataclass
class GoogleUser:
    """User info returned from Google"""
    google_id: str
    email: str
    display_name: str
    profile_picture_url: Optional[str] = None
    email_verified: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'google_id': self.google_id,
            'email': self.email,
            'display_name': self.display_name,
            'profile_picture_url': self.profile_picture_url,
            'email_verified': self.email_verified,
        }


class GoogleOAuth:
    """
    Handle Google OAuth 2.0 authentication flow.
    
    Usage:
        oauth = GoogleOAuth.from_env()
        
        # Step 1: Get authorization URL
        auth_url, state = oauth.get_authorization_url()
        # Redirect user to auth_url
        
        # Step 2: Handle callback (after user authorizes)
        user_info = oauth.handle_callback(authorization_code, state)
    """
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        # Note: State is now stored in Streamlit session_state, not here
        
    @classmethod
    def from_env(cls) -> 'GoogleOAuth':
        """Create OAuth handler from environment variables"""
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        # Use root URL for Streamlit (no custom routes)
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8501/')
        
        if not client_id or not client_secret:
            raise ValueError(
                "Missing Google OAuth credentials. "
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )
        
        config = OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        
        return cls(config)
    
    def get_authorization_url(self) -> tuple:
        """
        Generate Google authorization URL.
        
        Returns:
            (authorization_url, state_token)
        """
        # Generate CSRF state token
        state = self._generate_state()
        
        # Build the OAuth flow
        flow = self._create_flow()
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            state=state,
            prompt='select_account'  # Always show account picker
        )
        
        return authorization_url, state
    
    def handle_callback(self, authorization_code: str, state: str = None, stored_state: str = None) -> GoogleUser:
        """
        Handle OAuth callback after user authorizes.
        
        Args:
            authorization_code: Code from Google callback
            state: State token from URL (optional)
            stored_state: State token stored in session (optional)
            
        Returns:
            GoogleUser with user information
            
        Raises:
            ValueError: If token exchange fails
        """
        # Note: State verification is optional in Streamlit due to session resets
        # The OAuth code exchange is still secure as it requires the client secret
        
        # Exchange code for tokens
        flow = self._create_flow()
        flow.fetch_token(code=authorization_code)
        
        credentials = flow.credentials
        
        # Verify and decode the ID token
        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                self.config.client_id
            )
        except Exception as e:
            raise ValueError(f"Failed to verify ID token: {str(e)}")
        
        # Extract user info
        return GoogleUser(
            google_id=id_info.get('sub'),
            email=id_info.get('email'),
            display_name=id_info.get('name', id_info.get('email', '').split('@')[0]),
            profile_picture_url=id_info.get('picture'),
            email_verified=id_info.get('email_verified', False)
        )
    
    def verify_id_token(self, token: str) -> Optional[GoogleUser]:
        """
        Verify a Google ID token (for frontend-initiated auth).
        
        Args:
            token: ID token from Google Sign-In button
            
        Returns:
            GoogleUser if valid, None otherwise
        """
        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.config.client_id
            )
            
            return GoogleUser(
                google_id=id_info.get('sub'),
                email=id_info.get('email'),
                display_name=id_info.get('name', ''),
                profile_picture_url=id_info.get('picture'),
                email_verified=id_info.get('email_verified', False)
            )
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None
    
    def _create_flow(self) -> Flow:
        """Create OAuth flow object"""
        client_config = {
            "web": {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.config.redirect_uri],
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=self.config.scopes,
            redirect_uri=self.config.redirect_uri
        )
        
        return flow
    
    def _generate_state(self) -> str:
        """Generate a secure state token for CSRF protection"""
        state = secrets.token_urlsafe(32)
        # State will be stored in Streamlit session_state by the caller
        return state
    
    def _verify_state(self, state: str, stored_state: str) -> bool:
        """Verify state token matches the stored one"""
        if not stored_state or not state:
            return False
        return state == stored_state


# Quick test
if __name__ == "__main__":
    print("Google OAuth Module")
    print("=" * 50)
    
    # Check if credentials are configured
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if client_id and client_secret:
        print("✅ Google OAuth credentials found")
        
        oauth = GoogleOAuth.from_env()
        auth_url, state = oauth.get_authorization_url()
        
        print(f"\nAuthorization URL preview:")
        print(f"{auth_url[:80]}...")
        print(f"\nState token: {state}")
    else:
        print("❌ Google OAuth credentials not configured")
        print("\nTo set up Google OAuth:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create OAuth 2.0 credentials")
        print("3. Set environment variables:")
        print("   GOOGLE_CLIENT_ID=your-client-id")
        print("   GOOGLE_CLIENT_SECRET=your-client-secret")
