import client from './client'

export const authAPI = {
  register: (data) => client.post('/auth/register', data),
  login:    (data) => client.post('/auth/login', data),
  logout:   (refreshToken) => client.post('/auth/logout', { refresh_token: refreshToken }),
  getMe:    () => client.get('/auth/me'),
  refresh:  (refreshToken) => client.post('/auth/refresh', { refresh_token: refreshToken }),
}