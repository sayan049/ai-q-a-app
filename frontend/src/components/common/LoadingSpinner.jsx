export default function LoadingSpinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`${sizes[size]} ${className} flex items-center justify-center`}>
      <div className="w-full h-full rounded-full border-2 border-transparent
        border-t-[#00d9ff] animate-spin" />
    </div>
  )
}