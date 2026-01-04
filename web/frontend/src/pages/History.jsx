import { useState, useEffect } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Clock, MessageCircle, BookOpen, Star, Trash2 } from 'lucide-react'
import { motion } from 'framer-motion'
import axios from 'axios'

export default function History() {
  const { isAuthenticated, token, loading: authLoading } = useAuth()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchHistory()
    }
  }, [isAuthenticated, token])

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/api/user/history', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setHistory(response.data)
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSave = async (historyId, isSaved) => {
    try {
      if (isSaved) {
        await axios.delete(`/api/user/save/${historyId}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } else {
        await axios.post(`/api/user/save/${historyId}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }
      fetchHistory()
    } catch (error) {
      console.error('Failed to toggle save:', error)
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-accent-orange border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const formatDate = (dateStr) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Chat History</h1>
          <p className="text-gray-400 text-sm mt-1">
            {history.length} conversation{history.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-dark-800 rounded-2xl p-5 animate-pulse">
              <div className="h-4 bg-dark-600 rounded w-3/4 mb-3" />
              <div className="h-3 bg-dark-600 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-16">
          <Clock className="w-16 h-16 mx-auto mb-4 text-gray-600" />
          <h2 className="text-xl font-semibold text-white mb-2">No history yet</h2>
          <p className="text-gray-400 mb-6">Your chat history will appear here</p>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-medium rounded-xl hover:opacity-90 transition-opacity"
          >
            <MessageCircle className="w-5 h-5" />
            Start a conversation
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item, index) => (
            <motion.div
              key={item.history_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-dark-800 rounded-2xl p-5 border border-dark-600/50 card-hover group"
            >
              <div className="flex items-start justify-between gap-4">
                <Link 
                  to={`/chat?q=${encodeURIComponent(item.query)}`}
                  className="flex-1 min-w-0"
                >
                  <h3 className="font-medium text-white mb-2 line-clamp-2 group-hover:text-accent-orange transition-colors">
                    {item.query}
                  </h3>
                  <p className="text-sm text-gray-400 line-clamp-2 mb-3">
                    {item.response?.substring(0, 150)}...
                  </p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(item.created_at)}
                    </span>
                    {item.papers_used > 0 && (
                      <span className="flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        {item.papers_used} papers
                      </span>
                    )}
                  </div>
                </Link>
                
                <button
                  onClick={() => toggleSave(item.history_id, item.is_saved)}
                  className={`p-2 rounded-lg transition-colors ${
                    item.is_saved || item.is_favorite
                      ? 'text-accent-gold bg-accent-gold/10'
                      : 'text-gray-500 hover:text-accent-gold hover:bg-dark-700'
                  }`}
                >
                  <Star className={`w-5 h-5 ${item.is_saved || item.is_favorite ? 'fill-current' : ''}`} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
