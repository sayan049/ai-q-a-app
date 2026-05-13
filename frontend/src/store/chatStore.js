import { create } from 'zustand'

export const useChatStore = create((set) => ({
  messages: [],
  isStreaming: false,
  streamingContent: '',
  currentTimestamps: [],
  seekTo: null,

  setMessages: (messages) => set({ messages }),

  addUserMessage: (content) => set((state) => ({
    messages: [...state.messages, {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamps: [],
      sources: [],
      created_at: new Date().toISOString(),
    }],
  })),

  startStreaming: () => set({ isStreaming: true, streamingContent: '' }),

  appendToken: (token) => set((state) => ({
    streamingContent: state.streamingContent + token,
  })),

  finishStreaming: (fullResponse, timestamps, sources, messageId) => set((state) => ({
    messages: [...state.messages, {
      id: messageId || Date.now().toString(),
      role: 'assistant',
      content: fullResponse,
      timestamps: timestamps || [],
      sources: sources || [],
      created_at: new Date().toISOString(),
    }],
    isStreaming: false,
    streamingContent: '',
    currentTimestamps: timestamps || [],
  })),

  setSeekTo: (seconds) => set({ seekTo: seconds }),
  clearSeek: () => set({ seekTo: null }),

  clearMessages: () => set({
    messages: [],
    streamingContent: '',
    currentTimestamps: [],
    seekTo: null,
  }),
}))