// frontend/src/components/media/AudioPlayer.jsx
import { useEffect, useRef, useState } from 'react'
import { Play, Pause } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { formatTime } from '../../utils/formatTime'

export default function AudioPlayer({ fileId, filename, filePath }) {
  const containerRef = useRef(null)
  const wsRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isReady, setIsReady] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const { seekTo, clearSeek } = useChatStore()

  useEffect(() => {
    if (wsRef.current) {
      try { wsRef.current.destroy() } catch {}
      wsRef.current = null
    }

    setIsReady(false)
    setLoadError(false)
    setCurrentTime(0)
    setDuration(0)
    setIsPlaying(false)

    if (containerRef.current) {
      containerRef.current.innerHTML = ''
    }

    let ws = null
    let destroyed = false

    const init = async () => {
      try {
        const WaveSurfer = (await import('wavesurfer.js')).default
        if (destroyed || !containerRef.current) return

        ws = WaveSurfer.create({
          container: containerRef.current,
          waveColor: 'rgba(0,217,255,0.25)',
          progressColor: 'rgba(0,217,255,0.85)',
          cursorColor: '#00d9ff',
          barWidth: 2,
          barRadius: 2,
          barGap: 1,
          height: 32,
          normalize: true,
        })

        wsRef.current = ws
        const audioUrl = filePath || `/uploads/${fileId}`

        ws.on('ready', () => {
          if (!destroyed) { setDuration(ws.getDuration()); setIsReady(true) }
        })
        ws.on('audioprocess', () => {
          if (!destroyed) setCurrentTime(ws.getCurrentTime())
        })
        ws.on('play',   () => { if (!destroyed) setIsPlaying(true) })
        ws.on('pause',  () => { if (!destroyed) setIsPlaying(false) })
        ws.on('finish', () => {
          if (!destroyed) { setIsPlaying(false); setCurrentTime(0) }
        })
        ws.on('error', (err) => {
          if (!destroyed) { setLoadError(true); setIsReady(false) }
        })

        ws.load(audioUrl)
      } catch (err) {
        if (!destroyed) setLoadError(true)
      }
    }

    init()

    return () => {
      destroyed = true
      if (ws) { try { ws.pause(); ws.destroy() } catch {} }
      wsRef.current = null
    }
  }, [fileId, filePath])

  useEffect(() => {
    if (seekTo !== null && wsRef.current && isReady && duration > 0) {
      wsRef.current.seekTo(Math.min(seekTo / duration, 1))
      wsRef.current.play()
      clearSeek()
    }
  }, [seekTo, isReady, duration, clearSeek])

  const togglePlay = () => {
    if (wsRef.current && isReady) wsRef.current.playPause()
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2">

      {/* Play/Pause button */}
      <button
        onClick={togglePlay}
        disabled={!isReady}
        className={`w-8 h-8 rounded-full flex items-center justify-center
          flex-shrink-0 transition-all
          ${isReady
            ? 'bg-gradient-to-br from-cyan-500 to-purple-600 cursor-pointer hover:shadow-[0_0_15px_rgba(0,217,255,0.4)]'
            : 'bg-white/5 cursor-not-allowed opacity-50'
          }`}
      >
        {isPlaying
          ? <Pause size={12} className="text-white" />
          : <Play  size={12} className="text-white ml-0.5" />
        }
      </button>

      {/* Waveform — fills remaining space */}
      <div className="flex-1 min-w-0">
        <div
          ref={containerRef}
          className="w-full rounded overflow-hidden bg-black/20"
          style={{ height: '32px' }}
        />
      </div>

      {/* Time display */}
      <span className="text-[10px] font-mono text-gray-500 flex-shrink-0 whitespace-nowrap">
        {formatTime(currentTime)}/{formatTime(duration)}
      </span>

      {/* Spinner while loading */}
      {!isReady && !loadError && (
        <div className="w-3 h-3 border border-cyan-500/30 border-t-cyan-500
          rounded-full animate-spin flex-shrink-0" />
      )}
    </div>
  )
}