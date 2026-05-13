import { create } from 'zustand'
import { authAPI } from '../api/auth'

export const useAuthStore = create((set, get) => ({
  user: null,
  isLoading: false,
  isAuthenticated: !!localStorage.getItem('access_token'),

  login: async (email, password) => {
    set({ isLoading: true })
    try {
      const res = await authAPI.login({ email, password })
      const { access_token, refresh_token } = res.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      const meRes = await authAPI.getMe()
      set({ user: meRes.data, isAuthenticated: true, isLoading: false })
      return { success: true }
    } catch (err) {
      set({ isLoading: false })
      return { success: false, error: err.response?.data?.detail || 'Login failed' }
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true })
    try {
      const res = await authAPI.register({ email, username, password })
      const { access_token, refresh_token } = res.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      const meRes = await authAPI.getMe()
      set({ user: meRes.data, isAuthenticated: true, isLoading: false })
      return { success: true }
    } catch (err) {
      set({ isLoading: false })
      return { success: false, error: err.response?.data?.detail || 'Registration failed' }
    }
  },

  logout: async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) await authAPI.logout(refreshToken)
    } catch {}
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  fetchMe: async () => {
    try {
      const res = await authAPI.getMe()
      set({ user: res.data, isAuthenticated: true })
    } catch {
      get().logout()
    }
  },
}))