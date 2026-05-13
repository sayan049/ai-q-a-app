import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, Music, Video, AlertCircle } from 'lucide-react'
import { useFileUpload } from '../../hooks/useFileUpload'
import { useFileStore } from '../../store/fileStore'
import toast from 'react-hot-toast'

export default function DropZone() {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)
  const { upload, isUploading, progress, error, setError } = useFileUpload()
  const { setActiveFile, files } = useFileStore()

  const handleDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) await handleUpload(file)
  }

  const handleUpload = async (file) => {
    setError(null)
    const result = await upload(file)
    if (result.success) {
      toast.success('File uploaded! Processing started...')
    } else {
      toast.error(result.error || error || 'Upload failed')
    }
  }

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 bg-grid">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl"
      >
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-2">
            <span className="gradient-text">Upload & Ask</span>
          </h2>
          <p className="text-gray-500 text-sm">
            Drop a PDF, audio, or video file and start chatting with AI
          </p>
        </div>

        <motion.div
          onClick={() => !isUploading && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          animate={isDragging
            ? { scale: 1.02, borderColor: 'rgba(0,217,255,0.6)' }
            : { scale: 1,    borderColor: 'rgba(255,255,255,0.08)' }
          }
          className={`relative rounded-2xl border-2 border-dashed p-12 cursor-pointer
            transition-colors duration-300 text-center overflow-hidden
            ${isDragging ? 'bg-cyan-500/5' : 'bg-white/2 hover:bg-white/5'}
            ${isUploading ? 'pointer-events-none' : ''}`}
        >
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".pdf,.mp3,.wav,.ogg,.webm,.mp4,.avi,.mov,.flac,.m4a"
            onChange={(e) => e.target.files[0] && handleUpload(e.target.files[0])}
          />

          <AnimatePresence mode="wait">
            {!isUploading ? (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              >
                <div className={`w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center
                  transition-colors ${isDragging ? 'bg-cyan-500/20' : 'bg-white/5'}`}>
                  <Upload size={28} className={isDragging ? 'text-cyan-400' : 'text-gray-500'} />
                </div>
                <p className="text-gray-300 font-medium mb-1">
                  {isDragging ? 'Drop it!' : 'Drag & drop or click to upload'}
                </p>
                <p className="text-gray-600 text-sm">Max 500MB</p>

                <div className="mt-6 flex items-center justify-center gap-6 text-xs text-gray-600">
                  <div className="flex items-center gap-1.5">
                    <FileText size={14} className="text-orange-400" />PDF
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Music size={14} className="text-cyan-400" />Audio
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Video size={14} className="text-purple-400" />Video
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="uploading"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              >
                <div className="relative w-20 h-20 mx-auto mb-5">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="36" fill="transparent"
                      stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                    <circle cx="40" cy="40" r="36" fill="transparent"
                      stroke="#00d9ff" strokeWidth="4"
                      strokeDasharray={226}
                      strokeDashoffset={226 - (226 * progress) / 100}
                      className="transition-all duration-300"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center
                    text-cyan-400 font-bold text-sm">{progress}%</span>
                </div>
                <p className="text-gray-300 font-medium">Uploading...</p>
                <p className="text-gray-600 text-sm mt-1">Processing will start automatically</p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-red-500/10
              border border-red-500/20 text-red-400 text-sm"
          >
            <AlertCircle size={16} className="flex-shrink-0" />
            {error}
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}