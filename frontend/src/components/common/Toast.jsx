import { Toaster } from 'react-hot-toast'

export default function Toast() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#0d1117',
          color: '#f0f6fc',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px',
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: '14px',
        },
        success: { iconTheme: { primary: '#00d9ff', secondary: '#0d1117' } },
        error:   { iconTheme: { primary: '#ef4444', secondary: '#0d1117' } },
      }}
    />
  )
}