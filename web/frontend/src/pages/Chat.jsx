import { useState, useRef, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Send, Loader2, BookOpen, Clock, Sparkles, X, ChevronDown, ChevronUp, Zap, Target, Droplets, Moon, Activity, Dumbbell, Apple, Heart, Plus, MessageSquare, Trash2, Menu, ChevronLeft } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

// Consistent icon mapping
const TOPIC_ICONS = {
  protein: Target,
  nutrition: Apple,
  diet: Apple,
  recovery: Activity,
  sleep: Moon,
  rest: Moon,
  hydration: Droplets,
  water: Droplets,
  training: Dumbbell,
  exercise: Dumbbell,
  workout: Dumbbell,
  frequency: Zap,
  cardio: Heart,
  health: Heart,
  default: Sparkles
}

function getIconForTitle(title) {
  if (!title) return Sparkles
  const lower = title.toLowerCase()
  for (const [key, Icon] of Object.entries(TOPIC_ICONS)) {
    if (lower.includes(key)) return Icon
  }
  return Sparkles
}

// Parse legacy text response into structured format
function parseTextResponse(text) {
  if (!text) return null
  
  let content = text
  let references = []
  
  // Extract references section
  const refMatch = content.match(/\n\s*\*?\*?References:?\*?\*?\s*\n([\s\S]*?)$/i)
  if (refMatch) {
    content = content.substring(0, refMatch.index).trim()
    const refPattern = /(\d+)\.\s*([A-Za-z][A-Za-z\s\u00C0-\u017F]+?)(?:\s+et\s+al\.?)?\s*\((\d{4})\)\s*-\s*"([^"]+)"\s*-\s*([^-]+?)\s*-\s*PMID:\s*(\d+)/g
    let match
    while ((match = refPattern.exec(refMatch[1])) !== null) {
      references.push({
        num: parseInt(match[1]),
        author: match[2].trim(),
        year: match[3],
        title: match[4].trim(),
        journal: match[5].trim(),
        pmid: match[6]
      })
    }
  }
  
  // Parse numbered sections
  const numberedPattern = /(\d+)\.\s+([^:\n]+):\s*([^]*?)(?=\n\d+\.\s+[A-Z]|$)/g
  const matches = [...content.matchAll(numberedPattern)]
  
  let headline = ''
  let points = []
  let takeaway = null
  
  if (matches.length >= 2) {
    headline = content.substring(0, matches[0].index).trim()
    points = matches.map(m => ({
      title: m[2].trim(),
      content: m[3].trim().replace(/\n+/g, ' ')
    }))
    
    const lastMatch = matches[matches.length - 1]
    const afterLast = content.substring(lastMatch.index + lastMatch[0].length).trim()
    if (afterLast && !afterLast.match(/^\d+\./)) {
      takeaway = afterLast
    }
  } else {
    // No structured points - use first sentences as headline
    const sentences = content.split(/(?<=[.!?])\s+/)
    headline = sentences.slice(0, 2).join(' ')
    
    if (sentences.length > 2) {
      points = [{
        title: 'Key Information',
        content: sentences.slice(2).join(' ')
      }]
    }
  }
  
  return { headline, points, takeaway, references }
}

// Format citations in text
function formatCitations(text, references) {
  if (!text || !references?.length) return text
  
  return text
    .replace(/\(([A-Z][a-z\u00C0-\u017F]+)(?:\s+et\s+al\.?)?,?\s*(\d{4})\)/g, (match, author, year) => {
      const ref = references.find(r => 
        r.author?.toLowerCase().startsWith(author.toLowerCase()) && r.year === year
      )
      return ref?.pmid 
        ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/" target="_blank" class="cite">[${ref.num}]</a>`
        : match
    })
    .replace(/\(([^)]*;\s*[^)]*)\)/g, (match, inner) => {
      if (!/\d{4}/.test(inner)) return match
      const parts = inner.split(/;\s*/).map(cit => {
        const m = cit.match(/([A-Z][a-z\u00C0-\u017F]+)(?:\s+et\s+al\.?)?,?\s*(\d{4})/)
        if (m) {
          const ref = references.find(r => r.author?.toLowerCase().startsWith(m[1].toLowerCase()) && r.year === m[2])
          if (ref?.pmid) return `<a href="https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/" target="_blank" class="cite">[${ref.num}]</a>`
        }
        return null
      })
      return parts.every(p => p) ? parts.join('') : match
    })
}

export default function Chat() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated, login, token } = useAuth()
  
  // Conversation state
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem('fitfact_conversations')
    return saved ? JSON.parse(saved) : []
  })
  const [activeConvoId, setActiveConvoId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedRefs, setExpandedRefs] = useState({})
  const messagesEndRef = useRef(null)
  const processedInitialQuery = useRef(false)

  // Load active conversation
  useEffect(() => {
    if (activeConvoId) {
      const convo = conversations.find(c => c.id === activeConvoId)
      if (convo) setMessages(convo.messages)
    } else {
      setMessages([])
    }
  }, [activeConvoId])

  // Save conversations
  useEffect(() => {
    localStorage.setItem('fitfact_conversations', JSON.stringify(conversations))
  }, [conversations])

  // Update conversation messages
  useEffect(() => {
    if (activeConvoId && messages.length > 0) {
      setConversations(prev => prev.map(c => 
        c.id === activeConvoId 
          ? { ...c, messages, updatedAt: Date.now(), title: getConvoTitle(messages) }
          : c
      ))
    }
  }, [messages, activeConvoId])

  useEffect(() => {
    const q = searchParams.get('q')
    if (q && !processedInitialQuery.current) {
      processedInitialQuery.current = true
      setSearchParams({})
      startNewConversation(q)
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const getConvoTitle = (msgs) => {
    const firstUser = msgs.find(m => m.role === 'user')
    if (firstUser) {
      const text = firstUser.content
      return text.length > 30 ? text.substring(0, 30) + '...' : text
    }
    return 'New conversation'
  }

  const startNewConversation = (initialMessage = null) => {
    const newId = Date.now().toString()
    setConversations(prev => [{ id: newId, title: 'New conversation', messages: [], createdAt: Date.now(), updatedAt: Date.now() }, ...prev])
    setActiveConvoId(newId)
    setMessages([])
    if (initialMessage) setTimeout(() => handleSend(initialMessage), 100)
  }

  const deleteConversation = (id, e) => {
    e.stopPropagation()
    setConversations(prev => prev.filter(c => c.id !== id))
    if (activeConvoId === id) {
      setActiveConvoId(null)
      setMessages([])
    }
  }

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return
    
    if (!activeConvoId) {
      const newId = Date.now().toString()
      setConversations(prev => [{ id: newId, title: text.trim().substring(0, 30), messages: [], createdAt: Date.now(), updatedAt: Date.now() }, ...prev])
      setActiveConvoId(newId)
    }
    
    setMessages(prev => [...prev, { role: 'user', content: text.trim() }])
    setInput('')
    setLoading(true)

    try {
      const res = await axios.post('/api/chat', {
        message: text.trim(),
        conversation_history: messages.map(m => ({ role: m.role, content: m.content }))
      }, { headers: token ? { Authorization: `Bearer ${token}` } : {} })

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.response,
        structured: res.data.structured,
        metadata: { 
          papers_used: res.data.papers_used, 
          response_time: res.data.response_time, 
          cached: res.data.cached 
        }
      }])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.', 
        error: true 
      }])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp) => {
    const diff = Date.now() - timestamp
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return new Date(timestamp).toLocaleDateString()
  }

  return (
    <div className="flex h-[calc(100vh-64px)]">
      <style>{`
        .cite { 
          color: #e07c4a; 
          font-size: 0.7em; 
          font-weight: 700; 
          vertical-align: super; 
          text-decoration: none;
          padding: 0 1px;
        }
        .cite:hover { text-decoration: underline; }
      `}</style>

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="bg-dark-900 border-r border-dark-700/50 flex flex-col overflow-hidden"
          >
            <div className="p-3">
              <button onClick={() => startNewConversation()} className="w-full flex items-center gap-2 px-4 py-2.5 bg-dark-800 hover:bg-dark-700 border border-dark-600/50 rounded-xl text-white text-sm font-medium transition">
                <Plus className="w-4 h-4" /> New chat
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 pb-3">
              <p className="text-[11px] text-gray-500 uppercase tracking-wider px-2 mb-2">Recent</p>
              {conversations.length === 0 ? (
                <p className="text-gray-600 text-xs px-2">No conversations yet</p>
              ) : (
                <div className="space-y-0.5">
                  {conversations.map(convo => (
                    <button
                      key={convo.id}
                      onClick={() => setActiveConvoId(convo.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition group flex items-start gap-2 ${
                        activeConvoId === convo.id ? 'bg-dark-700 text-white' : 'text-gray-400 hover:bg-dark-800 hover:text-white'
                      }`}
                    >
                      <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-50" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{convo.title}</p>
                        <p className="text-[10px] text-gray-600">{formatDate(convo.updatedAt)}</p>
                      </div>
                      <button onClick={(e) => deleteConversation(convo.id, e)} className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {!isAuthenticated && (
              <div className="p-3 border-t border-dark-700/50">
                <button onClick={() => login()} className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white text-dark-900 rounded-lg text-xs font-medium hover:bg-gray-100">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                  Sign in to sync
                </button>
              </div>
            )}
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 px-4 py-2 border-b border-dark-700/50">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg">
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
          <span className="text-sm text-gray-500 truncate">
            {activeConvoId ? conversations.find(c => c.id === activeConvoId)?.title : 'FitFact'}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-16">
                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-orange to-accent-gold flex items-center justify-center">
                  <Sparkles className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-white mb-1">Ask FitFact</h2>
                <p className="text-gray-500 text-sm mb-6">Evidence-based fitness answers from research</p>
                <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
                  {['How much protein do I need?', 'Best recovery methods?', 'How often should I train?'].map((q, i) => (
                    <button key={i} onClick={() => handleSend(q)} className="px-3 py-1.5 bg-dark-800 hover:bg-dark-700 border border-dark-600/50 rounded-full text-xs text-gray-400 hover:text-white transition">
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, idx) => (
              <MessageBubble 
                key={idx} 
                message={msg} 
                index={idx} 
                expandedRefs={expandedRefs} 
                toggleRefs={(i) => setExpandedRefs(p => ({ ...p, [i]: !p[i] }))} 
              />
            ))}

            {loading && (
              <div className="flex gap-1.5 items-center bg-dark-800 rounded-2xl px-4 py-3 w-fit border border-dark-600/50">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-2 h-2 bg-accent-orange rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
                <span className="text-gray-500 text-sm ml-2">Searching research...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-dark-700/50 p-4">
          <div className="max-w-3xl mx-auto flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about fitness, nutrition..."
              className="flex-1 bg-dark-800 text-white placeholder-gray-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-orange/50 border border-dark-600/50"
              disabled={loading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="px-4 bg-gradient-to-r from-accent-orange to-accent-gold rounded-xl text-white disabled:opacity-40 hover:opacity-90"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message, index, expandedRefs, toggleRefs }) {
  // Get structured data - either from API or parsed from text
  const data = useMemo(() => {
    if (message.role !== 'assistant') return null
    if (message.structured && message.structured.headline) {
      return message.structured
    }
    return parseTextResponse(message.content)
  }, [message])

  if (message.role === 'user') {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="max-w-[80%] bg-gradient-to-r from-accent-orange to-accent-gold rounded-2xl rounded-br-sm px-4 py-2.5">
          <p className="text-white text-sm font-medium">{message.content}</p>
        </div>
      </motion.div>
    )
  }

  if (!data) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="bg-dark-800 rounded-2xl p-5 border border-dark-600/50">
          <p className="text-gray-300 text-sm">{message.content}</p>
        </div>
      </motion.div>
    )
  }

  const { headline, points, takeaway, references } = data

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="bg-dark-800 rounded-2xl border border-dark-600/50 overflow-hidden">
        
        {/* Headline - Large prominent text */}
        {headline && (
          <div className="p-5 pb-4">
            <h2 
              className="text-xl font-semibold text-white leading-snug"
              dangerouslySetInnerHTML={{ __html: formatCitations(headline, references) }}
            />
          </div>
        )}
        
        {/* Points - Card style */}
        {points && points.length > 0 && (
          <div className="px-5 pb-5 space-y-3">
            {points.map((point, idx) => {
              const Icon = getIconForTitle(point.title)
              return (
                <div key={idx} className="bg-dark-700/40 rounded-xl p-4 border border-dark-600/20">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent-orange/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Icon className="w-4 h-4 text-accent-orange" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-white mb-1">{point.title}</h3>
                      <p 
                        className="text-sm text-gray-400 leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: formatCitations(point.content, references) }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        
        {/* Takeaway */}
        {takeaway && (
          <div className="mx-5 mb-5 p-3 bg-accent-orange/5 rounded-xl border border-accent-orange/20">
            <p className="text-sm text-gray-300">
              <span className="text-accent-orange font-semibold">💡 </span>
              <span dangerouslySetInnerHTML={{ __html: formatCitations(takeaway.replace(/\s*-\s*/g, ' • '), references) }} />
            </p>
          </div>
        )}
        
        {/* References - Collapsible */}
        {references && references.length > 0 && (
          <div className="border-t border-dark-600/50">
            <button 
              onClick={() => toggleRefs(index)} 
              className="w-full px-5 py-2.5 flex items-center justify-between text-xs text-gray-500 hover:text-gray-400 transition"
            >
              <span className="flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" />
                {references.length} sources
              </span>
              {expandedRefs[index] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            
            <AnimatePresence>
              {expandedRefs[index] && (
                <motion.div 
                  initial={{ height: 0 }} 
                  animate={{ height: 'auto' }} 
                  exit={{ height: 0 }} 
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-4 space-y-1.5">
                    {references.map((ref, i) => (
                      <a
                        key={i}
                        href={`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-2.5 bg-dark-700/30 rounded-lg hover:bg-dark-700/50 transition group"
                      >
                        <div className="flex gap-2">
                          <span className="text-accent-orange text-xs font-bold">[{ref.num}]</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-gray-300 group-hover:text-white line-clamp-2">{ref.title}</p>
                            <p className="text-[10px] text-gray-500 mt-0.5">{ref.author} et al. • {ref.year} • {ref.journal}</p>
                          </div>
                        </div>
                      </a>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
        
        {/* Metadata footer */}
        {message.metadata && (
          <div className="px-5 py-2 bg-dark-900/30 flex items-center gap-3 text-[10px] text-gray-600 border-t border-dark-600/30">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {message.metadata.response_time?.toFixed(1)}s
            </span>
            {message.metadata.cached && <span className="text-green-600">cached</span>}
          </div>
        )}
      </div>
    </motion.div>
  )
}
