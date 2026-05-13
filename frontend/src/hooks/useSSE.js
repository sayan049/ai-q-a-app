import { useCallback } from 'react'
import { useChatStore } from '../store/chatStore'

export function useSSE() {
  const { addUserMessage, startStreaming, appendToken, finishStreaming } = useChatStore()

  const streamQuestion = useCallback(async (query, fileId) => {
    addUserMessage(query)
    startStreaming()

    const token = localStorage.getItem('access_token')
    const url = `/api/v1/chat/ask?query=${encodeURIComponent(query)}&file_id=${encodeURIComponent(fileId)}`

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

      const reader = response.body.getReader()
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
                  data.timestamps || [],
                  data.sources || [],
                  data.message_id || Date.now().toString(),
                )
                return
              }
              if (data.token) {
                appendToken(data.token)
              }
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