import { useState, useCallback } from 'react'
import { useFileStore } from '../store/fileStore'

const ALLOWED_EXTENSIONS = /\.(pdf|mp3|wav|ogg|webm|mp4|avi|mov|flac|m4a)$/i
const MAX_SIZE = 500 * 1024 * 1024

export function useFileUpload() {
  const [error, setError] = useState(null)
  const { uploadFile, isUploading, uploadProgress } = useFileStore()

  const upload = useCallback(async (file) => {
    setError(null)
    if (!file) return { success: false }
    if (!ALLOWED_EXTENSIONS.test(file.name)) {
      setError('Unsupported file type. Upload PDF, audio, or video.')
      return { success: false }
    }
    if (file.size > MAX_SIZE) {
      setError('File too large. Max size is 500MB.')
      return { success: false }
    }
    if (file.size === 0) {
      setError('File is empty.')
      return { success: false }
    }
    const result = await uploadFile(file)
    if (!result.success) setError(result.error)
    return result
  }, [uploadFile])

  return { upload, isUploading, progress: uploadProgress, error, setError }
}