import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useFileStore } from '../../store/fileStore'
import { chatAPI } from '../../api/chat'
import { useSSE } from '../../hooks/useSSE'
import ChatMessage from './ChatMessage'
import StreamingText from './StreamingText'
import ChatInput from './ChatInput'
import { MessageSquare, Trash2 } from 'lucide-react'

export default function ChatWindow() {
  const { messages, isStreaming, setMessages, clearMessages } = useChatStore()
  const { activeFile } = useFileStore()
  const { streamQuestion } = useSSE()
  const bottomRef = useRef(null)

  const isReady = activeFile?.status === 'ready'

  useEffect(() => {
    if (!activeFile?.id) return
    clearMessages()
    chatAPI.getHistory(activeFile.id)
      .then((res) => setMessages(res.data.messages || []))
      .catch(() => {})
  }, [activeFile?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const handleSend = (query) => {
    if (!activeFile?.id || !isReady) return
    streamQuestion(query, activeFile.id)
  }

  const handleClear = async () => {
    if (!activeFile?.id) return
    await chatAPI.clearHistory(activeFile.id).catch(() => {})
    clearMessages()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3
        border-b border-[var(--border-glass)] flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare size={15} className="text-cyan-400" />
          <span className="text-sm font-medium text-gray-300">Chat</span>
          {messages.length > 0 && (
            <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded-full text-gray-500">
              {messages.length}
            </span>
          )}
        </div>
        {messages.length > 0 && (
          <button onClick={handleClear}
            className="p-1.5 text-gray-600 hover:text-red-400 transition-colors">
            <Trash2 size={13} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-3">
              <MessageSquare size={22} className="text-gray-600" />
            </div>
            <p className="text-gray-500 text-sm font-medium">
              {isReady ? 'Ask anything about this file' : 'File is being processed...'}
            </p>
            <p className="text-gray-700 text-xs mt-1">
              {isReady ? 'Questions, summaries, timestamps...' : 'Please wait a moment'}
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isStreaming && <StreamingText />}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={!isReady} />
    </div>
  )
}