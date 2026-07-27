import Link from 'next/link'
import Image from 'next/image'

export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-royal-blue-900 flex flex-col">
      <div className="px-6 lg:px-8 py-6">
        <Link href="/" className="inline-flex items-center">
          <Image src="/images/Logo.png" alt="LABEELE.AI" width={144} height={36} priority className="h-7 w-auto object-contain" />
        </Link>
      </div>

      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">{title}</h1>
            {subtitle && <p className="text-gray-400 text-sm">{subtitle}</p>}
          </div>

          <div className="bg-white/5 backdrop-blur-md border border-gold-500/20 rounded-xl p-8">
            {children}
          </div>

          {footer && <div className="text-center mt-6 text-sm text-gray-400">{footer}</div>}
        </div>
      </div>
    </div>
  )
}
