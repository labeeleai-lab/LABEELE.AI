'use client'

import { useEffect, useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import { Folder, FolderOpen, FileCode, Loader2, Save, CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

interface TreeEntry {
  path: string
  type: 'blob' | 'tree'
  sha: string
  size?: number
}

interface TreeNode {
  name: string
  path: string
  type: 'blob' | 'tree'
  children?: TreeNode[]
}

function buildTree(entries: TreeEntry[]): TreeNode[] {
  const root: TreeNode[] = []
  const map = new Map<string, TreeNode>()
  const sorted = [...entries].sort((a, b) => a.path.localeCompare(b.path))

  for (const entry of sorted) {
    const parts = entry.path.split('/')
    const name = parts[parts.length - 1]
    const node: TreeNode = { name, path: entry.path, type: entry.type, children: entry.type === 'tree' ? [] : undefined }
    map.set(entry.path, node)
    const parentPath = parts.slice(0, -1).join('/')
    if (parentPath && map.has(parentPath)) {
      map.get(parentPath)!.children!.push(node)
    } else {
      root.push(node)
    }
  }
  return root
}

const LANGUAGE_BY_EXT: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  py: 'python',
  json: 'json',
  css: 'css',
  md: 'markdown',
  yml: 'yaml',
  yaml: 'yaml',
  html: 'html',
  sh: 'shell',
}

function languageForPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  return LANGUAGE_BY_EXT[ext] ?? 'plaintext'
}

function TreeView({
  nodes,
  expanded,
  onToggle,
  selectedPath,
  onSelectFile,
  depth = 0,
}: {
  nodes: TreeNode[]
  expanded: Set<string>
  onToggle: (path: string) => void
  selectedPath: string | null
  onSelectFile: (path: string) => void
  depth?: number
}) {
  return (
    <ul>
      {nodes.map((node) => (
        <li key={node.path}>
          {node.type === 'tree' ? (
            <>
              <button
                onClick={() => onToggle(node.path)}
                className="w-full flex items-center gap-1.5 py-1 text-sm text-gray-300 hover:text-gold-500 transition-colors cursor-pointer"
                style={{ paddingLeft: `${depth * 14}px` }}
              >
                {expanded.has(node.path) ? <FolderOpen className="w-3.5 h-3.5 shrink-0" /> : <Folder className="w-3.5 h-3.5 shrink-0" />}
                <span className="truncate">{node.name}</span>
              </button>
              {expanded.has(node.path) && node.children && (
                <TreeView nodes={node.children} expanded={expanded} onToggle={onToggle} selectedPath={selectedPath} onSelectFile={onSelectFile} depth={depth + 1} />
              )}
            </>
          ) : (
            <button
              onClick={() => onSelectFile(node.path)}
              className={`w-full flex items-center gap-1.5 py-1 text-sm transition-colors cursor-pointer ${
                selectedPath === node.path ? 'text-gold-500 font-medium' : 'text-gray-400 hover:text-gold-500'
              }`}
              style={{ paddingLeft: `${depth * 14 + 20}px` }}
            >
              <FileCode className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{node.name}</span>
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}

export default function AdminCodePage() {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  const [treeError, setTreeError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [fileSha, setFileSha] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [originalContent, setOriginalContent] = useState<string>('')
  const [fileLoading, setFileLoading] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)

  const [commitMessage, setCommitMessage] = useState('')
  const [committing, setCommitting] = useState(false)
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    fetch('/api/admin/github/tree')
      .then((res) => res.json())
      .then((body) => {
        if (body.error) throw new Error(body.error)
        setEntries(body.tree)
        setExpanded(new Set(body.tree.filter((e: TreeEntry) => e.type === 'tree' && !e.path.includes('/')).map((e: TreeEntry) => e.path)))
      })
      .catch((err) => setTreeError(err instanceof Error ? err.message : 'Failed to load repo tree.'))
  }, [])

  const tree = useMemo(() => (entries ? buildTree(entries) : []), [entries])

  const toggleFolder = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const selectFile = async (path: string) => {
    setSelectedPath(path)
    setFileLoading(true)
    setFileError(null)
    setNotice(null)
    try {
      const res = await fetch(`/api/admin/github/file?path=${encodeURIComponent(path)}`)
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Failed to load file')
      setContent(body.content)
      setOriginalContent(body.content)
      setFileSha(body.sha)
      setCommitMessage('')
    } catch (err) {
      setFileError(err instanceof Error ? err.message : 'Failed to load file.')
    } finally {
      setFileLoading(false)
    }
  }

  const handleCommit = async () => {
    if (!selectedPath) return
    setCommitting(true)
    setNotice(null)
    try {
      const res = await fetch('/api/admin/github/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedPath,
          content,
          sha: fileSha,
          message: commitMessage || `Edit ${selectedPath} via admin IDE`,
        }),
      })
      const body = await res.json()
      if (!res.ok) throw new Error(body.error || 'Commit failed')
      setFileSha(body.contentSha)
      setOriginalContent(content)
      setCommitMessage('')
      setNotice({ type: 'success', message: 'Committed to GitHub.' })
    } catch (err) {
      setNotice({ type: 'error', message: err instanceof Error ? err.message : 'Commit failed.' })
    } finally {
      setCommitting(false)
    }
  }

  const dirty = content !== originalContent
  const isBackendFile = selectedPath?.startsWith('backend/')

  return (
    <AdminShell>
      <h1 className="text-3xl font-bold text-white mb-1">Code</h1>
      <p className="text-gray-400 mb-6">
        Browse, edit, and commit directly to <code className="text-xs">labeeleai-lab/LABEELE.AI</code>.
      </p>

      <div className="mb-6 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-200 text-sm flex items-start gap-2.5">
        <AlertOctagon className="w-4 h-4 shrink-0 mt-0.5" />
        <span>
          Committing here updates GitHub only. There&apos;s no auto-deploy to the frontend (Vercel picks up
          pushes automatically) <strong>or</strong> the live Duke backend (Hugging Face Space) - backend
          changes need a manual sync/redeploy to take effect.
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <GlassCard className="lg:col-span-1 max-h-[42rem] overflow-y-auto">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">Repository</h2>
          {treeError ? (
            <p className="text-red-400 text-sm">{treeError}</p>
          ) : !entries ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : (
            <TreeView nodes={tree} expanded={expanded} onToggle={toggleFolder} selectedPath={selectedPath} onSelectFile={selectFile} />
          )}
        </GlassCard>

        <div className="lg:col-span-3 space-y-4">
          {!selectedPath ? (
            <GlassCard>
              <p className="text-gray-400 text-sm">Select a file to view and edit it.</p>
            </GlassCard>
          ) : (
            <>
              {isBackendFile && (
                <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 text-amber-200/90 text-xs">
                  This is a backend file - see the deploy note above.
                </div>
              )}

              <GlassCard className="p-0 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-gold-500/10">
                  <code className="text-sm text-white">{selectedPath}</code>
                  {dirty && <span className="text-xs text-gold-500">Unsaved changes</span>}
                </div>
                {fileLoading ? (
                  <div className="flex items-center justify-center h-96 text-gray-400 text-sm gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" /> Loading file&hellip;
                  </div>
                ) : fileError ? (
                  <div className="p-6 text-red-400 text-sm">{fileError}</div>
                ) : (
                  <MonacoEditor
                    height="480px"
                    language={languageForPath(selectedPath)}
                    theme="vs-dark"
                    value={content}
                    onChange={(value) => setContent(value ?? '')}
                    options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
                  />
                )}
              </GlassCard>

              {notice && (
                <div
                  role="alert"
                  className={`p-3 rounded-lg border text-sm flex items-start gap-2 ${
                    notice.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
                  }`}
                >
                  {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                  {notice.message}
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  value={commitMessage}
                  onChange={(e) => setCommitMessage(e.target.value)}
                  placeholder={`Edit ${selectedPath} via admin IDE`}
                  className="flex-1 px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors text-sm"
                />
                <button
                  onClick={handleCommit}
                  disabled={!dirty || committing}
                  className="flex items-center justify-center gap-2 px-6 py-2.5 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {committing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Commit
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </AdminShell>
  )
}
