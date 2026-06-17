#!/usr/bin/env node
/*
 * granola-export: pull Granola meeting notes into context/samarjit-granola/.
 *
 * Granola encrypts its local store. This reads the macOS login keychain
 * (Electron safeStorage) to unwrap Granola's data-encryption key, decrypts the
 * current API token from the local account file, then calls Granola's own API
 * for the canonical document, AI summary panel, and verbatim transcript. It
 * writes one markdown file per meeting in the repo's existing note format.
 *
 * Usage:
 *   node export.js                 # export every note not already in the out dir
 *   node export.js --list          # list documents + which are new, write nothing
 *   node export.js --all           # re-export every document (overwrites)
 *   node export.js --out <dir>     # output dir (default: context/samarjit-granola)
 *   node export.js --id <doc-id>   # export one specific document
 *
 * Running this triggers ONE macOS Keychain prompt the first time ("security
 * wants to use the Granola Safe Storage key"). Click Allow or Always Allow.
 * Secrets (keychain password, data key, API token) live only in memory and are
 * never printed or written to disk.
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ---------------------------------------------------------------- config ----

// People whose name Granola enriches wrong or not at all. Grounded in the repo
// (brain/people, the outreach send config), not invented. Extend as needed.
const NAME_MAP = {
  'samarjit.deshmukh.29@dartmouth.edu': 'Samarjit Deshmukh',
  'armaan.priyadarshan.29@dartmouth.edu': 'Armaan Priyadarshan',
  'shamitd@stanford.edu': "Shamit D'Souza",
  'ethanpzhou@berkeley.edu': 'Ethan Zhou',
};

const GRANOLA_DIR = path.join(
  process.env.HOME,
  'Library/Application Support/Granola'
);
const API = 'https://api.granola.ai';
const KEYCHAIN_SERVICE = 'Granola Safe Storage';

// ------------------------------------------------------------- arg parse ----

const argv = process.argv.slice(2);
function flag(name) { return argv.includes(name); }
function opt(name, dflt) {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
}
const MODE_LIST = flag('--list');
const MODE_ALL = flag('--all');
const ONLY_ID = opt('--id', null);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const OUT_DIR = path.resolve(
  opt('--out', path.join(REPO_ROOT, 'context', 'samarjit-granola'))
);

// ------------------------------------------------------------ decryption ----

function keychainSecret() {
  try {
    return execSync(
      `security find-generic-password -wgs ${JSON.stringify(KEYCHAIN_SERVICE)}`,
      { stdio: ['ignore', 'pipe', 'ignore'] }
    ).toString().trim();
  } catch (e) {
    throw new Error(
      `Could not read the "${KEYCHAIN_SERVICE}" keychain item. Is Granola ` +
      `installed and have you signed in? (If a prompt appeared, click Allow.)`
    );
  }
}

// Electron safeStorage on macOS: 'v10' prefix, then AES-128-CBC with a key
// derived as PBKDF2(keychainSecret, 'saltysalt', 1003, 16, sha1) and a 16-byte
// all-spaces IV.
function safeStorageDecrypt(buf, aesKey) {
  const d = crypto.createDecipheriv('aes-128-cbc', aesKey, Buffer.alloc(16, 0x20));
  return Buffer.concat([d.update(buf.subarray(3)), d.final()]);
}

// Files Granola encrypts with its own data key are AES-256-GCM framed as
// nonce(12) || ciphertext || tag(16).
function dekDecrypt(buf, dek) {
  const nonce = buf.subarray(0, 12);
  const tag = buf.subarray(buf.length - 16);
  const ct = buf.subarray(12, buf.length - 16);
  const d = crypto.createDecipheriv('aes-256-gcm', dek, nonce);
  d.setAuthTag(tag);
  return Buffer.concat([d.update(ct), d.final()]);
}

function unlockGranola() {
  const aesKey = crypto.pbkdf2Sync(keychainSecret(), 'saltysalt', 1003, 16, 'sha1');
  const dekB64 = safeStorageDecrypt(
    fs.readFileSync(path.join(GRANOLA_DIR, 'storage.dek')),
    aesKey
  ).toString('utf8');
  const dek = Buffer.from(dekB64, 'base64');
  if (dek.length !== 32) throw new Error(`unexpected data-key length ${dek.length}`);
  return dek;
}

function accessToken(dek) {
  const raw = dekDecrypt(
    fs.readFileSync(path.join(GRANOLA_DIR, 'stored-accounts.json.enc')),
    dek
  );
  const accounts = JSON.parse(JSON.parse(raw.toString('utf8')).accounts);
  const tokens = JSON.parse(accounts[0].tokens);
  const tok = tokens.access_token;
  const payload = JSON.parse(
    Buffer.from(tok.split('.')[1], 'base64url').toString('utf8')
  );
  const secsLeft = payload.exp - Math.floor(Date.now() / 1000);
  if (secsLeft <= 0) {
    throw new Error(
      'The stored Granola token has expired. Open the Granola app once so it ' +
      'refreshes the token, then re-run this export.'
    );
  }
  return { token: tok, email: accounts[0].email, secsLeft };
}

function readCacheText(dek) {
  try {
    return dekDecrypt(
      fs.readFileSync(path.join(GRANOLA_DIR, 'cache-v6.json.enc')),
      dek
    ).toString('utf8');
  } catch (_) {
    return '';
  }
}

// ------------------------------------------------------------------ API -----

async function api(endpoint, token, body) {
  const res = await fetch(`${API}/${endpoint}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'Granola/6.0.0',
      'Accept-Encoding': 'gzip',
    },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`${endpoint} -> HTTP ${res.status}`);
  return res.json();
}

// ------------------------------------------------- ProseMirror -> markdown ---

function inline(nodes) {
  return (nodes || []).map((n) => {
    if (n.type === 'text') {
      let t = n.text || '';
      for (const m of n.marks || []) {
        if (m.type === 'bold') t = `**${t}**`;
        else if (m.type === 'italic') t = `*${t}*`;
        else if (m.type === 'link') t = `[${t}](${(m.attrs || {}).href || ''})`;
      }
      return t;
    }
    return inline(n.content);
  }).join('');
}

function block(nodes, depth = 0) {
  const lines = [];
  for (const n of nodes || []) {
    switch (n.type) {
      case 'heading':
        lines.push('#'.repeat((n.attrs || {}).level || 3) + ' ' + inline(n.content), '');
        break;
      case 'paragraph': {
        const t = inline(n.content);
        if (t.trim()) lines.push(t, '');
        break;
      }
      case 'bulletList':
      case 'orderedList':
        for (const li of n.content || []) {
          let first = true;
          for (const sub of li.content || []) {
            if (sub.type === 'paragraph') {
              lines.push('  '.repeat(depth) + (first ? '- ' : '  ') + inline(sub.content));
              first = false;
            } else if (sub.type === 'bulletList' || sub.type === 'orderedList') {
              lines.push(...block([sub], depth + 1));
            }
          }
        }
        lines.push('');
        break;
      case 'horizontalRule':
        lines.push('---', '');
        break;
      default:
        lines.push(...block(n.content, depth));
    }
  }
  return lines;
}

// --------------------------------------------------------------- helpers ----

function stripClassYear(s) { return (s || '').replace(/\.\d+$/, '').trim(); }

function attendee(p) {
  if (!p) return null;
  const email = (p.email || '').trim();
  if (NAME_MAP[email]) return `${NAME_MAP[email]} (${email})`;
  let name = p.name || (((p.details || {}).person || {}).name || {}).fullName;
  name = stripClassYear(name);
  if (!name && email) {
    name = stripClassYear(email.split('@')[0]).replace(/[._-]+/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return email ? `${name} (${email})` : name;
}

function attendeeList(people) {
  const out = [];
  const seen = new Set();
  for (const p of [people.creator, ...(people.attendees || [])]) {
    if (!p || seen.has(p.email)) continue;
    seen.add(p.email);
    const a = attendee(p);
    if (a) out.push(a);
  }
  return out.join(', ');
}

function micName(doc) {
  // the recorder = the document creator; their first name labels mic segments
  const c = doc.people && doc.people.creator;
  const full = c && (NAME_MAP[c.email] || c.name ||
    (((c.details || {}).person || {}).name || {}).fullName);
  const first = stripClassYear(full || '').split(/\s+/)[0];
  return first || 'Me';
}

function formatTranscript(segs, mic) {
  const sorted = [...segs].sort((a, b) =>
    a.start_timestamp.localeCompare(b.start_timestamp));
  const t0 = new Date(sorted[0].start_timestamp).getTime();
  return sorted.map((s) => {
    const rel = Math.max(0, Math.floor((new Date(s.start_timestamp).getTime() - t0) / 1000));
    const mm = String(Math.floor(rel / 60)).padStart(2, '0');
    const ss = String(rel % 60).padStart(2, '0');
    const spk = s.source === 'microphone'
      ? `${mic} (mic)`
      : 'Other participant (system audio)';
    return `**[${mm}:${ss}] ${spk}:** ${(s.text || '').trim()}`;
  }).join('\n\n');
}

function slug(title, date) {
  const s = (title || 'untitled').toLowerCase()
    .replace(/[^\w\s-]/g, ' ').trim()
    .replace(/[\s_]+/g, '-').replace(/-+/g, '-')
    .replace(/^-|-$/g, '').slice(0, 80);
  return `${date}-${s || 'untitled'}.md`;
}

function findShareLink(cacheText, doc) {
  // Best effort: the "Chat with meeting transcript" share token lives in a chat
  // message in the cache. Map it to this doc by the doc title; fall back to a
  // lone token when only one is present.
  if (!cacheText) return null;
  const tokens = [...cacheText.matchAll(/https:\/\/notes\.granola\.ai\/t\/[\w-]+/g)]
    .map((m) => m[0]);
  if (tokens.length === 0) return null;
  if (doc.title) {
    const ti = cacheText.indexOf(doc.title);
    if (ti >= 0) {
      let best = null, bestDist = Infinity;
      for (const m of cacheText.matchAll(/https:\/\/notes\.granola\.ai\/t\/[\w-]+/g)) {
        const d = Math.abs(m.index - ti);
        if (d < bestDist) { bestDist = d; best = m[0]; }
      }
      if (best && bestDist < 8000) return best;
    }
  }
  return tokens.length === 1 ? tokens[0] : null;
}

function existingDocIds(dir) {
  const ids = new Set();
  if (!fs.existsSync(dir)) return ids;
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.md')) continue;
    const m = fs.readFileSync(path.join(dir, f), 'utf8')
      .match(/Granola document id:\s*([\w-]+)/);
    if (m) ids.add(m[1]);
  }
  return ids;
}

// ------------------------------------------------------------------ main ----

function buildNote(doc, panel, segs, shareLink) {
  const date = doc.created_at.slice(0, 10);
  const notesMd = panel
    ? block((panel.content || {}).content).join('\n').trim()
    : '_No AI summary panel was generated for this meeting._';
  const mic = micName(doc);
  const parts = [
    `# ${doc.title || 'Untitled note'}`,
    '',
    `- Date: ${date}`,
    `- Granola document id: ${doc.id}`,
    `- Created at: ${doc.created_at}`,
    `- Attendees: ${attendeeList(doc.people || {})}`,
    `- Content source: enhanced notes (AI summary panel)`,
    `- Transcript: verbatim from Granola, ${segs.length} segments`,
    '',
    '---',
    '',
    '## Notes',
    '',
    notesMd,
    '',
    '---',
    '',
  ];
  if (shareLink) {
    parts.push(`Chat with meeting transcript: [${shareLink}](${shareLink})`, '', '---', '');
  }
  parts.push('## Verbatim transcript', '', formatTranscript(segs, mic), '');
  return { text: parts.join('\n'), filename: slug(doc.title, date) };
}

(async () => {
  const dek = unlockGranola();
  const { token, email, secsLeft } = accessToken(dek);
  console.log(`Authenticated as ${email} (token valid ${Math.round(secsLeft / 60)} min).`);

  const { docs } = await api('v2/get-documents', token, { limit: 200 });
  const valid = docs
    .filter((d) => d.valid_meeting && !d.deleted_at)
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  const have = existingDocIds(OUT_DIR);
  let targets;
  if (ONLY_ID) targets = valid.filter((d) => d.id === ONLY_ID);
  else if (MODE_ALL) targets = valid;
  else targets = valid.filter((d) => !have.has(d.id));

  if (MODE_LIST) {
    for (const d of valid) {
      const tag = have.has(d.id) ? 'in-repo' : 'NEW    ';
      console.log(`${tag}  ${d.created_at}  ${d.id}  ${JSON.stringify(d.title)}`);
    }
    console.log(`\n${valid.length} documents, ${valid.filter((d) => !have.has(d.id)).length} new.`);
    return;
  }

  if (targets.length === 0) {
    console.log('No new notes to export.');
    return;
  }

  const cacheText = readCacheText(dek);
  fs.mkdirSync(OUT_DIR, { recursive: true });
  for (const doc of targets) {
    let panel = null, segs = [];
    try {
      const panels = await api('v1/get-document-panels', token, { document_id: doc.id });
      panel = (panels || []).find((p) => p.title === 'Summary') || (panels || [])[0] || null;
    } catch (e) { console.log(`  (panels unavailable for ${doc.id}: ${e.message})`); }
    try {
      segs = await api('v1/get-document-transcript', token, { document_id: doc.id });
      if (!Array.isArray(segs)) segs = [];
    } catch (e) { console.log(`  (transcript unavailable for ${doc.id}: ${e.message})`); }

    if (segs.length === 0) {
      console.log(`Skipping ${JSON.stringify(doc.title)}: no transcript yet.`);
      continue;
    }
    const shareLink = findShareLink(cacheText, doc);
    const { text, filename } = buildNote(doc, panel, segs, shareLink);
    fs.writeFileSync(path.join(OUT_DIR, filename), text);
    console.log(`Wrote ${filename}  (${segs.length} segments${shareLink ? ', share link' : ''})`);
  }
})().catch((e) => { console.error('ERROR:', e.message); process.exit(1); });
