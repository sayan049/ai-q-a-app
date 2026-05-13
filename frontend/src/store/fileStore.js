// frontend/src/store/fileStore.js
import { create } from 'zustand'
import { filesAPI } from '../api/files'

export const useFileStore = create((set, get) => ({
  files: [],
  activeFile: null,
  isLoading: false,
  isUploading: false,
  uploadProgress: 0,

  fetchFiles: async () => {
    set({ isLoading: true })
    try {
      const res = await filesAPI.list()
      set({ files: res.data.files || [], isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  uploadFile: async (file, onProgress) => {
    set({ isUploading: true, uploadProgress: 0 })
    try {
      const res = await filesAPI.upload(file, (p) => {
        set({ uploadProgress: p })
        if (onProgress) onProgress(p)
      })
      const newFile = res.data
      // file_id from upload response = id in list response
      const fileId = newFile.file_id || newFile.id

      // Add placeholder to list immediately
      set((state) => ({
        files: [{
          id: fileId,
          user_id: newFile.user_id,
          filename: newFile.filename,
          file_type: newFile.file_type,
          status: 'processing',
          size_bytes: newFile.size_bytes,
          chunk_count: 0,
          duration: null,
          page_count: null,
        }, ...state.files],
        isUploading: false,
        uploadProgress: 0,
      }))

      // Start polling for status updates
      get().pollFileStatus(fileId)
      return { success: true, fileId }
    } catch (err) {
      set({ isUploading: false, uploadProgress: 0 })
      return {
        success: false,
        error: err.response?.data?.detail || 'Upload failed',
      }
    }
  },

  pollFileStatus: (fileId) => {
    let attempts = 0
    const maxAttempts = 40 // 2 minutes max polling

    const interval = setInterval(async () => {
      attempts++
      if (attempts > maxAttempts) {
        clearInterval(interval)
        return
      }

      try {
        const res = await filesAPI.getFile(fileId)
        const updated = res.data

        set((state) => ({
          files: state.files.map((f) =>
            f.id === fileId ? { ...f, ...updated } : f
          ),
          activeFile:
            state.activeFile?.id === fileId
              ? { ...state.activeFile, ...updated }
              : state.activeFile,
        }))

        if (updated.status === 'ready' || updated.status === 'failed') {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 3000)
  },

  setActiveFile: (file) => set({ activeFile: file }),

  deleteFile: async (fileId) => {
    try {
      await filesAPI.deleteFile(fileId)
      set((state) => ({
        files: state.files.filter((f) => f.id !== fileId),
        activeFile:
          state.activeFile?.id === fileId ? null : state.activeFile,
      }))
      return { success: true }
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || 'Delete failed',
      }
    }
  },
}))