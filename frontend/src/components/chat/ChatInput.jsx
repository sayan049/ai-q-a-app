import { useState } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'

export default function ChatInput({ onSend, disabled }) {
  const [query, setQuery] = useState('')
  const { isStreaming } = useChatStore()

  const handleSubmit = (e) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || isStreaming || disabled) return
    setQuery('')
    onSend(q)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) handleSubmit(e)
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-[var(--border-glass)]">
      <div className={`flex items-end gap-3 p-3 rounded-xl border transition-all
        ${disabled || isStreaming
          ? 'border-white/5 bg-white/2'
          : 'border-white/10 bg-white/5 focus-within:border-cyan-500/40 focus-within:shadow-[0_0_20px_rgba(0,217,255,0.05)]'
        }`}
      >
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder={disabled ? 'Select a ready file to start chatting...' : 'Ask anything about this file...'}
          disabled={disabled || isStreaming}
          rows={1}
          className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600
            resize-none outline-none min-h-[20px] max-h-[120px] leading-relaxed"
          style={{ height: 'auto' }}
          onInput={(e) => {
            e.target.style.height = 'auto'
            e.target.style.height = e.target.scrollHeight + 'px'
          }}
        />
        <button
          type="submit"
          disabled={!query.trim() || isStreaming || disabled}
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
            transition-all ${query.trim() && !isStreaming && !disabled
              ? 'bg-gradient-to-br from-cyan-500 to-purple-600 text-white hover:shadow-[0_0_15px_rgba(0,217,255,0.4)] cursor-pointer'
              : 'bg-white/5 text-gray-600 cursor-not-allowed'
            }`}
        >
          {isStreaming
            ? <Loader2 size={15} className="animate-spin" />
            : <Send size={15} />
          }
        </button>
      </div>
      <p className="text-[10px] text-gray-700 mt-2 text-center">
        Enter to send • Shift+Enter for new line
      </p>
    </form>
  )
}