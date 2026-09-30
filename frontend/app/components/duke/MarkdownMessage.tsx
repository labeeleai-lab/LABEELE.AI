'use client'

import { isValidElement, useState, type ReactNode } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy } from 'lucide-react'

// Renders model output as formatted text. react-markdown never renders raw
// HTML from the answer (no rehype-raw), so model output can't inject markup.

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children)
  return ''
}

export function CopyButton({ text, label = 'Copy', className = '' }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
          setCopied(true)
          setTimeout(() => setCopied(false), 1600)
        } catch {
          // Clipboard can be blocked (permissions/insecure context) - nothing to do
        }
      }}
      aria-label={copied ? 'Copied' : label}
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-gray-400 transition-colors hover:bg-white/5 hover:text-gold-400 cursor-pointer ${className}`}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
      <span>{copied ? 'Copied' : label}</span>
    </button>
  )
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const child = Array.isArray(children) ? children[0] : children
  const className = isValidElement<{ className?: string }>(child) ? child.props.className ?? '' : ''
  const language = /language-([\w-]+)/.exec(className)?.[1]
  const code = textOf(children).replace(/\n$/, '')
  return (
    <div className="glass-inset my-4 overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/5 px-3 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-wider text-gray-500">{language ?? 'code'}</span>
        <CopyButton text={code} label="Copy code" />
      </div>
      <pre className="overflow-x-auto px-4 py-3 text-[13px] leading-relaxed">
        <code className="font-mono text-gray-200">{code}</code>
      </pre>
    </div>
  )
}

const components: Components = {
  h1: ({ children }) => <h3 className="mt-6 mb-3 text-lg font-semibold text-white first:mt-0">{children}</h3>,
  h2: ({ children }) => <h3 className="mt-6 mb-3 text-base font-semibold text-white first:mt-0">{children}</h3>,
  h3: ({ children }) => <h4 className="mt-5 mb-2 text-[15px] font-semibold text-gray-100 first:mt-0">{children}</h4>,
  h4: ({ children }) => <h5 className="mt-4 mb-2 text-sm font-semibold uppercase tracking-wide text-gold-400 first:mt-0">{children}</h5>,
  p: ({ children }) => <p className="my-3 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-gold-500/70">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5 marker:text-gold-500/80 marker:font-medium">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  em: ({ children }) => <em className="text-gray-200">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-gold-400 underline decoration-gold-500/40 underline-offset-2 transition-colors hover:text-gold-300 hover:decoration-gold-400"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-2 border-gold-500/50 pl-4 text-gray-300 italic">{children}</blockquote>
  ),
  hr: () => <hr className="my-5 border-white/10" />,
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  code: ({ className, children }) =>
    className ? (
      <code className={className}>{children}</code>
    ) : (
      <code className="rounded-md border border-white/10 bg-white/[0.06] px-1.5 py-0.5 font-mono text-[0.85em] text-gold-200">
        {children}
      </code>
    ),
  table: ({ children }) => (
    <div className="glass-inset my-4 overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="border-b border-white/10 bg-white/[0.03]">{children}</thead>,
  th: ({ children }) => <th className="whitespace-nowrap px-3 py-2 font-semibold text-gray-100">{children}</th>,
  td: ({ children }) => <td className="border-t border-white/5 px-3 py-2 align-top text-gray-300">{children}</td>,
}

export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="min-w-0 break-words text-[15px] leading-7 text-gray-300">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
