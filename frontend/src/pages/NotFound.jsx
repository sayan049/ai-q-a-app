// frontend/src/pages/NotFound.jsx
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, AlertTriangle } from 'lucide-react'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] bg-dots flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <div className="w-20 h-20 rounded-2xl bg-red-500/10 border border-red-500/20
          flex items-center justify-center mx-auto mb-6">
          <AlertTriangle size={36} className="text-red-400" />
        </div>

        <h1 className="text-6xl font-bold gradient-text mb-4">404</h1>
        <p className="text-gray-400 text-lg mb-2">Page not found</p>
        <p className="text-gray-600 text-sm mb-8">
          The page you are looking for does not exist.
        </p>

        <button
          onClick={() => navigate('/')}
          className="btn-primary px-6 py-2.5 inline-flex items-center gap-2"
        >
          <Home size={16} />
          Go Home
        </button>
      </motion.div>
    </div>
  )
}