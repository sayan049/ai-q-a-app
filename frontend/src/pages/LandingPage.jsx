import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { Cpu, Eye, EyeOff, ArrowRight, Zap, Shield, Brain } from 'lucide-react'
import toast from 'react-hot-toast'

export default function LandingPage() {
  const navigate = useNavigate()
  const { login, register, isLoading } = useAuthStore()
  const [mode, setMode] = useState('login')
  const [showPassword, setShowPassword] = useState(false)
  const [form, setForm] = useState({ email: '', username: '', password: '' })

  const handleSubmit = async (e) => {
    e.preventDefault()
    let result
    if (mode === 'login') {
      result = await login(form.email, form.password)
    } else {
      result = await register(form.email, form.username, form.password)
    }
    if (result.success) {
      toast.success(mode === 'login' ? 'Welcome back!' : 'Account created!')
      navigate('/dashboard')
    } else {
      toast.error(result.error || 'Something went wrong')
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] bg-dots flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/5 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-400 to-purple-600
            flex items-center justify-center mx-auto mb-4 glow-cyan">
            <Cpu size={28} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text mb-2">AI Q&A</h1>
          <p className="text-gray-500 text-sm">Chat with your documents and media files</p>
        </div>

        <div className="glass p-6">
          <div className="flex rounded-lg overflow-hidden border border-white/10 mb-6">
            {['login', 'register'].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-2 text-sm font-medium capitalize transition-all ${
                  mode === m
                    ? 'bg-gradient-to-r from-cyan-500/20 to-purple-600/20 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 mb-1.5 block">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@example.com"
                required
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5
                  text-sm text-gray-200 placeholder-gray-600 outline-none
                  focus:border-cyan-500/50 focus:shadow-[0_0_0_3px_rgba(0,217,255,0.05)]
                  transition-all"
              />
            </div>

            <AnimatePresence>
              {mode === 'register' && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                >
                  <label className="text-xs text-gray-500 mb-1.5 block">Username</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    placeholder="johndoe"
                    required={mode === 'register'}
                    minLength={3}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5
                      text-sm text-gray-200 placeholder-gray-600 outline-none
                      focus:border-cyan-500/50 transition-all"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label className="text-xs text-gray-500 mb-1.5 block">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5
                    text-sm text-gray-200 placeholder-gray-600 outline-none pr-10
                    focus:border-cyan-500/50 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-2.5 flex items-center justify-center gap-2 mt-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </div>

        <div className="mt-6 grid grid-cols-3 gap-3">
          {[
            { icon: Brain,  label: 'AI Powered',    sub: 'Groq LLM' },
            { icon: Zap,    label: 'Real-time',      sub: 'Streaming' },
            { icon: Shield, label: 'Secure',         sub: 'JWT Auth' },
          ].map(({ icon: Icon, label, sub }) => (
            <div key={label} className="glass p-3 text-center">
              <Icon size={16} className="mx-auto mb-1 text-cyan-400" />
              <p className="text-xs font-medium text-gray-300">{label}</p>
              <p className="text-[10px] text-gray-600">{sub}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}