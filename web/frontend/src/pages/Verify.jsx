import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Mail, Loader2, AlertCircle, CheckCircle, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

export default function Verify() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { verifyEmail, verifyEmailToken, resendVerification } = useAuth()
  
  const email = searchParams.get('email') || ''
  const token = searchParams.get('token')
  
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)
  
  const inputRefs = useRef([])

  // If token in URL, verify automatically
  useEffect(() => {
    if (token) {
      handleTokenVerification()
    }
  }, [token])

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [resendCooldown])

  const handleTokenVerification = async () => {
    setLoading(true)
    setError(null)
    
    const result = await verifyEmailToken(token)
    
    if (result.success) {
      setSuccess(true)
      setTimeout(() => navigate('/chat'), 2000)
    } else {
      setError(result.error)
    }
    setLoading(false)
  }

  const handleCodeChange = (index, value) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return
    
    const newCode = [...code]
    newCode[index] = value
    setCode(newCode)
    
    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }
    
    // Auto-submit when all digits entered
    if (newCode.every(d => d) && newCode.join('').length === 6) {
      handleCodeSubmit(newCode.join(''))
    }
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (pasted.length === 6) {
      setCode(pasted.split(''))
      handleCodeSubmit(pasted)
    }
  }

  const handleCodeSubmit = async (fullCode) => {
    setLoading(true)
    setError(null)
    
    const result = await verifyEmail(email, fullCode)
    
    if (result.success) {
      setSuccess(true)
      setTimeout(() => navigate('/chat'), 2000)
    } else {
      setError(result.error)
      setCode(['', '', '', '', '', ''])
      inputRefs.current[0]?.focus()
    }
    setLoading(false)
  }

  const handleResend = async () => {
    if (resendCooldown > 0) return
    
    const result = await resendVerification(email)
    if (result.success) {
      setResendCooldown(60)
      setError(null)
    } else {
      setError(result.error)
    }
  }

  if (success) {
    return (
      <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Email Verified!</h1>
          <p className="text-gray-400">Redirecting to chat...</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 py-12">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-orange to-accent-gold flex items-center justify-center">
            <Mail className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Check your email</h1>
          <p className="text-gray-400">
            We sent a verification code to<br />
            <span className="text-white font-medium">{email}</span>
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Code input */}
        <div className="bg-dark-800 rounded-2xl p-6 border border-dark-600/50">
          <p className="text-center text-gray-300 text-sm mb-6">
            Enter the 6-digit code
          </p>
          
          <div className="flex justify-center gap-2 mb-6" onPaste={handlePaste}>
            {code.map((digit, index) => (
              <input
                key={index}
                ref={el => inputRefs.current[index] = el}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleCodeChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                disabled={loading}
                className="w-12 h-14 bg-dark-700 text-white text-center text-2xl font-bold rounded-xl border border-dark-600/50 focus:border-accent-orange/50 focus:outline-none focus:ring-2 focus:ring-accent-orange/20 disabled:opacity-50"
              />
            ))}
          </div>

          {loading && (
            <div className="flex items-center justify-center gap-2 text-gray-400 mb-4">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Verifying...</span>
            </div>
          )}

          {/* Resend */}
          <div className="text-center">
            <p className="text-gray-500 text-sm mb-2">Didn't receive the code?</p>
            <button
              onClick={handleResend}
              disabled={resendCooldown > 0}
              className="text-accent-orange hover:underline text-sm font-medium disabled:text-gray-500 disabled:no-underline"
            >
              {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend code'}
            </button>
          </div>
        </div>

        {/* Back to login */}
        <p className="text-center mt-6 text-gray-400">
          <Link to="/login" className="text-accent-orange hover:underline font-medium">
            ← Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
