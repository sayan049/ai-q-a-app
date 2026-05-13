import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Cpu } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'

export default function StreamingText() {
  const { streamingContent } = useChatStore()

  return (
    <div className="flex gap-3">
      <div className="w-7 h-7 rounded-full bg-cyan-500/20 border border-cyan-500/30
        flex items-center justify-center flex-shrink-0 mt-0.5 animate-pulse">
        <Cpu size={13} className="text-cyan-400" />
      </div>
      <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-tl-sm text-sm
        bg-white/5 border border-white/8 text-gray-200 leading-relaxed">
        {streamingContent ? (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {streamingContent}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        )}
        <span className="cursor-blink" />
      </div>
    </div>
  )
}