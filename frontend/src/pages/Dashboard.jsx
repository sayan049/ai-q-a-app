import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useFileStore } from '../store/fileStore'
import { useChatStore } from '../store/chatStore'
import { chatAPI } from '../api/chat'
import Navbar from '../components/layout/Navbar'
import Sidebar from '../components/layout/Sidebar'
import DropZone from '../components/upload/DropZone'
import ChatWindow from '../components/chat/ChatWindow'
import AudioPlayer from '../components/media/AudioPlayer'
import VideoPlayer from '../components/media/VideoPlayer'
import { FileText, AlertCircle, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

function PDFInfo({ file }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <div className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20
        flex items-center justify-center flex-shrink-0">
        <FileText size={16} className="text-orange-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-200 truncate">{file.filename}</p>
        <p className="text-[10px] text-gray-500">
          {file.page_count ? `${file.page_count} pages` : 'PDF Document'}
          {file.chunk_count ? ` • ${file.chunk_count} chunks indexed` : ''}
        </p>
      </div>
      <span className="px-2 py-0.5 rounded-full bg-green-500/10 border border-green-500/20
        text-green-400 text-[9px] font-medium flex-shrink-0">
        Ready
      </span>
    </div>
  )
}

function MediaPanel({ file, isCollapsed, onToggle }) {
  const [isSummarizing, setIsSummarizing] = useState(false);
  const { finishStreaming } = useChatStore();

  if (!file) return null

  const ext = file.filename?.split('.').pop() || 'file'
  const filePath = `/uploads/${file.user_id}/${file.id}/original.${ext}`

  const handleGetSummary = async (e) => {
    e.stopPropagation(); // Don't trigger collapse
    if (isSummarizing) return;
    
    setIsSummarizing(true);
    const toastId = toast.loading("Generating AI summary...");
    
    try {
      const res = await chatAPI.getSummary(file.id);
      
      // Inject the summary as a special AI message into the chat store
      const summaryMarkdown = `### 📝 AI Summary\n${res.data.summary}\n\n**Key Topics Covered:**\n${res.data.key_topics.map(t => `- ${t}`).join('\n')}`;
      
      finishStreaming(
        summaryMarkdown, 
        [], // no timestamps for summary
        [], // no sources for summary
        'summary-' + Date.now()
      );
      
      toast.success("Summary added to chat!", { id: toastId });
    } catch (err) {
      console.error(err);
      toast.error("Failed to generate summary.", { id: toastId });
    } finally {
      setIsSummarizing(false);
    }
  };

  return (
    <div className="border-b border-[var(--border-glass)] flex-shrink-0">

      {/* Header with collapse toggle */}
      <div className="w-full flex items-center justify-between px-4 py-1.5
          border-b border-[var(--border-glass)] bg-white/[0.02]">
        
        <button
          onClick={onToggle}
          className="flex items-center gap-2 text-[10px] text-gray-500 hover:text-gray-300 
            transition-colors uppercase tracking-widest font-medium"
        >
          <span>
            {file.file_type === 'pdf'   ? '📄 Document' :
             file.file_type === 'audio' ? '🎵 Audio' :
             '🎬 Video'}
          </span>
          {isCollapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
        </button>

        {/* Bonus Feature: AI Summary Button */}
        {!isCollapsed && file.status === 'ready' && (
          <button
            onClick={handleGetSummary}
            disabled={isSummarizing}
            className="flex items-center gap-1.5 text-[9px] font-bold px-2 py-0.5 rounded-md
              bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 
              hover:bg-cyan-500/20 transition-all disabled:opacity-50"
          >
            <Sparkles size={10} className={isSummarizing ? "animate-spin" : ""} />
            {isSummarizing ? "SUMMARIZING..." : "GENERATE SUMMARY"}
          </button>
        )}
      </div>

      {/* Content — collapsible */}
      {!isCollapsed && (
        <div className="bg-black/10">
          {file.file_type === 'audio' && (
            <AudioPlayer
              fileId={file.id}
              filename={file.filename}
              filePath={filePath}
            />
          )}
          {file.file_type === 'video' && (
            <div className="p-4 flex justify-center">
               <VideoPlayer
                fileId={file.id}
                filename={file.filename}
                filePath={filePath}
              />
            </div>
          )}
          {file.file_type === 'pdf' && (
            <PDFInfo file={file} />
          )}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const { activeFile } = useFileStore()
  const [mediaCollapsed, setMediaCollapsed] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) navigate('/')
  }, [isAuthenticated, navigate])

  useEffect(() => {
    setMediaCollapsed(false)
  }, [activeFile?.id])

  const showDropZone = !activeFile
  const isProcessing = activeFile?.status === 'processing' || activeFile?.status === 'uploading'
  const isFailed     = activeFile?.status === 'failed'

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[var(--bg-primary)]">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-hidden relative">
          {/* Background decoration */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-[100px] pointer-events-none" />
          
          {showDropZone ? (
            <DropZone />
          ) : (
            <div className="flex flex-col h-full relative z-10">

              {/* Processing banner */}
              {isProcessing && (
                <div className="flex items-center justify-center gap-2 px-4 py-2
                  bg-amber-500/5 border-b border-amber-500/10 flex-shrink-0">
                  <div className="w-3 h-3 border-2 border-amber-500/30
                    border-t-amber-500 rounded-full animate-spin" />
                  <p className="text-amber-400 text-[11px] font-medium tracking-wide">
                    AI is currently processing your file...
                  </p>
                </div>
              )}

              {/* Failed banner */}
              {isFailed && (
                <div className="flex items-center gap-2 px-4 py-2
                  bg-red-500/5 border-b border-red-500/10 flex-shrink-0">
                  <AlertCircle size={12} className="text-red-400 flex-shrink-0" />
                  <p className="text-red-400 text-[11px] truncate font-medium">
                    Error: {activeFile.error_message || 'Processing failed'}
                  </p>
                </div>
              )}

              {/* Media Panel — compact and collapsible */}
              <MediaPanel
                file={activeFile}
                isCollapsed={mediaCollapsed}
                onToggle={() => setMediaCollapsed(!mediaCollapsed)}
              />

              {/* Chat — fills ALL remaining space */}
              <div className="flex-1 overflow-hidden min-h-0 bg-transparent">
                <ChatWindow />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}