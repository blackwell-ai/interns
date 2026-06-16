#!/usr/bin/env node
// collect-usage.mjs — push one person's daily Claude Code token usage to Supabase.
//
// Runs per person (cron or a harness skill run). It shells out to ccusage,
// which reads the local Claude Code JSONL logs, then upserts one row per day
// into daily_usage and re-renders the pooled brain/metrics/LEADERBOARD.md.
//
//   PERSON="Armaan" SUPABASE_URL="https://x.supabase.co" SUPABASE_KEY="<anon>" \
//     node collect-usage.mjs --since 20260101
//
// Secrets are read from the environment at runtime, never from the repo.
// SUPABASE_KEY is the anon key (a public client identifier; RLS guards the
// table). Flags the collector owns: --dry-run, --no-snapshot, --snapshot
// <path>. Everything else is forwarded to ccusage (e.g. --since, --until).
//
// Zero dependencies on purpose: this script is ephemeral and must run with a
// bare `node` on any teammate's machine. The durable assets are the migration,
// the SKILL.md, and the committed snapshot.

import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { mkdirSync, writeFileSync } from 'node:fs'

const OWN_FLAGS = new Set(['--dry-run', '--no-snapshot'])
const argv = process.argv.slice(2)
const dryRun = argv.includes('--dry-run')
const noSnapshot = argv.includes('--no-snapshot')

// --snapshot <path> override, default <repo>/brain/metrics/LEADERBOARD.md.
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../')
let snapshotPath = resolve(repoRoot, 'brain/metrics/LEADERBOARD.md')
const snapIdx = argv.indexOf('--snapshot')
if (snapIdx !== -1 && argv[snapIdx + 1]) snapshotPath = resolve(argv[snapIdx + 1])

// Pass through to ccusage everything that is not one of our flags.
const ccusageArgs = []
for (let i = 0; i < argv.length; i++) {
  const a = argv[i]
  if (OWN_FLAGS.has(a)) continue
  if (a === '--snapshot') { i++; continue }
  ccusageArgs.push(a)
}

const die = (msg) => { console.error(`collect-usage: ${msg}`); process.exit(1) }

const PERSON = (process.env.PERSON || '').trim()
const SUPABASE_URL = (process.env.SUPABASE_URL || '').replace(/\/+$/, '')
const SUPABASE_KEY = (process.env.SUPABASE_KEY || '').trim()

if (!PERSON) die('set PERSON to your display name, e.g. PERSON="Armaan"')
if (!dryRun && (!SUPABASE_URL || !SUPABASE_KEY)) {
  die('set SUPABASE_URL and SUPABASE_KEY (anon key), or pass --dry-run')
}

// --- run ccusage -----------------------------------------------------------

function runCcusage() {
  const args = ['-y', 'ccusage', 'claude', 'daily', '--json', ...ccusageArgs]
  const res = spawnSync('npx', args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
  if (res.error) die(`could not run npx ccusage: ${res.error.message}`)
  if (res.status !== 0) die(`ccusage exited ${res.status}: ${(res.stderr || '').trim()}`)
  // ccusage --json prints pure JSON to stdout; be defensive about any noise.
  const out = res.stdout || ''
  const start = out.indexOf('{')
  const end = out.lastIndexOf('}')
  if (start === -1 || end === -1) die('ccusage produced no JSON; check that Claude Code logs exist')
  try {
    return JSON.parse(out.slice(start, end + 1))
  } catch (e) {
    die(`could not parse ccusage JSON: ${e.message}`)
  }
}

function ccusageVersion() {
  try {
    const r = spawnSync('npx', ['-y', 'ccusage', '--version'], { encoding: 'utf8' })
    return (r.stdout || '').trim().split(/\s+/).pop() || ''
  } catch { return '' }
}

// Tolerant field reader: the spec calls out that ccusage renames token fields
// across releases. Try the known names in order; a miss returns 0.
const pick = (obj, ...keys) => {
  for (const k of keys) {
    const v = obj?.[k]
    if (v !== undefined && v !== null) return v
  }
  return undefined
}
const int = (v) => Math.round(Number(v) || 0)
const flt = (v) => Number(v) || 0

function toRow(d, version) {
  const input = int(pick(d, 'inputTokens', 'input_tokens'))
  const output = int(pick(d, 'outputTokens', 'output_tokens'))
  const cacheCreate = int(pick(d, 'cacheCreationTokens', 'cache_creation_tokens', 'cacheCreationInputTokens'))
  const cacheRead = int(pick(d, 'cacheReadTokens', 'cache_read_tokens', 'cacheReadInputTokens'))
  let total = int(pick(d, 'totalTokens', 'total_tokens'))
  if (!total) total = input + output + cacheCreate + cacheRead
  const models = pick(d, 'modelsUsed', 'models_used')
    || (Array.isArray(d?.modelBreakdowns) ? d.modelBreakdowns.map((m) => m.modelName).filter(Boolean) : [])
  return {
    person: PERSON,
    day: pick(d, 'date', 'day'),
    input_tokens: input,
    output_tokens: output,
    cache_creation_tokens: cacheCreate,
    cache_read_tokens: cacheRead,
    total_tokens: total,
    total_cost: flt(pick(d, 'totalCost', 'cost', 'total_cost')),
    models,
    ccusage_version: version,
  }
}

const parsed = runCcusage()
const daily = parsed?.daily || parsed?.data || []
if (!Array.isArray(daily) || daily.length === 0) {
  die('ccusage returned no daily rows for the requested range')
}
const version = ccusageVersion()
const rows = daily.map((d) => toRow(d, version)).filter((r) => r.day)

// Loud guard for the documented field-drift failure mode.
const allZero = rows.every((r) => r.total_tokens === 0)
if (allZero) {
  console.error('collect-usage: WARNING every row has total_tokens=0.')
  console.error('  ccusage field names likely changed. Update the pick() mappings')
  console.error('  in toRow(). One sample row from ccusage:')
  console.error('  ' + JSON.stringify(daily[daily.length - 1]))
}

const span = `${rows[0].day}..${rows[rows.length - 1].day}`
console.log(`collect-usage: ${PERSON} — ${rows.length} day(s) ${span} (ccusage ${version || '?'})`)

if (dryRun) {
  console.log(JSON.stringify(rows, null, 2))
  console.log('collect-usage: --dry-run, nothing written')
  process.exit(0)
}

// --- upsert into Supabase --------------------------------------------------

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  'Content-Type': 'application/json',
}

async function upsert(batch) {
  const url = `${SUPABASE_URL}/rest/v1/daily_usage?on_conflict=person,day`
  const res = await fetch(url, {
    method: 'POST',
    headers: { ...headers, Prefer: 'resolution=merge-duplicates,return=minimal' },
    body: JSON.stringify(batch),
  })
  if (!res.ok) die(`upsert failed ${res.status}: ${(await res.text()).trim()}`)
}

async function fetchLeaderboard() {
  const url = `${SUPABASE_URL}/rest/v1/leaderboard?select=*&order=total_tokens.desc`
  const res = await fetch(url, { headers })
  if (!res.ok) die(`could not read leaderboard view ${res.status}: ${(await res.text()).trim()}`)
  return res.json()
}

// --- snapshot --------------------------------------------------------------

const fmtTokens = (n) => {
  const v = Number(n) || 0
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K'
  return String(v)
}

function renderSnapshot(board) {
  // Local date (en-CA gives YYYY-MM-DD), matching ccusage's local day values
  // and the repo's local-date convention, not UTC.
  const today = new Date().toLocaleDateString('en-CA')
  const lines = []
  lines.push('# Token leaderboard')
  lines.push('')
  lines.push(`Snapshot regenerated ${today}. Ranked by lifetime total tokens put`)
  lines.push('through Claude Code, pooled from each person\'s local logs via ccusage.')
  lines.push('Flat Max 20x subscription, so this is usage and relative intensity, not a')
  lines.push('bill. The live interactive board is token-leaderboard.html; this file is')
  lines.push('the durable record. Generated by skills/token-leaderboard/collect-usage.mjs.')
  lines.push('')
  lines.push('| # | Person | Total tokens | Last 7d | Days | In | Out | Cache read | Last active |')
  lines.push('|---|--------|-------------:|--------:|-----:|---:|----:|-----------:|-------------|')
  board.forEach((r, i) => {
    lines.push(
      `| ${i + 1} | ${r.person} | ${fmtTokens(r.total_tokens)} | ${fmtTokens(r.tokens_7d)} | ` +
      `${r.days_active} | ${fmtTokens(r.input_tokens)} | ${fmtTokens(r.output_tokens)} | ` +
      `${fmtTokens(r.cache_read_tokens)} | ${r.last_active || ''} |`
    )
  })
  lines.push('')
  lines.push('Total tokens is cache-read heavy by nature (context replayed each turn).')
  lines.push('In and Out are the tokens a person actually drove. One member missing means')
  lines.push('that member has not run the collector.')
  lines.push('')
  return lines.join('\n')
}

await upsert(rows)
console.log(`collect-usage: upserted ${rows.length} row(s) for ${PERSON}`)

if (!noSnapshot) {
  const board = await fetchLeaderboard()
  mkdirSync(dirname(snapshotPath), { recursive: true })
  writeFileSync(snapshotPath, renderSnapshot(board))
  console.log(`collect-usage: wrote ${snapshotPath} (${board.length} people)`)
}
