import LoadingSpinner from './LoadingSpinner'

export default function Button({
  children, onClick, disabled, loading,
  variant = 'primary', size = 'md', className = '', type = 'button',
}) {
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  const base = 'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200'
  const variants = {
    primary: 'btn-primary text-white',
    ghost:   'btn-ghost',
    danger:  'bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 cursor-pointer rounded-lg',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading && <LoadingSpinner size="sm" />}
      {children}
    </button>
  )
}