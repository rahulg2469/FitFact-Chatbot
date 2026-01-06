-- Email/Password Authentication Schema Updates
-- Run this to add email auth support to existing users table

-- Add email auth columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128),
ADD COLUMN IF NOT EXISTS password_salt VARCHAR(64),
ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) DEFAULT 'google',
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS verification_token VARCHAR(64),
ADD COLUMN IF NOT EXISTS verification_code VARCHAR(6),
ADD COLUMN IF NOT EXISTS verification_expires TIMESTAMP,
ADD COLUMN IF NOT EXISTS reset_token VARCHAR(64),
ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;

-- Make google_id nullable for email auth users
ALTER TABLE users ALTER COLUMN google_id DROP NOT NULL;

-- Add constraint to ensure either google_id or password exists
-- (Commented out for flexibility - uncomment if strict validation needed)
-- ALTER TABLE users ADD CONSTRAINT auth_method_check 
--     CHECK (google_id IS NOT NULL OR password_hash IS NOT NULL);

-- Index for verification lookups
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token) WHERE verification_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token) WHERE reset_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider);

-- Update existing users to have google auth provider
UPDATE users SET auth_provider = 'google', email_verified = TRUE WHERE google_id IS NOT NULL AND auth_provider IS NULL;

COMMENT ON COLUMN users.auth_provider IS 'Authentication method: google or email';
COMMENT ON COLUMN users.email_verified IS 'Whether email has been verified (always true for Google OAuth)';
COMMENT ON COLUMN users.verification_token IS 'Token for email verification link';
COMMENT ON COLUMN users.verification_code IS '6-digit code for email verification';
