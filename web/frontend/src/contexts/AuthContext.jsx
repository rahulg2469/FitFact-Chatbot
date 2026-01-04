import { createContext, useContext, useState, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import axios from 'axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('fitfact_token'))
  const [loading, setLoading] = useState(true)

  // Check existing session on mount
  useEffect(() => {
    if (token) {
      verifySession()
    } else {
      setLoading(false)
    }
  }, [])

  const verifySession = async () => {
    try {
      const response = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUser(response.data)
    } catch (error) {
      // Token invalid, clear it
      localStorage.removeItem('fitfact_token')
      setToken(null)
    } finally {
      setLoading(false)
    }
  }

  const login = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        // Get user info from Google
        const userInfo = await axios.get(
          'https://www.googleapis.com/oauth2/v3/userinfo',
          { headers: { Authorization: `Bearer ${tokenResponse.access_token}` } }
        )

        // Exchange for our own token
        const response = await axios.post('/api/auth/google', {
          credential: tokenResponse.access_token,
          user_info: userInfo.data
        })

        const { token: newToken, user: userData } = response.data
        
        localStorage.setItem('fitfact_token', newToken)
        setToken(newToken)
        setUser(userData)
        
        return userData
      } catch (error) {
        console.error('Login failed:', error)
        throw error
      }
    },
    onError: (error) => {
      console.error('Google login error:', error)
    }
  })

  const logout = async () => {
    try {
      if (token) {
        await axios.post('/api/auth/logout', {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('fitfact_token')
      setToken(null)
      setUser(null)
    }
  }

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
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
