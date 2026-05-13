import { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import { Video } from 'lucide-react'

export default function VideoPlayer({ fileId, filename, filePath }) {
  const videoRef = useRef(null)
  const { seekTo, clearSeek } = useChatStore()

  useEffect(() => {
    if (seekTo !== null && videoRef.current) {
      videoRef.current.currentTime = seekTo
      videoRef.current.play()
      clearSeek()
    }
  }, [seekTo, clearSeek])

  return (
    <div className="p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2 mb-1">
        <Video size={14} className="text-purple-400" />
        <span className="text-xs text-gray-400 truncate">{filename}</span>
      </div>
      <video
        ref={videoRef}
        src={filePath}
        controls
        className="w-full rounded-xl bg-black border border-white/10"
        style={{ maxHeight: '240px' }}
      />
    </div>
  )
}