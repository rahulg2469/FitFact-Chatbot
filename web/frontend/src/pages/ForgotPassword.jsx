import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Mail, Loader2, AlertCircle, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

export default function ForgotPassword() {
  const { forgotPassword } = useAuth()
  
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const result = await forgotPassword(email)
    
    if (result.success) {
      setSent(true)
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  if (sent) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-orange/20 flex items-center justify-center">
            <Mail className="w-8 h-8 text-accent-orange" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Check your email</h1>
          <p className="text-gray-400 mb-6">
            If an account exists for <span className="text-white">{email}</span>, you'll receive a password reset link.
          </p>
          <Link to="/login" className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-medium rounded-xl hover:opacity-90 transition">
            Back to Sign In
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
          <h1 className="text-2xl font-bold text-white mb-2">Reset your password</h1>
          <p className="text-gray-400">Enter your email and we'll send you a reset link</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <div className="bg-dark-800 rounded-2xl p-6 border border-dark-600/50">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required className="w-full bg-dark-700 text-white rounded-xl pl-10 pr-4 py-3 border border-dark-600/50 focus:border-accent-orange/50 focus:outline-none focus:ring-2 focus:ring-accent-orange/20" />
              </div>
            </div>

            <button type="submit" disabled={loading || !email} className="w-full py-3 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-medium rounded-xl hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Send reset link'}
            </button>
          </form>
        </div>

        <p className="text-center mt-6 text-gray-400">
          <Link to="/login" className="text-accent-orange hover:underline font-medium">← Back to sign in</Link>
        </p>
      </motion.div>
    </div>
  )
}
