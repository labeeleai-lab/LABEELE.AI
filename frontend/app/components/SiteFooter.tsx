import Link from 'next/link'
import Image from 'next/image'

const COLUMNS: { title: string; links: { href: string; label: string }[] }[] = [
  {
    title: 'Product',
    links: [
      { href: '/features', label: 'Features' },
      { href: '/pricing', label: 'Pricing' },
      { href: '/docs', label: 'Documentation' },
    ],
  },
  {
    title: 'Company',
    links: [
      { href: '/about', label: 'About' },
      { href: '/blog', label: 'Blog' },
      { href: '/careers', label: 'Careers' },
      { href: '/contact', label: 'Contact' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { href: '/privacy', label: 'Privacy Policy' },
      { href: '/terms', label: 'Terms of Service' },
      { href: '/security', label: 'Security' },
      { href: '/compliance', label: 'Compliance' },
    ],
  },
]

export default function SiteFooter() {
  return (
    <footer className="border-t border-white/[0.07] bg-[#081030]/60 px-4 py-16 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          <div>
            <Image src="/images/Logo.png" alt="LABEELE.AI" width={120} height={30} className="h-6 w-auto object-contain mb-4" />
            <p className="text-gray-400 text-sm leading-relaxed max-w-xs">
              A specialist AI agent platform for security, ML, infrastructure, backend, DevOps,
              vision, and emerging tech tasks.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h2 className="eyebrow mb-4">{col.title}</h2>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className="text-sm text-gray-400 transition-colors hover:text-white">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-white/[0.07] pt-8">
          <p className="text-center text-gray-500 text-sm">
            © {new Date().getFullYear()} LABEELE.AI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
