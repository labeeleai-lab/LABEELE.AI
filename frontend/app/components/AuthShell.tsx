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
    <div className="flex min-h-screen flex-col">
      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center" aria-label="LABEELE.AI home">
          <Image src="/images/Logo.png" alt="LABEELE.AI" width={144} height={36} priority className="h-7 w-auto object-contain" />
        </Link>
      </div>

      <main id="main" className="flex flex-1 items-center justify-center px-4 pb-16 sm:px-6">
        <div className="w-full max-w-md animate-message-in">
          <div className="mb-8 text-center">
            <h1 className="mb-2 text-2xl font-semibold tracking-tight text-white">{title}</h1>
            {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
          </div>

          <div className="surface-panel p-6 sm:p-8">{children}</div>

          {footer && <div className="mt-6 text-center text-sm text-gray-400">{footer}</div>}
        </div>
      </main>
    </div>
  )
}
