import { useEffect } from 'react'
import { Plus } from 'lucide-react'
import { useFileStore } from '../../store/fileStore'
import { useChatStore } from '../../store/chatStore'
import FileList from '../upload/FileList'

export default function Sidebar() {
  const { fetchFiles, setActiveFile } = useFileStore()
  const { clearMessages } = useChatStore()

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

  const handleNew = () => {
    setActiveFile(null)
    clearMessages()
  }

  return (
    <aside
      className="w-64 border-r border-[var(--border-glass)] bg-[var(--bg-secondary)]
      flex flex-col flex-shrink-0 overflow-hidden"
    >
      <div className="p-4 border-b border-[var(--border-glass)]">
        <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-widest mb-3">
          Library
        </p>

        <button
          onClick={handleNew}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg
          border border-dashed border-white/10 text-gray-500 text-sm
          hover:border-cyan-500/40 hover:text-cyan-400 transition-all group"
        >
          <Plus
            size={15}
            className="group-hover:rotate-90 transition-transform duration-200"
          />
          Upload New File
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <FileList />
      </div>
    </aside>
  )
}