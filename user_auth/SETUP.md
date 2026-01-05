# User Authentication Setup Guide

## Overview

FitFact uses Google OAuth 2.0 for user authentication. This provides:
- One-click sign-in (no passwords to manage)
- Secure authentication handled by Google
- User profile with name and picture from Google account

## Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Name it "FitFact" or similar

### 2. Enable Google+ API

1. Go to **APIs & Services** → **Library**
2. Search for "Google+ API" 
3. Click **Enable**

### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Fill in:
   - App name: `FitFact`
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
5. Add test users (your Gmail addresses) if in testing mode
6. Save

### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `FitFact Web Client`
5. Authorized JavaScript origins:
   ```
   http://localhost:8501
   ```
6. Authorized redirect URIs:
   ```
   http://localhost:8501/callback
   http://localhost:8501/
   ```
7. Click **Create**
8. **Save the Client ID and Client Secret**

### 5. Configure Environment Variables

Add to your `.env` file:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8501/callback

# JWT Secret (generate a secure random string)
JWT_SECRET_KEY=your-secret-key-here-make-it-long-and-random

# Database (if not already set)
DB_NAME=fitfact_db
DB_USER=satya
DB_HOST=localhost
DB_PORT=5432
```

To generate a secure JWT secret:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Apply Database Schema

```bash
# Connect to PostgreSQL and apply the schema
psql -d fitfact_db -f user_auth/user_schema.sql
```

Or in psql:
```sql
\i user_auth/user_schema.sql
```

Verify tables were created:
```sql
\dt

-- Should show:
-- users
-- user_sessions
-- user_preferences
-- user_query_history
-- user_saved_responses
-- auth_logs
-- user_rate_limits
```

### 7. Install Dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 PyJWT
```

Or:
```bash
pip install -r requirements.txt
```

### 8. Test the Setup

```bash
cd /path/to/FitFact-Chatbot
python3 -c "
from user_auth import GoogleOAuth, UserManager, SessionManager

# Test OAuth config
import os
if os.getenv('GOOGLE_CLIENT_ID'):
    print('✅ Google OAuth credentials found')
else:
    print('❌ Missing GOOGLE_CLIENT_ID')

# Test database connection
try:
    mgr = UserManager()
    guest = mgr.get_user_by_email('guest@fitfact.local')
    if guest:
        print('✅ Database connection works')
        print(f'   Guest user ID: {guest.user_id}')
    mgr.close()
except Exception as e:
    print(f'❌ Database error: {e}')
"
```

## File Structure

```
user_auth/
├── __init__.py          # Module exports
├── google_oauth.py      # Google OAuth flow handling
├── session_manager.py   # JWT session management
├── user_manager.py      # User CRUD operations
├── user_schema.sql      # PostgreSQL schema
└── SETUP.md            # This file
```

## Usage Example

```python
from user_auth import GoogleOAuth, UserManager, SessionManager

# Initialize
oauth = GoogleOAuth.from_env()
user_mgr = UserManager()
session_mgr = SessionManager()

# Step 1: Get authorization URL (redirect user here)
auth_url, state = oauth.get_authorization_url()

# Step 2: Handle callback (after user authorizes)
google_user = oauth.handle_callback(authorization_code, state)

# Step 3: Create/get user in database
user = user_mgr.get_or_create_user(
    google_id=google_user.google_id,
    email=google_user.email,
    display_name=google_user.display_name,
    profile_picture_url=google_user.profile_picture_url
)

# Step 4: Create session
session = session_mgr.create_session(user.user_id)

# Step 5: Use session token for subsequent requests
# (Store in cookie or session state)
token = session.session_token

# Validate token on each request
user_id = session_mgr.validate_token(token)
if user_id:
    # User is authenticated
    user = user_mgr.get_user_by_id(user_id)
```

## Rate Limits

Default rate limits per account type:
- **Free**: 50 queries/day, 1000 queries/month
- **Premium**: 500 queries/day, 10000 queries/month
- **Admin**: Unlimited

## Next Steps

After setup, integrate with Streamlit UI:
1. Add login/logout buttons
2. Store session token in `st.session_state`
3. Show user profile info
4. Track query history per user
