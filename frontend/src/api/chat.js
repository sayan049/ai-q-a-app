import client from './client'

export const chatAPI = {
  getHistory:   (fileId) => client.get(`/chat/history/${fileId}`),
  clearHistory: (fileId) => client.delete(`/chat/history/${fileId}`),
  getSummary:   (fileId) => client.get(`/summary/${fileId}`),
}