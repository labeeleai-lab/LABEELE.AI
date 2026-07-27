import type { TrainingExample } from './duke-api'

// Client-side parser for admin-uploaded training data files. Supports JSON,
// JSONL, and CSV, each with a few common key aliases so the admin doesn't
// have to reformat existing data to one exact schema. Deliberately does NOT
// try to guess structure out of free-form .txt/.md files - unreliable
// guessing would silently produce garbage training examples, so unsupported
// files are reported as skipped instead.

export interface ParsedFileResult {
  fileName: string
  examples: TrainingExample[]
  error?: string
}

const INSTRUCTION_KEYS = ['instruction', 'prompt', 'question', 'input']
const OUTPUT_KEYS = ['output', 'response', 'answer', 'completion']

function pickField(obj: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = obj[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return undefined
}

function recordToExample(obj: Record<string, unknown>): TrainingExample | null {
  const instruction = pickField(obj, INSTRUCTION_KEYS)
  const output = pickField(obj, OUTPUT_KEYS)
  if (!instruction || !output) return null
  const personaId = typeof obj.persona_id === 'string' ? obj.persona_id : undefined
  return { instruction, output, persona_id: personaId }
}

function parseJson(text: string): TrainingExample[] {
  const data = JSON.parse(text)
  const rows = Array.isArray(data) ? data : [data]
  const examples: TrainingExample[] = []
  for (const row of rows) {
    if (row && typeof row === 'object') {
      const example = recordToExample(row as Record<string, unknown>)
      if (example) examples.push(example)
    }
  }
  return examples
}

function parseJsonl(text: string): TrainingExample[] {
  const examples: TrainingExample[] = []
  const lines = text.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    const row = JSON.parse(trimmed)
    if (row && typeof row === 'object') {
      const example = recordToExample(row as Record<string, unknown>)
      if (example) examples.push(example)
    }
  }
  return examples
}

// Minimal RFC4180-ish CSV line splitter: handles quoted fields, escaped
// quotes ("") inside quotes, and commas inside quotes. Good enough for
// simple two/three-column exports; not a full CSV spec implementation.
function splitCsvLine(line: string): string[] {
  const fields: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          current += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        current += char
      }
    } else if (char === '"') {
      inQuotes = true
    } else if (char === ',') {
      fields.push(current)
      current = ''
    } else {
      current += char
    }
  }
  fields.push(current)
  return fields.map((f) => f.trim())
}

function parseCsv(text: string): TrainingExample[] {
  const lines = text.split('\n').filter((l) => l.trim().length > 0)
  if (lines.length === 0) return []

  const header = splitCsvLine(lines[0]).map((h) => h.toLowerCase())
  const instructionIdx = header.findIndex((h) => INSTRUCTION_KEYS.includes(h))
  const outputIdx = header.findIndex((h) => OUTPUT_KEYS.includes(h))
  const personaIdx = header.findIndex((h) => h === 'persona_id')

  const hasHeader = instructionIdx !== -1 && outputIdx !== -1
  const iIdx = hasHeader ? instructionIdx : 0
  const oIdx = hasHeader ? outputIdx : 1
  const pIdx = hasHeader ? personaIdx : -1
  const dataLines = hasHeader ? lines.slice(1) : lines

  const examples: TrainingExample[] = []
  for (const line of dataLines) {
    const fields = splitCsvLine(line)
    const instruction = fields[iIdx]?.trim()
    const output = fields[oIdx]?.trim()
    if (!instruction || !output) continue
    const persona_id = pIdx !== -1 ? fields[pIdx]?.trim() || undefined : undefined
    examples.push({ instruction, output, persona_id })
  }
  return examples
}

export async function parseTrainingFile(file: File): Promise<ParsedFileResult> {
  const name = file.name
  const ext = name.split('.').pop()?.toLowerCase()
  const text = await file.text()

  try {
    if (ext === 'json') return { fileName: name, examples: parseJson(text) }
    if (ext === 'jsonl' || ext === 'ndjson') return { fileName: name, examples: parseJsonl(text) }
    if (ext === 'csv') return { fileName: name, examples: parseCsv(text) }
    return { fileName: name, examples: [], error: `Unsupported file type ".${ext ?? ''}" - use .json, .jsonl, or .csv.` }
  } catch (err) {
    return { fileName: name, examples: [], error: err instanceof Error ? `Could not parse: ${err.message}` : 'Could not parse file.' }
  }
}

export async function parseTrainingFiles(files: FileList | File[]): Promise<ParsedFileResult[]> {
  const list = Array.from(files)
  return Promise.all(list.map(parseTrainingFile))
}
