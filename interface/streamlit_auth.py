"""
Streamlit Authentication Components for FitFact

Provides:
- Google Sign-In button and flow
- User profile display
- Session management in Streamlit
- Sign-in prompt popup
"""

import streamlit as st
import os
import sys
from typing import Optional, Callable
from urllib.parse import urlencode, parse_qs, urlparse

# Add parent path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from user_auth import GoogleOAuth, UserManager, SessionManager, User, UserPreferences


class StreamlitAuth:
    """
    Handle authentication in Streamlit.
    
    Usage:
        auth = StreamlitAuth()
        
        # In sidebar
        auth.render_auth_section()
        
        # Check if logged in
        if auth.is_authenticated:
            user = auth.current_user
            
        # Show sign-in prompt
        auth.show_signin_prompt()
    """
    
    def __init__(self):
        self._init_session_state()
        self._oauth = None
        self._user_mgr = None
        self._session_mgr = None
    
    def _init_session_state(self):
        """Initialize Streamlit session state for auth"""
        if 'auth_initialized' not in st.session_state:
            st.session_state.auth_initialized = True
            st.session_state.user = None
            st.session_state.session_token = None
            st.session_state.is_authenticated = False
            st.session_state.oauth_state = None
            st.session_state.show_signin_prompt = False
            st.session_state.signin_prompt_dismissed = False
            st.session_state.message_count = 0
            st.session_state.preferences = None
    
    @property
    def oauth(self) -> GoogleOAuth:
        if self._oauth is None:
            try:
                self._oauth = GoogleOAuth.from_env()
            except ValueError as e:
                st.error(f"OAuth not configured: {e}")
                return None
        return self._oauth
    
    @property
    def user_mgr(self) -> UserManager:
        if self._user_mgr is None:
            self._user_mgr = UserManager()
        return self._user_mgr
    
    @property
    def session_mgr(self) -> SessionManager:
        if self._session_mgr is None:
            self._session_mgr = SessionManager()
        return self._session_mgr
    
    @property
    def is_authenticated(self) -> bool:
        return st.session_state.get('is_authenticated', False)
    
    @property
    def current_user(self) -> Optional[User]:
        return st.session_state.get('user')
    
    @property
    def current_preferences(self) -> Optional[UserPreferences]:
        return st.session_state.get('preferences')
    
    def render_auth_section(self):
        """Render the authentication section in sidebar"""
        if self.is_authenticated and self.current_user:
            self._render_user_profile()
        else:
            self._render_login_button()
    
    def _render_user_profile(self):
        """Render logged-in user profile"""
        user = self.current_user
        
        # Profile container
        st.markdown("### 👤 Profile")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if user.profile_picture_url:
                st.image(user.profile_picture_url, width=50)
            else:
                st.markdown("👤")
        
        with col2:
            st.markdown(f"**{user.display_name}**")
            st.caption(user.email)
        
        # Account type badge
        if user.account_type == 'premium':
            st.success("⭐ Premium")
        elif user.account_type == 'admin':
            st.info("🔧 Admin")
        
        # Quick stats
        st.markdown("---")
        stat_col1, stat_col2 = st.columns(2)
        with stat_col1:
            st.metric("Queries", user.total_queries)
        with stat_col2:
            # Get rate limit info
            try:
                rate_info = self.user_mgr.check_rate_limit(user.user_id)
                st.metric("Remaining", rate_info['remaining'])
            except:
                st.metric("Remaining", "∞")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Sign Out", use_container_width=True):
            self._logout()
            st.rerun()
    
    def _render_login_button(self):
        """Render Google Sign-In button"""
        st.markdown("### 🔐 Sign In")
        st.caption("Save your chat history and preferences")
        
        if st.button("🔵 Sign in with Google", use_container_width=True, type="primary"):
            self._initiate_login()
    
    def _initiate_login(self):
        """Start Google OAuth flow"""
        if not self.oauth:
            st.error("Google OAuth not configured")
            return
        
        auth_url, state = self.oauth.get_authorization_url()
        st.session_state.oauth_state = state
        
        # Redirect to Google
        st.markdown(f"""
        <meta http-equiv="refresh" content="0;url={auth_url}">
        <p>Redirecting to Google Sign-In...</p>
        <p>If not redirected, <a href="{auth_url}">click here</a></p>
        """, unsafe_allow_html=True)
        st.stop()
    
    def handle_oauth_callback(self):
        """Handle OAuth callback from Google"""
        # Check for authorization code in URL
        query_params = st.query_params
        
        code = query_params.get('code')
        state = query_params.get('state')
        
        if code and state:
            try:
                # Get stored state from session
                stored_state = st.session_state.get('oauth_state')
                
                # Exchange code for user info
                google_user = self.oauth.handle_callback(code, state, stored_state)
                
                # Create/get user in database
                user = self.user_mgr.get_or_create_user(
                    google_id=google_user.google_id,
                    email=google_user.email,
                    display_name=google_user.display_name,
                    profile_picture_url=google_user.profile_picture_url
                )
                
                # Create session
                session = self.session_mgr.create_session(user.user_id)
                
                # Store in session state
                st.session_state.user = user
                st.session_state.session_token = session.session_token
                st.session_state.is_authenticated = True
                st.session_state.preferences = self.user_mgr.get_preferences(user.user_id)
                
                # Clear URL params
                st.query_params.clear()
                
                st.success(f"Welcome, {user.display_name}!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
                st.query_params.clear()
    
    def _logout(self):
        """Log out current user"""
        if st.session_state.session_token:
            try:
                self.session_mgr.invalidate_session(st.session_state.session_token)
                self.user_mgr.log_logout(st.session_state.user.user_id)
            except:
                pass
        
        # Clear session state
        st.session_state.user = None
        st.session_state.session_token = None
        st.session_state.is_authenticated = False
        st.session_state.preferences = None
        st.session_state.signin_prompt_dismissed = False
    
    def check_signin_prompt(self) -> bool:
        """
        Check if we should show sign-in prompt.
        Returns True if prompt should be shown.
        """
        # Don't show if already authenticated
        if self.is_authenticated:
            return False
        
        # Don't show if user dismissed it
        if st.session_state.get('signin_prompt_dismissed', False):
            return False
        
        # Show after 2nd user message (count user messages in session)
        messages = st.session_state.get('messages', [])
        user_message_count = sum(1 for m in messages if m.get('role') == 'user')
        return user_message_count >= 2
    
    def increment_message_count(self):
        """Increment message counter (call after each user message)"""
        st.session_state.message_count = st.session_state.get('message_count', 0) + 1
    
    def render_signin_prompt(self):
        """Render the sign-in prompt popup"""
        if not self.check_signin_prompt():
            return
        
        # Create a modal-like popup using a container
        with st.container():
            st.markdown("""
            <style>
            .signin-prompt {
                background: linear-gradient(135deg, rgba(30, 40, 60, 0.98) 0%, rgba(40, 50, 70, 0.98) 100%);
                border: 2px solid rgba(100, 120, 180, 0.5);
                border-radius: 15px;
                padding: 1.5rem;
                margin: 1rem 0;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            }
            .signin-prompt h3 {
                color: white;
                margin-bottom: 0.5rem;
            }
            .signin-prompt p {
                color: #b0c4de;
                font-size: 0.95rem;
            }
            </style>
            <div class="signin-prompt">
                <h3>💡 Want to save your conversation?</h3>
                <p>Sign in to save your chat history, bookmark responses, and get personalized recommendations.</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("🔵 Sign in with Google", key="prompt_signin", type="primary"):
                    self._initiate_login()
            
            with col2:
                if st.button("Maybe later", key="prompt_dismiss"):
                    st.session_state.signin_prompt_dismissed = True
                    st.rerun()
    
    def save_query_to_history(self, query: str, response: str, 
                              papers_used: int = 0, response_time_ms: int = 0,
                              was_cached: bool = False) -> Optional[int]:
        """
        Save a query to user's history (only if authenticated).
        
        Returns:
            history_id if saved, None if not authenticated
        """
        if not self.is_authenticated or not self.current_user:
            return None
        
        try:
            history_id = self.user_mgr.add_to_history(
                user_id=self.current_user.user_id,
                query_text=query,
                response_text=response,
                papers_used=papers_used,
                response_time_ms=response_time_ms,
                was_cached=was_cached
            )
            return history_id
        except Exception as e:
            print(f"Failed to save to history: {e}")
            return None
    
    def get_user_history(self, limit: int = 50):
        """Get current user's query history"""
        if not self.is_authenticated or not self.current_user:
            return []
        
        try:
            return self.user_mgr.get_history(self.current_user.user_id, limit=limit)
        except:
            return []


def init_auth() -> StreamlitAuth:
    """
    Initialize authentication for the app.
    Call this at the start of your Streamlit app.
    
    Returns:
        StreamlitAuth instance
    """
    auth = StreamlitAuth()
    
    # Handle OAuth callback if present
    auth.handle_oauth_callback()
    
    return auth


# For testing
if __name__ == "__main__":
    st.set_page_config(page_title="Auth Test", page_icon="🔐")
    
    st.title("Authentication Test")
    
    auth = init_auth()
    
    with st.sidebar:
        auth.render_auth_section()
    
    st.write("### Status")
    st.write(f"Authenticated: {auth.is_authenticated}")
    
    if auth.current_user:
        st.write(f"User: {auth.current_user.display_name}")
        st.write(f"Email: {auth.current_user.email}")
    
    # Test message counter
    if st.button("Simulate message"):
        auth.increment_message_count()
        st.rerun()
    
    st.write(f"Message count: {st.session_state.get('message_count', 0)}")
    
    # Show signin prompt
    auth.render_signin_prompt()
