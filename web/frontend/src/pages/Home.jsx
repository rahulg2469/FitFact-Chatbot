import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { ArrowRight, Sparkles, BookOpen, Zap, Target, Flame } from 'lucide-react'
import { motion } from 'framer-motion'

const quickQuestions = [
  {
    icon: Target,
    title: "Protein Intake",
    question: "What's the ideal protein intake for muscle gain?",
    color: "from-accent-orange to-orange-600",
  },
  {
    icon: Flame,
    title: "HIIT vs Cardio",
    question: "Is HIIT better than steady cardio for fat loss?",
    color: "from-accent-coral to-red-600",
  },
  {
    icon: Zap,
    title: "Workout Frequency",
    question: "How many times per week should I train?",
    color: "from-accent-blue to-blue-600",
  },
  {
    icon: Sparkles,
    title: "Recovery",
    question: "What are the best recovery methods after training?",
    color: "from-purple-500 to-violet-600",
  },
]

const features = [
  {
    icon: BookOpen,
    title: "Research-Backed",
    description: "Every answer cites peer-reviewed studies from PubMed"
  },
  {
    icon: Sparkles,
    title: "AI-Powered",
    description: "Claude AI synthesizes research into clear, actionable advice"
  },
  {
    icon: Target,
    title: "Personalized",
    description: "Save your history and get tailored recommendations"
  },
]

export default function Home() {
  const { user, isAuthenticated } = useAuth()

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good Morning'
    if (hour < 17) return 'Good Afternoon'
    return 'Good Evening'
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Hero Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          {isAuthenticated ? (
            <>
              <span className="text-gray-400">{getGreeting()}</span>
              <br />
              <span className="gradient-text">{user?.display_name?.split(' ')[0]}</span>
            </>
          ) : (
            <>
              <span className="text-white">Evidence-Based</span>
              <br />
              <span className="gradient-text">Fitness Advice</span>
            </>
          )}
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          Get fitness and nutrition advice backed by peer-reviewed research. 
          Every response includes citations to scientific studies.
        </p>
      </motion.div>

      {/* Quick Questions */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Quick Questions</h2>
          <Link 
            to="/chat" 
            className="text-accent-orange hover:text-accent-gold flex items-center gap-1 text-sm font-medium"
          >
            Ask anything <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickQuestions.map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Link
                to={`/chat?q=${encodeURIComponent(item.question)}`}
                className="block bg-dark-800 rounded-2xl p-5 border border-dark-600/50 card-hover group"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mb-4`}>
                  <item.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold text-white mb-2 group-hover:text-accent-orange transition-colors">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-400 line-clamp-2">
                  {item.question}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mb-16">
        <h2 className="text-xl font-semibold text-white mb-6">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1 }}
              className="bg-dark-800/50 rounded-2xl p-6 border border-dark-600/30"
            >
              <div className="w-10 h-10 rounded-lg bg-dark-700 flex items-center justify-center mb-4">
                <feature.icon className="w-5 h-5 text-accent-orange" />
              </div>
              <h3 className="font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-400">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      {!isAuthenticated && (
        <motion.section 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="text-center bg-gradient-to-br from-dark-700 to-dark-800 rounded-3xl p-8 border border-dark-600/50"
        >
          <h2 className="text-2xl font-bold text-white mb-3">
            Ready to get started?
          </h2>
          <p className="text-gray-400 mb-6">
            Sign in to save your chat history and get personalized recommendations.
          </p>
          <Link
            to="/chat"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-accent-orange to-accent-gold text-white font-semibold rounded-xl hover:opacity-90 transition-opacity"
          >
            Start Chatting <ArrowRight className="w-5 h-5" />
          </Link>
        </motion.section>
      )}
    </div>
  )
}
