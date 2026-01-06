import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Mail, Lock, User, Eye, EyeOff, Loader2, AlertCircle, Check, Sparkles, CheckCircle } from 'lucide-react'
import { motion } from 'framer-motion'

export default function Register() {
  const navigate = useNavigate()
  const { register, googleLogin, authError, clearError } = useAuth()
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  // Password validation
  const hasMinLength = password.length >= 8
  const hasUppercase = /[A-Z]/.test(password)
  const hasLowercase = /[a-z]/.test(password)
  const hasNumber = /\d/.test(password)
  const isValidPassword = hasMinLength && hasUppercase && hasLowercase && hasNumber

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!isValidPassword) {
      setError('Please meet all password requirements')
      return
    }

    setLoading(true)
    setError(null)
    clearError()

    const result = await register(email, password, displayName || null)
    
    if (result.success) {
      setSuccess(true)
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  const handleGoogleLogin = async () => {
    setLoading(true)
    setError(null)
    const result = await googleLogin()
    if (result.success) {
      navigate('/chat')
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  const PasswordCheck = ({ valid, text }) => (
    <div className={`flex items-center gap-2 text-xs ${valid ? 'text-green-400' : 'text-gray-500'}`}>
      {valid ? <Check className="w-3.5 h-3.5" /> : <div className="w-3.5 h-3.5 rounded-full border border-current" />}
      {text}
    </div>
  )

  if (success) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Check your email!</h1>
          <p className="text-gray-400 mb-6">
            We sent a verification link to<br />
            <span className="text-white font-medium">{email}</span>
          </p>
          <p className="text-gray-500 text-sm mb-6">
            Click the link in the email to verify your account, then you can sign in.
          </p>
          <Link to="/login" className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-medium rounded-xl hover:opacity-90 transition">
            Go to Sign In
          </Link>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-orange to-accent-gold flex items-center justify-center">
            <Sparkles className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Create your account</h1>
          <p className="text-gray-400">Join FitFact for evidence-based fitness advice</p>
        </div>

        {(error || authError) && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-400 text-sm">{error || authError}</p>
          </div>
        )}

        <div className="bg-dark-800 rounded-2xl p-6 border border-dark-600/50">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Name (optional)</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Your name" className="w-full bg-dark-700 text-white rounded-xl pl-10 pr-4 py-3 border border-dark-600/50 focus:border-accent-orange/50 focus:outline-none focus:ring-2 focus:ring-accent-orange/20" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required className="w-full bg-dark-700 text-white rounded-xl pl-10 pr-4 py-3 border border-dark-600/50 focus:border-accent-orange/50 focus:outline-none focus:ring-2 focus:ring-accent-orange/20" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required className="w-full bg-dark-700 text-white rounded-xl pl-10 pr-12 py-3 border border-dark-600/50 focus:border-accent-orange/50 focus:outline-none focus:ring-2 focus:ring-accent-orange/20" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              
              {password && (
                <div className="mt-3 p-3 bg-dark-700/50 rounded-lg space-y-1.5">
                  <PasswordCheck valid={hasMinLength} text="At least 8 characters" />
                  <PasswordCheck valid={hasUppercase} text="One uppercase letter" />
                  <PasswordCheck valid={hasLowercase} text="One lowercase letter" />
                  <PasswordCheck valid={hasNumber} text="One number" />
                </div>
              )}
            </div>

            <button type="submit" disabled={loading || !isValidPassword} className="w-full py-3 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-medium rounded-xl hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create account'}
            </button>
          </form>

          <div className="flex items-center gap-4 my-6">
            <div className="flex-1 h-px bg-dark-600/50"></div>
            <span className="text-gray-500 text-sm">or</span>
            <div className="flex-1 h-px bg-dark-600/50"></div>
          </div>

          <button onClick={handleGoogleLogin} disabled={loading} className="w-full py-3 bg-white text-dark-900 font-medium rounded-xl hover:bg-gray-100 transition flex items-center justify-center gap-3 disabled:opacity-50">
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <p className="text-center mt-6 text-gray-400">
          Already have an account? <Link to="/login" className="text-accent-orange hover:underline font-medium">Sign in</Link>
        </p>
      </motion.div>
    </div>
  )
}
