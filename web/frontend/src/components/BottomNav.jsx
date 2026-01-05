import { NavLink } from 'react-router-dom'
import { Home, MessageCircle, Clock, Search } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function BottomNav() {
  const { isAuthenticated } = useAuth()

  const navItems = [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/chat', icon: MessageCircle, label: 'Chat' },
    ...(isAuthenticated ? [{ to: '/history', icon: Clock, label: 'History' }] : []),
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 md:hidden bg-dark-800/95 backdrop-blur-xl border-t border-dark-600/50 z-50">
      <div className="flex justify-around items-center py-2">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-colors ${
                isActive
                  ? 'text-accent-orange'
                  : 'text-gray-500 hover:text-gray-300'
              }`
            }
          >
            <Icon className="w-6 h-6" />
            <span className="text-xs font-medium">{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
