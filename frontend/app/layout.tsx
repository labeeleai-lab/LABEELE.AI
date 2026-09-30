import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

// Self-hosted at build time by next/font (no runtime request to Google);
// exposed as --font-sans for globals.css and Tailwind's font-sans.
const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-sans' })

export const metadata: Metadata = {
  title: {
    default: 'LABEELE.AI - Specialist AI Agents',
    template: '%s | LABEELE.AI',
  },
  description: 'Seven focused AI specialists - security, ML, systems, backend, DevOps, vision, and emerging tech - behind one query interface.',
  keywords: ['AI', 'Machine Learning', 'Specialist Agents', 'Security', 'DevOps', 'Computer Vision'],
  authors: [{ name: 'LABEELE.AI' }],
  metadataBase: new URL('https://www.labeele.ai'),
  icons: {
    icon: '/images/Favicon.png',
    apple: '/images/Favicon.png',
  },
  openGraph: {
    title: 'LABEELE.AI - Specialist AI Agents',
    description: 'Seven focused AI specialists behind one query interface.',
    type: 'website',
    locale: 'en_US',
    siteName: 'LABEELE.AI',
  },
  twitter: {
    card: 'summary',
    title: 'LABEELE.AI - Specialist AI Agents',
    description: 'Seven focused AI specialists behind one query interface.',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0F1C4D',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  )
}