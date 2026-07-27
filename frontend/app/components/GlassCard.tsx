export default function GlassCard({ 
  children, 
  className = '' 
}: { 
  children: React.ReactNode
  className?: string 
}) {
  return (
    <div className={`bg-white/5 backdrop-blur-md border border-gold-500/25 rounded-xl p-6 transition-colors hover:border-gold-500/60 ${className}`}>
      {children}
    </div>
  )
}
