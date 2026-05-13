import client from './client'

export const filesAPI = {
  upload: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  },
  list:       ()       => client.get('/files/list'),
  getFile:    (id)     => client.get(`/files/${id}`),
  deleteFile: (id)     => client.delete(`/files/${id}`),
}