'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Menu, X } from 'lucide-react'

const NAV_LINKS = [
  { href: '/features', label: 'Features' },
  { href: '/pricing', label: 'Pricing' },
  { href: '/docs', label: 'Docs' },
  { href: '/about', label: 'About' },
]

export default function SiteHeader() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-gold-500/20 bg-royal-blue-900/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <Image src="/images/Logo.png" alt="LABEELE.AI" width={144} height={36} priority className="h-7 w-auto object-contain" />
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-gray-300 hover:text-gold-500 transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm font-medium text-gray-200 hover:text-gold-500 transition-colors px-3 py-2"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="text-sm font-semibold px-4 py-2 rounded-lg bg-gold-500 text-royal-blue-900 hover:bg-gold-400 transition-colors"
          >
            Start free trial
          </Link>
        </div>

        <button
          className="md:hidden text-gray-200 cursor-pointer"
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <nav className="md:hidden border-t border-gold-500/20 bg-royal-blue-900 px-6 py-4 flex flex-col gap-4">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-gray-200 hover:text-gold-500 transition-colors"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </Link>
          ))}
          <div className="border-t border-gold-500/10 pt-4 flex flex-col gap-3">
            <Link href="/login" className="text-gray-200 hover:text-gold-500" onClick={() => setMobileOpen(false)}>
              Log in
            </Link>
            <Link
              href="/signup"
              className="text-center font-semibold px-4 py-2 rounded-lg bg-gold-500 text-royal-blue-900"
              onClick={() => setMobileOpen(false)}
            >
              Start free trial
            </Link>
          </div>
        </nav>
      )}
    </header>
  )
}
