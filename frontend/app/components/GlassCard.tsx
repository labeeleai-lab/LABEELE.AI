// Standard LABEELE.AI card surface (see .surface in globals.css). Only
// cards that are actually clickable get a hover state - a hover effect on a
// static card falsely signals interactivity.
export default function GlassCard({
  children,
  className = '',
  interactive = false,
}: {
  children: React.ReactNode
  className?: string
  interactive?: boolean
}) {
  return <div className={`surface p-6 ${interactive ? 'surface-interactive' : ''} ${className}`}>{children}</div>
}
