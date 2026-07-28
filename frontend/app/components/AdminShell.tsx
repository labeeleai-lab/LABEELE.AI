'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { LogOut, ArrowLeft } from 'lucide-react'
import { supabaseBrowser } from '@/lib/supabase/client'

const NAV_LINKS = [
  { href: '/admin', label: 'Overview' },
  { href: '/admin/training', label: 'Training' },
  { href: '/admin/personas', label: 'Personas' },
  { href: '/admin/knowledge', label: 'Knowledge' },
  { href: '/admin/annotate', label: 'Annotate' },
  { href: '/admin/code', label: 'Code' },
  { href: '/admin/team', label: 'Team' },
]

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  const handleSignOut = async () => {
    await supabaseBrowser?.auth.signOut()
    router.push('/')
    router.refresh()
  }

  return (
    <div className="min-h-screen bg-royal-blue-900">
      <header className="sticky top-0 z-50 border-b border-gold-500/20 bg-royal-blue-900/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 shrink-0">
            <Image src="/images/Logo.png" alt="LABEELE.AI" width={110} height={28} className="h-5 w-auto object-contain" />
            <span className="text-xs font-semibold uppercase tracking-wide text-gold-500/80 border-l border-gold-500/20 pl-4">
              Admin
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-5 overflow-x-auto">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm whitespace-nowrap transition-colors ${
                  pathname === link.href ? 'text-gold-500 font-medium' : 'text-gray-300 hover:text-gold-500'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-4 shrink-0">
            <Link href="/dashboard" className="hidden sm:flex items-center gap-1.5 text-sm text-gray-400 hover:text-gold-500 transition-colors">
              <ArrowLeft className="w-4 h-4" /> Dashboard
            </Link>
            <button
              onClick={handleSignOut}
              className="flex items-center gap-2 text-sm text-gray-300 hover:text-gold-500 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>

        <nav className="md:hidden flex items-center gap-4 px-6 pb-3 overflow-x-auto">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm whitespace-nowrap transition-colors ${
                pathname === link.href ? 'text-gold-500 font-medium' : 'text-gray-300'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-6 lg:px-8 py-10">{children}</main>
    </div>
  )
}
