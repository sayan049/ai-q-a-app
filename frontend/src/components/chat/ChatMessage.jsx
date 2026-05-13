// frontend/src/components/chat/ChatMessage.jsx
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { User, Cpu, Clock } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { formatTime } from '../../utils/formatTime'

export default function ChatMessage({ message }) {
  const { setSeekTo } = useChatStore()
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center
        flex-shrink-0 mt-0.5 ${
          isUser
            ? 'bg-purple-500/20 border border-purple-500/30'
            : 'bg-cyan-500/20 border border-cyan-500/30'
        }`}>
        {isUser
          ? <User size={13} className="text-purple-400" />
          : <Cpu  size={13} className="text-cyan-400"   />
        }
      </div>

      {/* Content */}
      <div className={`max-w-[80%] flex flex-col gap-2
        ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Message bubble */}
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-purple-500/15 border border-purple-500/20 text-gray-200 rounded-tr-sm'
            : 'bg-white/5 border border-white/8 text-gray-200 rounded-tl-sm'
        }`}>
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp chips — only for AI messages with timestamps */}
        {!isUser && message.timestamps && message.timestamps.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            <span className="text-[10px] text-gray-600 self-center">
              Jump to:
            </span>
            {message.timestamps.map((ts, i) => (
              <button
                key={i}
                onClick={() => setSeekTo(ts.start)}
                title={`"${ts.text?.slice(0, 50)}..."`}
                className="flex items-center gap-1 px-2.5 py-1 rounded-full
                  text-xs bg-cyan-500/10 border border-cyan-500/20 text-cyan-400
                  hover:bg-cyan-500/25 hover:border-cyan-500/40
                  transition-all font-mono cursor-pointer"
              >
                <Clock size={10} />
                {formatTime(ts.start)}
                {ts.end && ts.end !== ts.start && (
                  <span className="text-cyan-600">
                    →{formatTime(ts.end)}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Sources for PDF */}
        {!isUser && message.sources && message.sources.length > 0
          && message.sources.some(s => s.page_num) && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.sources
              .filter(s => s.page_num)
              .map((s, i) => (
                <span key={i}
                  className="text-[10px] px-2 py-0.5 rounded-full
                    bg-orange-500/10 border border-orange-500/20 text-orange-400">
                  Page {s.page_num}
                </span>
              ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}