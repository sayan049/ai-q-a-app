import { useAuthStore } from '../../store/authStore'
import { useFileStore } from '../../store/fileStore'
import { LogOut, User, Cpu, FileText } from 'lucide-react'

export default function Navbar() {
  const { user, logout } = useAuthStore()
  const { activeFile } = useFileStore()

  return (
    <nav className="h-14 border-b border-[var(--border-glass)] bg-[var(--bg-primary)]/90
      backdrop-blur-md flex items-center justify-between px-6 flex-shrink-0 z-40">

      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-600
          flex items-center justify-center glow-cyan">
          <Cpu size={16} className="text-white" />
        </div>
        <span className="font-bold text-lg tracking-tight gradient-text">AI Q&A</span>
      </div>

      <div className="flex-1 flex justify-center px-8">
        {activeFile && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full
            bg-white/5 border border-white/10 max-w-sm">
            <FileText size={13} className="text-cyan-400 flex-shrink-0" />
            <span className="text-xs text-gray-300 truncate">{activeFile.original_filename || activeFile.filename}</span>
            {activeFile.status === 'ready' && (
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 flex-shrink-0
                shadow-[0_0_6px_rgba(34,197,94,0.8)]" />
            )}
            {activeFile.status === 'processing' && (
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0
                animate-pulse" />
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:block text-right">
          <p className="text-xs font-medium text-gray-200 leading-none">{user?.username}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">{user?.email}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10
          flex items-center justify-center">
          <User size={15} className="text-gray-400" />
        </div>
        <button
          onClick={logout}
          title="Logout"
          className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
        >
          <LogOut size={17} />
        </button>
      </div>
    </nav>
  )
}