#!/usr/bin/env node
// leaderboard.mjs — a terminal view of the token leaderboard, in the spirit of
// Claude Code's /usage. Zero dependencies. Reads the live Supabase `leaderboard`
// view and renders a ranked, auto-refreshing board. Interactive on a TTY (keys
// to switch window, refresh, quit); prints once and exits when piped.
//
//   node skills/token-leaderboard/leaderboard.mjs          # interactive
//   node skills/token-leaderboard/leaderboard.mjs --once   # print once and exit
//
// Config: SUPABASE_URL + SUPABASE_KEY from the environment, or, when run from
// the repo, SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY out of credentials/.env, so
// it just works with no setup.

import { readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const argv = process.argv.slice(2)
const ONCE = argv.includes('--once') || !process.stdout.isTTY
const COLOR = process.stdout.isTTY
// --refresh: push this machine's own latest usage to Supabase before showing
// the board, so the runner's numbers are current. --window sets the starting
// window (all | 30d | 7d).
const REFRESH = argv.includes('--refresh')
const WIN_ALIASES = { all: 0, alltime: 0, total: 0, '30d': 1, '30': 1, month: 1, '7d': 2, '7': 2, week: 2 }
function parseWindow() {
  const i = argv.indexOf('--window')
  const v = i !== -1 && argv[i + 1] ? argv[i + 1].toLowerCase() : ''
  return v in WIN_ALIASES ? WIN_ALIASES[v] : 0
}

// --- config ----------------------------------------------------------------
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../')
function fromEnvFile(name) {
  try {
    const txt = readFileSync(resolve(repoRoot, 'credentials/.env'), 'utf8')
    const m = txt.match(new RegExp('^' + name + '=(.*)$', 'm'))
    return m ? m[1].trim().replace(/^["']|["']$/g, '') : ''
  } catch { return '' }
}
const SUPABASE_URL = (process.env.SUPABASE_URL || fromEnvFile('SUPABASE_URL')).replace(/\/+$/, '')
const SUPABASE_KEY = process.env.SUPABASE_KEY || fromEnvFile('SUPABASE_PUBLISHABLE_KEY') || fromEnvFile('SUPABASE_KEY')
if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('leaderboard: set SUPABASE_URL and SUPABASE_KEY, or run from the repo with credentials/.env present')
  process.exit(1)
}

// --- state -----------------------------------------------------------------
const WINDOWS = [
  { key: 'total_tokens', label: 'All time' },
  { key: 'tokens_30d', label: '30 days' },
  { key: 'tokens_7d', label: '7 days' },
]
let windowIdx = parseWindow()
let rows = []
let lastError = ''
let lastUpdated = ''
let loading = false
let selfRefresh = ''

const headers = { apikey: SUPABASE_KEY, Authorization: 'Bearer ' + SUPABASE_KEY }

// Push this machine's own usage to Supabase (today and the last 7 days, so the
// 7d window stays current). Synchronous: it blocks until the upsert completes,
// which is the point — the board that renders next includes it.
function refreshOwnUsage() {
  const PERSON = (process.env.PERSON || process.env.LEADERBOARD_PERSON || fromEnvFile('LEADERBOARD_PERSON')).trim()
  if (!PERSON) { selfRefresh = 'self-refresh skipped (set LEADERBOARD_PERSON)'; return }
  const d = new Date(); d.setDate(d.getDate() - 7)
  const since = d.toLocaleDateString('en-CA').replace(/-/g, '')
  const collector = resolve(dirname(fileURLToPath(import.meta.url)), 'collect-usage.mjs')
  const r = spawnSync(process.execPath, [collector, '--since', since, '--no-snapshot'], {
    env: { ...process.env, PERSON, SUPABASE_URL, SUPABASE_KEY }, encoding: 'utf8',
  })
  if (r.status === 0) selfRefresh = 'refreshed ' + PERSON
  else if (/no daily rows/.test(r.stderr || '')) selfRefresh = 'no recent usage for ' + PERSON
  else selfRefresh = 'self-refresh failed'
}

async function load() {
  loading = true
  if (!ONCE) render()
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/leaderboard?select=*`, { headers })
    if (!res.ok) throw new Error(res.status + ' ' + (await res.text()).slice(0, 120))
    const data = await res.json()
    rows = Array.isArray(data) ? data : []
    lastError = ''
    lastUpdated = new Date().toLocaleTimeString()
  } catch (e) {
    lastError = e.message
  } finally {
    loading = false
    if (!ONCE) render()
  }
}

// --- formatting ------------------------------------------------------------
const fmt = (n) => {
  const v = Number(n) || 0
  if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return String(v)
}
const E = {
  reset: '\x1b[0m', bold: '\x1b[1m',
  gold: '\x1b[38;5;220m', blue: '\x1b[38;5;75m', gray: '\x1b[38;5;244m',
  dim: '\x1b[38;5;240m', ink: '\x1b[38;5;252m', red: '\x1b[38;5;203m',
}
const c = (code, s) => (COLOR ? code + s + E.reset : String(s))
const pad = (s, n) => { s = String(s); return s.length >= n ? s.slice(0, n) : s + ' '.repeat(n - s.length) }
const padL = (s, n) => { s = String(s); return s.length >= n ? s : ' '.repeat(n - s.length) + s }

function buildLines() {
  const W = Math.max(60, process.stdout.columns || 80)
  const win = WINDOWS[windowIdx]
  const lines = []
  const sel = WINDOWS.map((w, i) =>
    i === windowIdx ? c(E.bold + E.ink, '[' + w.label + ']') : c(E.dim, ' ' + w.label + ' ')
  ).join(' ')
  lines.push(' ' + c(E.bold, 'Token leaderboard') + '   ' + c(E.dim, 'Claude Max 20x, usage not a bill'))
  lines.push(' ' + sel)
  lines.push('')

  const sorted = [...rows].sort((a, b) => (Number(b[win.key]) || 0) - (Number(a[win.key]) || 0))
  const max = Math.max(1, ...sorted.map((r) => Number(r[win.key]) || 0))
  const rankW = 2, nameW = 12, valW = 8, metaW = 32
  const barW = Math.max(8, W - (1 + rankW + 1 + nameW + 1 + valW + 1 + metaW + 1))

  if (!sorted.length) {
    lines.push('  ' + c(E.gray, loading ? 'Loading...' : 'No usage yet. Run the collector to populate the board.'))
  }
  sorted.forEach((r, i) => {
    const v = Number(r[win.key]) || 0
    const lead = i === 0
    const fill = Math.round((v / max) * barW)
    const bar = c(lead ? E.blue : E.dim, '█'.repeat(fill)) + c(E.dim, '·'.repeat(barW - fill))
    const drove = (Number(r.input_tokens) || 0) + (Number(r.output_tokens) || 0)
    const meta = c(E.gray, pad(fmt(drove) + ' driven · ' + (r.days_active || 0) + 'd · ' + (r.last_active || ''), metaW))
    const rankCol = c(lead ? E.gold : E.dim, padL(i + 1, rankW))
    const nameCol = c(lead ? E.bold + E.gold : E.ink, pad(r.person, nameW))
    const valCol = c(lead ? E.bold + E.gold : E.ink, padL(fmt(v), valW))
    lines.push(' ' + rankCol + ' ' + nameCol + ' ' + bar + ' ' + valCol + ' ' + meta)
  })

  lines.push('')
  lines.push(' ' + c(E.dim, '[a] all  [3] 30d  [7] 7d   [r] refresh   [q] quit'))
  const count = rows.length === 1 ? '1 person' : rows.length + ' people'
  const status = lastError
    ? c(E.red, 'error: ' + lastError)
    : c(E.gray, count + ' · updated ' + (lastUpdated || '...') + (selfRefresh ? ' · ' + selfRefresh : '') + (loading ? ' · refreshing' : ''))
  lines.push(' ' + status)
  return lines
}

// --- render ----------------------------------------------------------------
function render() {
  process.stdout.write('\x1b[H\x1b[2J' + buildLines().join('\n'))
}

// --- lifecycle -------------------------------------------------------------
function quit(code = 0) {
  try {
    if (process.stdin.isTTY) process.stdin.setRawMode(false)
    process.stdout.write('\x1b[?25h\x1b[?1049l') // show cursor, leave alt screen
  } catch {}
  process.exit(code)
}

async function main() {
  if (ONCE) {
    if (REFRESH) refreshOwnUsage()
    await load()
    process.stdout.write(buildLines().join('\n') + '\n')
    return
  }
  process.stdout.write('\x1b[?1049h\x1b[?25l') // enter alt screen, hide cursor
  process.stdin.setRawMode(true)
  process.stdin.resume()
  process.stdin.on('data', (buf) => {
    const k = buf.toString()
    if (k === 'q' || k === '\u0003' || k === '\u001b') quit(0)
    else if (k === 'a' || k === '1') { windowIdx = 0; render() }
    else if (k === '3') { windowIdx = 1; render() }
    else if (k === '7') { windowIdx = 2; render() }
    else if (k === 'r') { if (REFRESH) refreshOwnUsage(); load() }
  })
  process.stdout.on('resize', render)
  process.on('SIGINT', () => quit(0))
  if (REFRESH) refreshOwnUsage()
  await load()
  setInterval(load, 30000)
}

main()
