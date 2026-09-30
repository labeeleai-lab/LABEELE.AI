'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, LogOut, ShieldCheck, UserCircle2 } from 'lucide-react'

const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/account', label: 'Account', icon: UserCircle2 },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    fetch('/api/admin/status')
      .then((res) => res.json())
      .then((body) => setIsAdmin(Boolean(body.isAdmin)))
      .catch(() => setIsAdmin(false))
  }, [])

  const handleSignOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/')
    router.refresh()
  }

  const links = isAdmin ? [...NAV_LINKS, { href: '/jireh', label: 'JIREH Mode', icon: ShieldCheck }] : NAV_LINKS
  const isActive = (href: string) => (href === '/jireh' ? pathname.startsWith('/jireh') : pathname === href)

  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] btn btn-primary btn-sm">
        Skip to content
      </a>
      <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#0b1535]/75 backdrop-blur-xl backdrop-saturate-150">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex shrink-0 items-center" aria-label="LABEELE.AI home">
            <Image src="/images/Logo.png" alt="LABEELE.AI" width={120} height={30} priority className="h-6 w-auto object-contain" />
          </Link>

          <nav aria-label="Primary" className="hidden items-center gap-1 sm:flex">
            {links.map((link) => {
              const Icon = link.icon
              const active = isActive(link.href)
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    active ? 'bg-white/[0.07] font-medium text-white' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-100'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${active ? 'text-gold-500' : ''}`} aria-hidden="true" />
                  {link.label}
                </Link>
              )
            })}
          </nav>

          <button type="button" onClick={handleSignOut} className="btn btn-ghost btn-sm ml-auto">
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>

        {/* Phones: the primary nav as a compact tab row (previously hidden entirely) */}
        <nav aria-label="Primary" className="hide-scrollbar flex gap-1 overflow-x-auto px-4 pb-2 sm:hidden">
          {links.map((link) => {
            const Icon = link.icon
            const active = isActive(link.href)
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? 'page' : undefined}
                className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] ${
                  active ? 'bg-white/[0.08] font-medium text-white' : 'text-gray-400'
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${active ? 'text-gold-500' : ''}`} aria-hidden="true" />
                {link.label}
              </Link>
            )
          })}
        </nav>
      </header>

      <main id="main" className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        {children}
      </main>
    </div>
  )
}
