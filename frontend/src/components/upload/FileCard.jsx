import { motion } from 'framer-motion'
import {
  FileText, Music, Video, Trash2,
  CheckCircle, AlertCircle, Loader2, Clock,
} from 'lucide-react'
import { useFileStore } from '../../store/fileStore'
import { formatFileSize } from '../../utils/formatTime'

const FILE_ICONS = {
  pdf:   { icon: FileText, color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20' },
  audio: { icon: Music,    color: 'text-cyan-400',   bg: 'bg-cyan-500/10',   border: 'border-cyan-500/20'   },
  video: { icon: Video,    color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
}

const STATUS_CONFIG = {
  ready:      { icon: CheckCircle,  color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', label: 'Ready',      animate: false },
  processing: { icon: Loader2,      color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Processing', animate: true  },
  uploading:  { icon: Loader2,      color: 'text-blue-400',  bg: 'bg-blue-500/10',  border: 'border-blue-500/20',  label: 'Uploading',  animate: true  },
  failed:     { icon: AlertCircle,  color: 'text-red-400',   bg: 'bg-red-500/10',   border: 'border-red-500/20',   label: 'Failed',     animate: false },
}

export default function FileCard({ file, isActive, onClick }) {
  const { deleteFile } = useFileStore()

  const fileConfig   = FILE_ICONS[file.file_type]   || FILE_ICONS.pdf
  const statusConfig = STATUS_CONFIG[file.status]   || STATUS_CONFIG.processing

  const FileIcon   = fileConfig.icon
  const StatusIcon = statusConfig.icon

  const handleDelete = async (e) => {
    e.stopPropagation()
    await deleteFile(file.id)
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onClick}
      className={`group relative p-3 rounded-xl cursor-pointer transition-all border ${
        isActive
          ? 'bg-cyan-500/10 border-cyan-500/25 shadow-[0_0_15px_rgba(0,217,255,0.05)]'
          : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'
      }`}
    >
      <div className="flex items-start gap-2.5">

        {/* File type icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
          ${fileConfig.bg} border ${fileConfig.border}`}>
          <FileIcon size={15} className={fileConfig.color} />
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-200 truncate leading-snug">
            {file.filename || file.original_filename}
          </p>

          {/* Status + size */}
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className={`inline-flex items-center gap-1 text-[9px] font-medium
              px-1.5 py-0.5 rounded border
              ${statusConfig.bg} ${statusConfig.border} ${statusConfig.color}`}>
              <StatusIcon
                size={9}
                className={statusConfig.animate ? 'animate-spin' : ''}
              />
              {statusConfig.label}
            </span>
            <span className="text-[10px] text-gray-600">
              {formatFileSize(file.size_bytes)}
            </span>
          </div>

          {/* Extra metadata */}
          <div className="flex items-center gap-2 mt-1">
            {file.page_count > 0 && (
              <span className="text-[10px] text-gray-600">
                {file.page_count} pages
              </span>
            )}
            {file.duration > 0 && (
              <span className="text-[10px] text-gray-600 flex items-center gap-0.5">
                <Clock size={8} />
                {Math.floor(file.duration / 60)}m {Math.floor(file.duration % 60)}s
              </span>
            )}
            {file.chunk_count > 0 && (
              <span className="text-[10px] text-gray-600">
                {file.chunk_count} chunks
              </span>
            )}
          </div>

          {/* Error message */}
          {file.status === 'failed' && file.error_message && (
            <p className="mt-1 text-[10px] text-red-400 truncate">
              {file.error_message}
            </p>
          )}
        </div>

        {/* Delete button */}
        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-1 rounded
            text-gray-600 hover:text-red-400 transition-all flex-shrink-0 mt-0.5"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Processing progress bar */}
      {(file.status === 'processing' || file.status === 'uploading') && (
        <div className="mt-2 h-0.5 w-full bg-white/5 rounded-full overflow-hidden">
          <div className="h-full shimmer rounded-full" />
        </div>
      )}
    </motion.div>
  )
}