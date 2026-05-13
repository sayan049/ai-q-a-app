// frontend/src/hooks/useSSE.js
import { useCallback } from 'react'
import { useChatStore } from '../store/chatStore'

// Strip trailing slash to prevent double-slash URLs
const RAW_URL = import.meta.env.VITE_API_URL || ''
const API_BASE = RAW_URL
  ? `${RAW_URL.replace(/\/$/, '')}/api/v1`
  : '/api/v1'

export function useSSE() {
  const {
    addUserMessage,
    startStreaming,
    appendToken,
    finishStreaming,
  } = useChatStore()

  const streamQuestion = useCallback(async (query, fileId) => {
    addUserMessage(query)
    startStreaming()

    const token = localStorage.getItem('access_token')
    const url = `${API_BASE}/chat/ask?query=${encodeURIComponent(query)}&file_id=${encodeURIComponent(fileId)}`

    try {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'text/event-stream',
        },
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        finishStreaming(
          `❌ Error: ${err.detail || response.statusText}`,
          [], [], 'error-' + Date.now()
        )
        return
      }

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim()
            if (!jsonStr) continue
            try {
              const data = JSON.parse(jsonStr)
              if (data.error) {
                finishStreaming(`❌ ${data.error}`, [], [], 'error-' + Date.now())
                return
              }
              if (data.done) {
                finishStreaming(
                  data.full_response || '',
                  data.timestamps    || [],
                  data.sources       || [],
                  data.message_id    || Date.now().toString(),
                )
                return
              }
              if (data.token) appendToken(data.token)
            } catch { /* skip malformed */ }
          }
        }
      }
    } catch (err) {
      finishStreaming(
        `❌ Connection error: ${err.message}`,
        [], [], 'error-' + Date.now()
      )
    }
  }, [addUserMessage, startStreaming, appendToken, finishStreaming])

  return { streamQuestion }
}