import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Dumbbell, LogOut, User } from 'lucide-react'

export default function Header() {
  const { user, isAuthenticated, googleLogin, logout, loading } = useAuth()

  return (
    <header className="sticky top-0 z-50 bg-dark-900/80 backdrop-blur-xl border-b border-dark-600/50">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-accent-orange to-accent-gold rounded-xl flex items-center justify-center">
            <Dumbbell className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">FitFact</h1>
            <p className="text-xs text-gray-500 hidden sm:block">Evidence-Based Fitness</p>
          </div>
        </Link>

        {/* User section */}
        <div className="flex items-center gap-3">
          {loading ? (
            <div className="w-8 h-8 rounded-full bg-dark-600 animate-pulse" />
          ) : isAuthenticated ? (
            <div className="flex items-center gap-3">
              {user?.profile_picture_url ? (
                <img 
                  src={user.profile_picture_url} 
                  alt={user.display_name}
                  className="w-9 h-9 rounded-full border-2 border-dark-500"
                />
              ) : (
                <div className="w-9 h-9 rounded-full bg-dark-600 flex items-center justify-center">
                  <User className="w-5 h-5 text-gray-400" />
                </div>
              )}
              <div className="hidden sm:block">
                <p className="text-sm font-medium text-white">{user?.display_name}</p>
                <p className="text-xs text-gray-500">{user?.total_queries || 0} queries</p>
              </div>
              <button
                onClick={logout}
                className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-colors"
                title="Sign out"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-4 py-2 text-gray-300 hover:text-white font-medium transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-gradient-to-r from-accent-orange to-accent-gold text-white rounded-lg font-medium hover:opacity-90 transition"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
