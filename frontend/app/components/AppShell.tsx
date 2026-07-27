'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { LogOut, ShieldCheck } from 'lucide-react'
import { supabaseBrowser } from '@/lib/supabase/client'

const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/account', label: 'Account' },
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
    await supabaseBrowser?.auth.signOut()
    router.push('/')
    router.refresh()
  }

  return (
    <div className="min-h-screen bg-royal-blue-900">
      <header className="sticky top-0 z-50 border-b border-gold-500/20 bg-royal-blue-900/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/images/Logo.png" alt="LABEELE.AI" width={120} height={30} priority className="h-6 w-auto object-contain" />
          </Link>

          <nav className="hidden sm:flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm transition-colors ${
                  pathname === link.href ? 'text-gold-500 font-medium' : 'text-gray-300 hover:text-gold-500'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {isAdmin && (
              <Link
                href="/admin"
                className={`flex items-center gap-1.5 text-sm transition-colors ${
                  pathname.startsWith('/admin') ? 'text-gold-500 font-medium' : 'text-gray-300 hover:text-gold-500'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Admin
              </Link>
            )}
          </nav>

          <div className="flex items-center gap-4">
            {isAdmin && (
              <Link
                href="/admin"
                className="sm:hidden flex items-center gap-1.5 text-sm text-gold-500"
                aria-label="Admin"
              >
                <ShieldCheck className="w-4 h-4" />
              </Link>
            )}
            <button
              onClick={handleSignOut}
              className="flex items-center gap-2 text-sm text-gray-300 hover:text-gold-500 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 lg:px-8 py-10">{children}</main>
    </div>
  )
}
