-- =====================================================
-- FitFact User Authentication Schema
-- Google OAuth + User Profiles + Preferences
-- =====================================================

-- 1. Users table (core user data from Google OAuth)
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    profile_picture_url TEXT,
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT TRUE,  -- Google accounts are pre-verified
    account_type VARCHAR(20) DEFAULT 'free' CHECK (account_type IN ('free', 'premium', 'admin')),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Analytics
    login_count INT DEFAULT 1,
    total_queries INT DEFAULT 0,
    last_ip_address INET
);

-- 2. User sessions (for JWT token management)
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500),
    
    -- Session metadata
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(50),
    
    -- Expiration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE
);

-- 3. User preferences (personalization settings)
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Fitness profile
    fitness_goals TEXT[],  -- e.g., {'muscle_gain', 'fat_loss', 'endurance'}
    experience_level VARCHAR(20) DEFAULT 'intermediate' 
        CHECK (experience_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    preferred_topics TEXT[],  -- e.g., {'nutrition', 'strength_training', 'recovery'}
    
    -- Physical stats (optional, for personalized advice)
    age_range VARCHAR(20),  -- e.g., '25-34'
    weight_unit VARCHAR(10) DEFAULT 'kg' CHECK (weight_unit IN ('kg', 'lbs')),
    height_unit VARCHAR(10) DEFAULT 'cm' CHECK (height_unit IN ('cm', 'ft')),
    
    -- Response preferences
    response_style VARCHAR(20) DEFAULT 'balanced' 
        CHECK (response_style IN ('concise', 'balanced', 'detailed', 'scientific')),
    show_citations BOOLEAN DEFAULT TRUE,
    show_study_details BOOLEAN DEFAULT FALSE,
    
    -- UI preferences
    theme VARCHAR(10) DEFAULT 'dark' CHECK (theme IN ('light', 'dark', 'auto')),
    language VARCHAR(5) DEFAULT 'en',
    
    -- Notification settings
    email_notifications BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. User query history (track what users ask)
CREATE TABLE IF NOT EXISTS user_query_history (
    history_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    
    -- Link to cached response if available
    cached_response_id INT,
    
    -- Metadata
    papers_used INT DEFAULT 0,
    response_time_ms INT,
    was_cached BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Saved/bookmarked responses
CREATE TABLE IF NOT EXISTS user_saved_responses (
    saved_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    history_id INT REFERENCES user_query_history(history_id) ON DELETE CASCADE,
    
    -- User annotations
    title VARCHAR(255),
    notes TEXT,
    tags TEXT[],
    is_favorite BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, history_id)
);

-- 6. Authentication logs (security audit)
CREATE TABLE IF NOT EXISTS auth_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'login_success', 'login_failed', 'logout', 'session_expired',
        'token_refresh', 'account_created', 'profile_updated', 'password_reset'
    )),
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Rate limits per user
CREATE TABLE IF NOT EXISTS user_rate_limits (
    user_id INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Daily limits
    daily_queries INT DEFAULT 0,
    daily_limit INT DEFAULT 50,  -- Free tier: 50/day
    last_daily_reset DATE DEFAULT CURRENT_DATE,
    
    -- Monthly limits  
    monthly_queries INT DEFAULT 0,
    monthly_limit INT DEFAULT 1000,  -- Free tier: 1000/month
    last_monthly_reset DATE DEFAULT DATE_TRUNC('month', CURRENT_DATE)::DATE,
    
    -- Throttle status
    is_throttled BOOLEAN DEFAULT FALSE,
    throttled_until TIMESTAMP
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_history_user ON user_query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_history_created ON user_query_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_saved_user ON user_saved_responses(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_favorite ON user_saved_responses(user_id, is_favorite) WHERE is_favorite = TRUE;

CREATE INDEX IF NOT EXISTS idx_auth_logs_user ON auth_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_time ON auth_logs(created_at DESC);

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Function to update last login
CREATE OR REPLACE FUNCTION update_user_login(
    p_user_id INT,
    p_ip_address INET DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE users 
    SET last_login = CURRENT_TIMESTAMP,
        login_count = login_count + 1,
        last_ip_address = COALESCE(p_ip_address, last_ip_address),
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to check and update rate limits
CREATE OR REPLACE FUNCTION check_rate_limit(p_user_id INT)
RETURNS TABLE(allowed BOOLEAN, remaining INT, reset_time TIMESTAMP) AS $$
DECLARE
    v_daily_queries INT;
    v_daily_limit INT;
    v_last_reset DATE;
BEGIN
    -- Get current limits
    SELECT daily_queries, daily_limit, last_daily_reset
    INTO v_daily_queries, v_daily_limit, v_last_reset
    FROM user_rate_limits
    WHERE user_id = p_user_id;
    
    -- If no record exists, create one
    IF NOT FOUND THEN
        INSERT INTO user_rate_limits (user_id)
        VALUES (p_user_id);
        
        RETURN QUERY SELECT TRUE, 50, (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP;
        RETURN;
    END IF;
    
    -- Reset daily counter if new day
    IF v_last_reset < CURRENT_DATE THEN
        UPDATE user_rate_limits
        SET daily_queries = 0, last_daily_reset = CURRENT_DATE
        WHERE user_id = p_user_id;
        v_daily_queries := 0;
    END IF;
    
    -- Check if under limit
    IF v_daily_queries < v_daily_limit THEN
        RETURN QUERY SELECT TRUE, (v_daily_limit - v_daily_queries - 1), (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP;
    ELSE
        RETURN QUERY SELECT FALSE, 0, (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to increment query count
CREATE OR REPLACE FUNCTION increment_user_queries(p_user_id INT)
RETURNS VOID AS $$
BEGIN
    -- Update user total
    UPDATE users
    SET total_queries = total_queries + 1
    WHERE user_id = p_user_id;
    
    -- Update rate limits
    UPDATE user_rate_limits
    SET daily_queries = daily_queries + 1,
        monthly_queries = monthly_queries + 1
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to clean expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < CURRENT_TIMESTAMP OR is_valid = FALSE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- DEFAULT DATA
-- =====================================================

-- Create a guest/anonymous user for non-logged-in queries
INSERT INTO users (google_id, email, display_name, account_type)
VALUES ('guest', 'guest@fitfact.local', 'Guest User', 'free')
ON CONFLICT (google_id) DO NOTHING;
