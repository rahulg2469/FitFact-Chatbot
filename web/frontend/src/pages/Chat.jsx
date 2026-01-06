import { useState, useRef, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Send, Loader2, BookOpen, Clock, Sparkles, ChevronDown, ChevronUp, Zap, Target, Droplets, Moon, Activity, Dumbbell, Apple, Heart, Plus, MessageSquare, Trash2, Menu, ChevronLeft } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// API URL - use localhost for dev
const API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''

// Consistent icon mapping
const TOPIC_ICONS = {
  protein: Target, nutrition: Apple, diet: Apple, recovery: Activity,
  sleep: Moon, rest: Moon, hydration: Droplets, water: Droplets,
  training: Dumbbell, exercise: Dumbbell, workout: Dumbbell,
  frequency: Zap, cardio: Heart, health: Heart, default: Sparkles
}

function getIconForTitle(title) {
  if (!title) return Sparkles
  const lower = title.toLowerCase()
  for (const [key, Icon] of Object.entries(TOPIC_ICONS)) {
    if (lower.includes(key)) return Icon
  }
  return Sparkles
}

function parseTextResponse(text) {
  if (!text) return null
  
  let content = text
  let references = []
  
  const refMatch = content.match(/\n\s*\*?\*?References:?\*?\*?\s*\n([\s\S]*?)$/i)
  if (refMatch) {
    content = content.substring(0, refMatch.index).trim()
    const refPattern = /(\d+)\.\s*([A-Za-z][A-Za-z\s\u00C0-\u017F]+?)(?:\s+et\s+al\.?)?\s*\((\d{4})\)\s*-\s*"([^"]+)"\s*-\s*([^-]+?)\s*-\s*PMID:\s*(\d+)/g
    let match
    while ((match = refPattern.exec(refMatch[1])) !== null) {
      references.push({ num: parseInt(match[1]), author: match[2].trim(), year: match[3], title: match[4].trim(), journal: match[5].trim(), pmid: match[6] })
    }
  }
  
  const numberedPattern = /(\d+)\.\s+([^:\n]+):\s*([^]*?)(?=\n\d+\.\s+[A-Z]|$)/g
  const matches = [...content.matchAll(numberedPattern)]
  
  let headline = '', points = [], takeaway = null
  
  if (matches.length >= 2) {
    headline = content.substring(0, matches[0].index).trim()
    points = matches.map(m => ({ title: m[2].trim(), content: m[3].trim().replace(/\n+/g, ' ') }))
    const lastMatch = matches[matches.length - 1]
    const afterLast = content.substring(lastMatch.index + lastMatch[0].length).trim()
    if (afterLast && !afterLast.match(/^\d+\./)) takeaway = afterLast
  } else {
    const sentences = content.split(/(?<=[.!?])\s+/)
    headline = sentences.slice(0, 2).join(' ')
    if (sentences.length > 2) points = [{ title: 'Key Information', content: sentences.slice(2).join(' ') }]
  }
  
  return { headline, points, takeaway, references }
}

function formatCitations(text, references) {
  if (!text || !references?.length) return text
  return text
    .replace(/\(([A-Z][a-z\u00C0-\u017F]+)(?:\s+et\s+al\.?)?,?\s*(\d{4})\)/g, (match, author, year) => {
      const ref = references.find(r => r.author?.toLowerCase().startsWith(author.toLowerCase()) && r.year === year)
      return ref?.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/" target="_blank" class="cite">[${ref.num}]</a>` : match
    })
}

// Get storage key based on user
function getStorageKey(userId) {
  return userId ? `fitfact_conversations_${userId}` : 'fitfact_conversations_guest'
}

export default function Chat() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { isAuthenticated, user } = useAuth()
  
  const storageKey = getStorageKey(user?.uid)
  
  const [conversations, setConversations] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [activeConvoId, setActiveConvoId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [expandedRefs, setExpandedRefs] = useState({})
  const messagesEndRef = useRef(null)
  const processedInitialQuery = useRef(false)
  const prevUserRef = useRef(user?.uid)

  // Reload conversations when user changes
  useEffect(() => {
    const currentUserId = user?.uid
    if (currentUserId !== prevUserRef.current) {
      const key = getStorageKey(currentUserId)
      try {
        const saved = localStorage.getItem(key)
        setConversations(saved ? JSON.parse(saved) : [])
      } catch {
        setConversations([])
      }
      setActiveConvoId(null)
      setMessages([])
      prevUserRef.current = currentUserId
    }
  }, [user?.uid])

  // Load active conversation messages
  useEffect(() => {
    if (activeConvoId) {
      const convo = conversations.find(c => c.id === activeConvoId)
      if (convo && convo.messages) {
        setMessages(convo.messages)
      }
    }
  }, [activeConvoId])

  // Save conversations to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(conversations))
    } catch (e) {
      console.error('Failed to save conversations:', e)
    }
  }, [conversations, storageKey])

  // Handle initial query from URL
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
    const newConvo = { 
      id: newId, 
      title: initialMessage ? initialMessage.substring(0, 30) : 'New conversation', 
      messages: [], 
      createdAt: Date.now(), 
      updatedAt: Date.now() 
    }
    setConversations(prev => [newConvo, ...prev])
    setActiveConvoId(newId)
    setMessages([])
    if (initialMessage) {
      setTimeout(() => handleSend(initialMessage), 100)
    }
  }

  const handleDeleteConversation = (id, e) => {
    e.stopPropagation()
    setConversations(prev => prev.filter(c => c.id !== id))
    if (activeConvoId === id) {
      setActiveConvoId(null)
      setMessages([])
    }
  }

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return
    
    let convoId = activeConvoId
    
    // Create conversation if needed
    if (!convoId) {
      const newId = Date.now().toString()
      const newConvo = { 
        id: newId, 
        title: text.trim().substring(0, 30), 
        messages: [], 
        createdAt: Date.now(), 
        updatedAt: Date.now() 
      }
      setConversations(prev => [newConvo, ...prev])
      convoId = newId
      setActiveConvoId(newId)
    }
    
    const userMessage = { role: 'user', content: text.trim() }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          conversation_history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      })
      
      const data = await res.json()
      
      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        structured: data.structured,
        metadata: { papers_used: data.papers_used, response_time: data.response_time, cached: data.cached }
      }
      
      const finalMessages = [...newMessages, assistantMessage]
      setMessages(finalMessages)
      
      // Update conversation in state
      setConversations(prev => prev.map(c => 
        c.id === convoId 
          ? { ...c, messages: finalMessages, updatedAt: Date.now(), title: getConvoTitle(finalMessages) }
          : c
      ))
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.', error: true }])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (timestamp) => {
    if (!timestamp || isNaN(timestamp)) return ''
    try {
      const ts = typeof timestamp === 'number' ? timestamp : Date.now()
      const diff = Date.now() - ts
      if (diff < 60000) return 'Just now'
      if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
      return new Date(ts).toLocaleDateString()
    } catch {
      return ''
    }
  }

  return (
    <div className="flex h-[calc(100vh-64px)]">
      <style>{`.cite { color: #e07c4a; font-size: 0.7em; font-weight: 700; vertical-align: super; text-decoration: none; padding: 0 1px; } .cite:hover { text-decoration: underline; }`}</style>

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside initial={{ width: 0, opacity: 0 }} animate={{ width: 260, opacity: 1 }} exit={{ width: 0, opacity: 0 }} className="bg-dark-900 border-r border-dark-700/50 flex flex-col overflow-hidden">
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
                    <button key={convo.id} onClick={() => setActiveConvoId(convo.id)} className={`w-full text-left px-3 py-2 rounded-lg transition group flex items-start gap-2 ${activeConvoId === convo.id ? 'bg-dark-700 text-white' : 'text-gray-400 hover:bg-dark-800 hover:text-white'}`}>
                      <MessageSquare className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 opacity-50" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{convo.title}</p>
                        <p className="text-[10px] text-gray-600">{formatDate(convo.updatedAt)}</p>
                      </div>
                      <button onClick={(e) => handleDeleteConversation(convo.id, e)} className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400"><Trash2 className="w-3 h-3" /></button>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="p-3 border-t border-dark-700/50">
              {isAuthenticated ? (
                <div className="flex items-center gap-2 px-2 py-1 text-xs text-gray-500">
                  <div className="w-6 h-6 rounded-full bg-accent-orange/20 flex items-center justify-center">
                    <span className="text-accent-orange font-medium">{user?.displayName?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}</span>
                  </div>
                  <span className="truncate">{user?.email}</span>
                </div>
              ) : (
                <a href="/login" className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600/50 rounded-lg text-xs text-gray-400 hover:text-white transition">
                  Sign in to sync chats
                </a>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-2 px-4 py-2 border-b border-dark-700/50">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg">
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
          <span className="text-sm text-gray-500 truncate">{activeConvoId ? conversations.find(c => c.id === activeConvoId)?.title : 'FitFact'}</span>
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
                    <button key={i} onClick={() => handleSend(q)} className="px-3 py-1.5 bg-dark-800 hover:bg-dark-700 border border-dark-600/50 rounded-full text-xs text-gray-400 hover:text-white transition">{q}</button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, idx) => <MessageBubble key={idx} message={msg} index={idx} expandedRefs={expandedRefs} toggleRefs={(i) => setExpandedRefs(p => ({ ...p, [i]: !p[i] }))} />)}

            {loading && (
              <div className="flex gap-1.5 items-center bg-dark-800 rounded-2xl px-4 py-3 w-fit border border-dark-600/50">
                {[0, 1, 2].map(i => <div key={i} className="w-2 h-2 bg-accent-orange rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
                <span className="text-gray-500 text-sm ml-2">Searching research...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-dark-700/50 p-4">
          <div className="max-w-3xl mx-auto flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} placeholder="Ask about fitness, nutrition..." className="flex-1 bg-dark-800 text-white placeholder-gray-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent-orange/50 border border-dark-600/50" disabled={loading} />
            <button onClick={() => handleSend()} disabled={!input.trim() || loading} className="px-4 bg-gradient-to-r from-accent-orange to-accent-gold rounded-xl text-white disabled:opacity-40 hover:opacity-90">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message, index, expandedRefs, toggleRefs }) {
  const data = useMemo(() => {
    if (message.role !== 'assistant') return null
    if (message.structured?.headline) return message.structured
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
          <p className="text-gray-300 text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </motion.div>
    )
  }

  const { headline, points, takeaway, references } = data

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
      <div className="bg-dark-800 rounded-2xl border border-dark-600/50 overflow-hidden">
        {headline && <div className="p-5 pb-4"><h2 className="text-xl font-semibold text-white leading-snug" dangerouslySetInnerHTML={{ __html: formatCitations(headline, references) }} /></div>}
        
        {points && points.length > 0 && (
          <div className="px-5 pb-5 space-y-3">
            {points.map((point, idx) => {
              const Icon = getIconForTitle(point.title)
              return (
                <div key={idx} className="bg-dark-700/40 rounded-xl p-4 border border-dark-600/20">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent-orange/10 flex items-center justify-center flex-shrink-0 mt-0.5"><Icon className="w-4 h-4 text-accent-orange" /></div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-white mb-1">{point.title}</h3>
                      <p className="text-sm text-gray-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatCitations(point.content, references) }} />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        
        {takeaway && <div className="mx-5 mb-5 p-3 bg-accent-orange/5 rounded-xl border border-accent-orange/20"><p className="text-sm text-gray-300"><span className="text-accent-orange font-semibold">💡 </span><span dangerouslySetInnerHTML={{ __html: formatCitations(takeaway, references) }} /></p></div>}
        
        {references && references.length > 0 && (
          <div className="border-t border-dark-600/50">
            <button onClick={() => toggleRefs(index)} className="w-full px-5 py-2.5 flex items-center justify-between text-xs text-gray-500 hover:text-gray-400 transition">
              <span className="flex items-center gap-1.5"><BookOpen className="w-3.5 h-3.5" />{references.length} sources</span>
              {expandedRefs[index] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            <AnimatePresence>
              {expandedRefs[index] && (
                <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                  <div className="px-5 pb-4 space-y-1.5">
                    {references.map((ref, i) => (
                      <a key={i} href={`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`} target="_blank" rel="noopener noreferrer" className="block p-2.5 bg-dark-700/30 rounded-lg hover:bg-dark-700/50 transition group">
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
        
        {message.metadata && (
          <div className="px-5 py-2 bg-dark-900/30 flex items-center gap-3 text-[10px] text-gray-600 border-t border-dark-600/30">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{message.metadata.response_time?.toFixed(1)}s</span>
            {message.metadata.cached && <span className="text-green-600">cached</span>}
          </div>
        )}
      </div>
    </motion.div>
  )
}
