"""
Email/Password Authentication for FitFact

Handles:
- User registration with email verification
- Password hashing and validation
- Email verification tokens
- Password reset functionality
"""

import os
import secrets
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class EmailAuthManager:
    """Handle email/password authentication"""
    
    def __init__(self, connection=None):
        self._conn = connection
        self._owns_connection = connection is None
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@fitfact.app')
        self.app_url = os.getenv('APP_URL', 'http://localhost:3000')
    
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
        if self._owns_connection and self._conn and not self._conn.closed:
            self._conn.close()
    
    # ==================== PASSWORD HASHING ====================
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """
        Hash password with salt using SHA-256.
        Returns (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Combine password with salt and hash
        salted = f"{password}{salt}"
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        
        return hashed, salt
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    # ==================== TOKEN GENERATION ====================
    
    def _generate_verification_token(self) -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)
    
    def _generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # ==================== USER REGISTRATION ====================
    
    def register_user(self, email: str, password: str, display_name: str = None) -> Dict:
        """
        Register a new user with email/password.
        
        Returns:
            {'success': bool, 'message': str, 'user_id': int, 'verification_token': str}
        """
        conn = self._get_connection()
        
        # Validate email format
        if not self._is_valid_email(email):
            return {'success': False, 'message': 'Invalid email format'}
        
        # Validate password strength
        password_check = self._validate_password(password)
        if not password_check['valid']:
            return {'success': False, 'message': password_check['message']}
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if email already exists
                cur.execute("SELECT user_id, email_verified FROM users WHERE email = %s", (email,))
                existing = cur.fetchone()
                
                if existing:
                    if existing['email_verified']:
                        return {'success': False, 'message': 'Email already registered'}
                    else:
                        # User exists but not verified - allow re-registration
                        user_id = existing['user_id']
                        # Update password and generate new token
                        password_hash, salt = self._hash_password(password)
                        verification_token = self._generate_verification_token()
                        verification_code = self._generate_verification_code()
                        
                        cur.execute("""
                            UPDATE users 
                            SET password_hash = %s,
                                password_salt = %s,
                                display_name = COALESCE(%s, display_name),
                                verification_token = %s,
                                verification_code = %s,
                                verification_expires = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = %s
                        """, (
                            password_hash, salt, display_name or email.split('@')[0],
                            verification_token, verification_code,
                            datetime.now() + timedelta(hours=24),
                            user_id
                        ))
                        conn.commit()
                        
                        # Send verification email
                        self._send_verification_email(email, verification_token, verification_code)
                        
                        return {
                            'success': True,
                            'message': 'Verification email sent. Please check your inbox.',
                            'user_id': user_id,
                            'verification_token': verification_token
                        }
                
                # Create new user
                password_hash, salt = self._hash_password(password)
                verification_token = self._generate_verification_token()
                verification_code = self._generate_verification_code()
                
                cur.execute("""
                    INSERT INTO users (
                        email, password_hash, password_salt, display_name,
                        auth_provider, verification_token, verification_code,
                        verification_expires, email_verified
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                    RETURNING user_id
                """, (
                    email, password_hash, salt, display_name or email.split('@')[0],
                    'email', verification_token, verification_code,
                    datetime.now() + timedelta(hours=24)
                ))
                
                user_id = cur.fetchone()['user_id']
                
                # Create default preferences
                cur.execute("INSERT INTO user_preferences (user_id) VALUES (%s)", (user_id,))
                
                # Create rate limit entry
                cur.execute("INSERT INTO user_rate_limits (user_id) VALUES (%s)", (user_id,))
                
                conn.commit()
                
                # Send verification email
                self._send_verification_email(email, verification_token, verification_code)
                
                return {
                    'success': True,
                    'message': 'Registration successful! Please check your email to verify your account.',
                    'user_id': user_id,
                    'verification_token': verification_token
                }
                
        except Exception as e:
            conn.rollback()
            print(f"Registration error: {e}")
            return {'success': False, 'message': 'Registration failed. Please try again.'}
    
    # ==================== EMAIL VERIFICATION ====================
    
    def verify_email_by_token(self, token: str) -> Dict:
        """Verify email using the link token"""
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, email, verification_expires 
                    FROM users 
                    WHERE verification_token = %s AND email_verified = FALSE
                """, (token,))
                
                user = cur.fetchone()
                
                if not user:
                    return {'success': False, 'message': 'Invalid or expired verification link'}
                
                if user['verification_expires'] < datetime.now():
                    return {'success': False, 'message': 'Verification link has expired. Please register again.'}
                
                # Verify the user
                cur.execute("""
                    UPDATE users 
                    SET email_verified = TRUE,
                        verification_token = NULL,
                        verification_code = NULL,
                        verification_expires = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user['user_id'],))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'Email verified successfully! You can now sign in.',
                    'user_id': user['user_id']
                }
                
        except Exception as e:
            conn.rollback()
            print(f"Verification error: {e}")
            return {'success': False, 'message': 'Verification failed'}
    
    def verify_email_by_code(self, email: str, code: str) -> Dict:
        """Verify email using the 6-digit code"""
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, verification_code, verification_expires 
                    FROM users 
                    WHERE email = %s AND email_verified = FALSE
                """, (email,))
                
                user = cur.fetchone()
                
                if not user:
                    return {'success': False, 'message': 'User not found or already verified'}
                
                if user['verification_expires'] < datetime.now():
                    return {'success': False, 'message': 'Verification code has expired. Please register again.'}
                
                if not secrets.compare_digest(user['verification_code'], code):
                    return {'success': False, 'message': 'Invalid verification code'}
                
                # Verify the user
                cur.execute("""
                    UPDATE users 
                    SET email_verified = TRUE,
                        verification_token = NULL,
                        verification_code = NULL,
                        verification_expires = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user['user_id'],))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'Email verified successfully!',
                    'user_id': user['user_id']
                }
                
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': 'Verification failed'}
    
    def resend_verification(self, email: str) -> Dict:
        """Resend verification email"""
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, email_verified FROM users WHERE email = %s
                """, (email,))
                
                user = cur.fetchone()
                
                if not user:
                    return {'success': False, 'message': 'Email not found'}
                
                if user['email_verified']:
                    return {'success': False, 'message': 'Email already verified'}
                
                # Generate new tokens
                verification_token = self._generate_verification_token()
                verification_code = self._generate_verification_code()
                
                cur.execute("""
                    UPDATE users 
                    SET verification_token = %s,
                        verification_code = %s,
                        verification_expires = %s
                    WHERE user_id = %s
                """, (
                    verification_token, verification_code,
                    datetime.now() + timedelta(hours=24),
                    user['user_id']
                ))
                
                conn.commit()
                
                # Send email
                self._send_verification_email(email, verification_token, verification_code)
                
                return {'success': True, 'message': 'Verification email sent'}
                
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': 'Failed to resend verification'}
    
    # ==================== LOGIN ====================
    
    def login(self, email: str, password: str) -> Dict:
        """
        Authenticate user with email/password.
        
        Returns:
            {'success': bool, 'message': str, 'user': dict}
        """
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, email, display_name, password_hash, password_salt,
                           email_verified, is_active, profile_picture_url, account_type,
                           total_queries
                    FROM users 
                    WHERE email = %s AND auth_provider = 'email'
                """, (email,))
                
                user = cur.fetchone()
                
                if not user:
                    return {'success': False, 'message': 'Invalid email or password'}
                
                if not user['email_verified']:
                    return {
                        'success': False, 
                        'message': 'Please verify your email before signing in',
                        'needs_verification': True
                    }
                
                if not user['is_active']:
                    return {'success': False, 'message': 'Account is deactivated'}
                
                # Verify password
                if not self._verify_password(password, user['password_hash'], user['password_salt']):
                    return {'success': False, 'message': 'Invalid email or password'}
                
                # Update last login
                cur.execute("""
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP,
                        login_count = login_count + 1
                    WHERE user_id = %s
                """, (user['user_id'],))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'user_id': user['user_id'],
                        'email': user['email'],
                        'display_name': user['display_name'],
                        'profile_picture_url': user['profile_picture_url'],
                        'account_type': user['account_type'],
                        'total_queries': user['total_queries']
                    }
                }
                
        except Exception as e:
            print(f"Login error: {e}")
            return {'success': False, 'message': 'Login failed'}
    
    # ==================== PASSWORD RESET ====================
    
    def request_password_reset(self, email: str) -> Dict:
        """Send password reset email"""
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id FROM users 
                    WHERE email = %s AND auth_provider = 'email'
                """, (email,))
                
                user = cur.fetchone()
                
                if not user:
                    # Don't reveal if email exists
                    return {'success': True, 'message': 'If your email is registered, you will receive a reset link'}
                
                # Generate reset token
                reset_token = self._generate_verification_token()
                
                cur.execute("""
                    UPDATE users 
                    SET reset_token = %s,
                        reset_token_expires = %s
                    WHERE user_id = %s
                """, (
                    reset_token,
                    datetime.now() + timedelta(hours=1),
                    user['user_id']
                ))
                
                conn.commit()
                
                # Send reset email
                self._send_password_reset_email(email, reset_token)
                
                return {'success': True, 'message': 'If your email is registered, you will receive a reset link'}
                
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': 'Failed to process request'}
    
    def reset_password(self, token: str, new_password: str) -> Dict:
        """Reset password using token"""
        conn = self._get_connection()
        
        # Validate new password
        password_check = self._validate_password(new_password)
        if not password_check['valid']:
            return {'success': False, 'message': password_check['message']}
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, reset_token_expires 
                    FROM users 
                    WHERE reset_token = %s
                """, (token,))
                
                user = cur.fetchone()
                
                if not user:
                    return {'success': False, 'message': 'Invalid or expired reset link'}
                
                if user['reset_token_expires'] < datetime.now():
                    return {'success': False, 'message': 'Reset link has expired'}
                
                # Update password
                password_hash, salt = self._hash_password(new_password)
                
                cur.execute("""
                    UPDATE users 
                    SET password_hash = %s,
                        password_salt = %s,
                        reset_token = NULL,
                        reset_token_expires = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (password_hash, salt, user['user_id']))
                
                conn.commit()
                
                return {'success': True, 'message': 'Password reset successfully'}
                
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': 'Password reset failed'}
    
    # ==================== VALIDATION ====================
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> Dict:
        """
        Validate password strength.
        Returns {'valid': bool, 'message': str}
        """
        if len(password) < 8:
            return {'valid': False, 'message': 'Password must be at least 8 characters'}
        
        if not any(c.isupper() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one uppercase letter'}
        
        if not any(c.islower() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one lowercase letter'}
        
        if not any(c.isdigit() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one number'}
        
        return {'valid': True, 'message': 'Password is strong'}
    
    # ==================== EMAIL SENDING ====================
    
    def _send_verification_email(self, email: str, token: str, code: str):
        """Send verification email with link and code"""
        verification_link = f"{self.app_url}/verify?token={token}"
        
        subject = "Verify your FitFact account"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #e07c4a, #d4a44a); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">FitFact</h1>
                <p style="color: white; opacity: 0.9;">Evidence-Based Fitness</p>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333;">Verify Your Email</h2>
                <p style="color: #666; line-height: 1.6;">
                    Thanks for signing up! Please verify your email to complete your registration.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" 
                       style="background: #e07c4a; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Verify Email
                    </a>
                </div>
                
                <p style="color: #666; text-align: center;">Or enter this code:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; 
                                 color: #e07c4a; background: #fff; padding: 15px 25px; 
                                 border-radius: 8px; border: 2px dashed #e07c4a;">
                        {code}
                    </span>
                </div>
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This link and code expire in 24 hours.
                </p>
            </div>
            
            <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>If you didn't create an account, you can safely ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Verify your FitFact account
        
        Thanks for signing up! Please verify your email.
        
        Click this link: {verification_link}
        
        Or enter this code: {code}
        
        This link and code expire in 24 hours.
        """
        
        self._send_email(email, subject, html_body, text_body)
    
    def _send_password_reset_email(self, email: str, token: str):
        """Send password reset email"""
        reset_link = f"{self.app_url}/reset-password?token={token}"
        
        subject = "Reset your FitFact password"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #e07c4a, #d4a44a); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">FitFact</h1>
            </div>
            
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333;">Reset Your Password</h2>
                <p style="color: #666; line-height: 1.6;">
                    We received a request to reset your password. Click the button below to create a new password.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background: #e07c4a; color: white; padding: 12px 30px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This link expires in 1 hour.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Reset your FitFact password
        
        Click this link to reset your password: {reset_link}
        
        This link expires in 1 hour.
        """
        
        self._send_email(email, subject, html_body, text_body)
    
    def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str):
        """Send email using SMTP"""
        if not self.smtp_user or not self.smtp_password:
            print(f"[EMAIL] Would send to {to_email}: {subject}")
            print(f"[EMAIL] SMTP not configured - email not sent")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            print(f"[EMAIL] Sent to {to_email}: {subject}")
            
        except Exception as e:
            print(f"[EMAIL] Failed to send to {to_email}: {e}")


# Test
if __name__ == "__main__":
    print("Email Auth Manager Test")
    print("=" * 50)
    
    auth = EmailAuthManager()
    
    # Test password validation
    print("\nPassword validation tests:")
    test_passwords = ["short", "nouppercase1", "NOLOWERCASE1", "NoNumbers"]
    for pwd in test_passwords:
        result = auth._validate_password(pwd)
        print(f"  '{pwd}': {result['message']}")
    
    print(f"  'ValidPass123': {auth._validate_password('ValidPass123')['message']}")
    
    auth.close()
