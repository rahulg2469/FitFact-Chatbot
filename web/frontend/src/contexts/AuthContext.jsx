import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

// Check if Firebase is configured
const FIREBASE_CONFIGURED = import.meta.env.VITE_FIREBASE_API_KEY && 
                            import.meta.env.VITE_FIREBASE_API_KEY !== 'your-api-key'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    // Check for saved user in localStorage (fallback when Firebase not configured)
    const savedUser = localStorage.getItem('fitfact_user')
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem('fitfact_user')
      }
    }
    setLoading(false)
  }, [])

  // Placeholder functions - will be replaced with Firebase when configured
  const googleLogin = async () => {
    if (!FIREBASE_CONFIGURED) {
      setAuthError('Firebase not configured. Please set up Firebase first.')
      return { success: false, error: 'Firebase not configured' }
    }
    // Firebase implementation will go here
    return { success: false, error: 'Not implemented' }
  }

  const register = async (email, password, displayName = null) => {
    if (!FIREBASE_CONFIGURED) {
      setAuthError('Firebase not configured. Please set up Firebase first.')
      return { success: false, error: 'Firebase not configured' }
    }
    return { success: false, error: 'Not implemented' }
  }

  const login = async (email, password) => {
    if (!FIREBASE_CONFIGURED) {
      setAuthError('Firebase not configured. Please set up Firebase first.')
      return { success: false, error: 'Firebase not configured' }
    }
    return { success: false, error: 'Not implemented' }
  }

  const resendVerification = async () => {
    return { success: false, error: 'Not implemented' }
  }

  const forgotPassword = async (email) => {
    return { success: true, message: 'If your email is registered, you will receive a reset link' }
  }

  const logout = async () => {
    setUser(null)
    localStorage.removeItem('fitfact_user')
  }

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      authError,
      isAuthenticated: !!user,
      googleLogin,
      register,
      login,
      resendVerification,
      forgotPassword,
      logout,
      clearError: () => setAuthError(null)
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
