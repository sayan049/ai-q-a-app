// frontend/src/utils/markdownParser.js
// Lightweight markdown to plain text converter
// Used for generating previews/summaries without full rendering

export function markdownToText(markdown) {
  if (!markdown) return ''

  return markdown
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '[code block]')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove headers
    .replace(/^#{1,6}\s+/gm, '')
    // Remove bold/italic
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove links
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove images
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')
    // Remove blockquotes
    .replace(/^>\s+/gm, '')
    // Remove horizontal rules
    .replace(/^[-*_]{3,}$/gm, '')
    // Remove list markers
    .replace(/^[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function extractTimestamps(text) {
  // Extract [MM:SS] patterns from text
  const pattern = /\[(\d{1,2}):(\d{2})\]/g
  const timestamps = []
  let match

  while ((match = pattern.exec(text)) !== null) {
    const minutes = parseInt(match[1], 10)
    const seconds = parseInt(match[2], 10)
    timestamps.push({
      label: match[0],
      seconds: minutes * 60 + seconds,
      index: match.index,
    })
  }

  return timestamps
}

export function truncateText(text, maxLength = 150) {
  if (!text || text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}