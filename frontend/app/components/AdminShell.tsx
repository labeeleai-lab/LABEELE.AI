'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  ArrowLeft,
  BookOpen,
  ClipboardList,
  Code2,
  GraduationCap,
  LayoutGrid,
  LogOut,
  Mail,
  ShieldCheck,
  Users,
  Users2,
} from 'lucide-react'

// JIREH = LABEELE.AI's model-operations console. Same glass system as the
// DUKE workspace, but its own personality: persistent sidebar, grouped
// sections, a gold active rail, and a faint console grid behind content.
const NAV_GROUPS = [
  {
    label: 'Model',
    links: [
      { href: '/jireh', label: 'Overview', icon: LayoutGrid },
      { href: '/jireh/training', label: 'Training', icon: GraduationCap },
      { href: '/jireh/personas', label: 'Personas', icon: Users2 },
      { href: '/jireh/knowledge', label: 'Knowledge', icon: BookOpen },
      { href: '/jireh/annotate', label: 'Annotate', icon: ClipboardList },
    ],
  },
  {
    label: 'Workspace',
    links: [
      { href: '/jireh/code', label: 'Code', icon: Code2 },
      { href: '/jireh/messages', label: 'Messages', icon: Mail },
      { href: '/jireh/team', label: 'Team', icon: Users },
    ],
  },
]
const ALL_LINKS = NAV_GROUPS.flatMap((g) => g.links)

function JirehMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-gold-500/40 bg-gradient-to-br from-gold-500/25 to-gold-500/5 text-gold-400">
        <ShieldCheck className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-[0.18em] text-white">JIREH</p>
        {!compact && <p className="text-[11px] text-gray-500">Model operations</p>}
      </div>
    </div>
  )
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  const handleSignOut = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    router.push('/')
    router.refresh()
  }

  const isActive = (href: string) => pathname === href
  const current = ALL_LINKS.find((l) => isActive(l.href))

  return (
    <div className="min-h-screen lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] btn btn-primary btn-sm">
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/[0.07] bg-[#081030]/70 backdrop-blur-xl lg:flex">
        <div className="flex h-16 items-center border-b border-white/[0.06] px-5">
          <JirehMark />
        </div>

        <nav aria-label="JIREH" className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-600">{group.label}</p>
              <ul className="space-y-0.5">
                {group.links.map((link) => {
                  const Icon = link.icon
                  const active = isActive(link.href)
                  return (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        aria-current={active ? 'page' : undefined}
                        className={`relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                          active ? 'bg-white/[0.07] font-medium text-white' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-100'
                        }`}
                      >
                        {active && <span aria-hidden="true" className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-gold-500" />}
                        <Icon className={`h-4 w-4 ${active ? 'text-gold-400' : 'text-gray-500'}`} aria-hidden="true" />
                        {link.label}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="space-y-1 border-t border-white/[0.06] p-3">
          <Link href="/dashboard" className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-white/[0.04] hover:text-gray-100">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> DUKE workspace
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-gray-400 transition-colors hover:bg-white/[0.04] hover:text-gray-100 cursor-pointer"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" /> Sign out
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {/* Tablet/phone top bar + section tabs */}
        <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#081030]/80 backdrop-blur-xl lg:hidden">
          <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6">
            <JirehMark compact />
            <div className="flex items-center gap-1">
              <Link href="/dashboard" className="btn btn-ghost btn-sm" aria-label="Back to DUKE workspace">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">DUKE</span>
              </Link>
              <button type="button" onClick={handleSignOut} className="btn btn-ghost btn-sm" aria-label="Sign out">
                <LogOut className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
          <nav aria-label="JIREH" className="hide-scrollbar flex gap-1 overflow-x-auto px-3 pb-2 sm:px-5">
            {ALL_LINKS.map((link) => {
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
                  <Icon className={`h-3.5 w-3.5 ${active ? 'text-gold-400' : ''}`} aria-hidden="true" />
                  {link.label}
                </Link>
              )
            })}
          </nav>
        </header>

        <main id="main" className="jireh-canvas mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-10 lg:py-10">
          {current && current.href !== '/jireh' && (
            <nav aria-label="Breadcrumb" className="mb-4 hidden text-xs text-gray-500 lg:block">
              <Link href="/jireh" className="hover:text-gray-300">JIREH</Link>
              <span className="mx-1.5 text-gray-700">/</span>
              <span className="text-gray-400">{current.label}</span>
            </nav>
          )}
          {children}
        </main>
      </div>
    </div>
  )
}
