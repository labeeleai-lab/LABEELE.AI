'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { supabaseBrowser } from '@/lib/supabase/client'

const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/account', label: 'Account' },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
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
          </nav>

          <button
            onClick={handleSignOut}
            className="flex items-center gap-2 text-sm text-gray-300 hover:text-gold-500 transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 lg:px-8 py-10">{children}</main>
    </div>
  )
}
