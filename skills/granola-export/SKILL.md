---
name: granola-export
version: 1.0.0
description: |
  Export Granola meeting notes into context/samarjit-granola/ in the repo's
  note format (metadata header, AI summary panel, verbatim transcript). Reads
  Granola's encrypted local store via the macOS keychain, then pulls canonical
  content from Granola's API. Use after a meeting to capture the latest note,
  or to backfill every note not yet in the repo.
license: MIT
compatibility: claude-code
allowed-tools:
  - Bash
  - Read
  - Write
---

# granola-export

Pulls Granola meeting notes onto disk so they live in the repo alongside the
other durable context. One note per meeting, written to
`context/samarjit-granola/` in the same format as the notes already there.

## When to use

- A meeting just finished and its note should be in the repo.
- You want to backfill: grab every Granola note that is not already committed.
- You need the verbatim transcript, not just the AI summary (the free Granola
  MCP server paywalls verbatim transcripts; this path does not).

## Run it

From the repo root:

```bash
node skills/granola-export/export.js            # export every note not already in the repo
node skills/granola-export/export.js --list     # list documents and which are new, write nothing
node skills/granola-export/export.js --all       # re-export every document (overwrites existing files)
node skills/granola-export/export.js --id <doc>  # export one document by id
node skills/granola-export/export.js --out <dir> # write somewhere other than context/samarjit-granola
```

The first run shows one macOS Keychain prompt ("security wants to use the
Granola Safe Storage key"). Click Allow, or Always Allow to silence it on later
runs. Granola must be installed and signed in on this machine.

Default mode is idempotent: it reads the document id out of every existing
`.md` file in the output folder and skips anything already there, so rerunning
it only ever adds the new meetings.

## How it works (so the next agent can fix it)

Granola encrypts its local store, so you cannot just read a file off disk. The
chain is:

1. macOS keychain holds a random password under the service `Granola Safe
   Storage`. This is Electron's `safeStorage`. Reading it is the one step that
   prompts the user.
2. That password runs through `PBKDF2(password, "saltysalt", 1003 iterations,
   16 bytes, SHA-1)` to make an AES-128 key.
3. `storage.dek` starts with the bytes `v10`. Strip those, then AES-128-CBC
   decrypt with a 16-byte all-spaces IV. The result is a base64 string that
   decodes to Granola's 32-byte data key (the DEK).
4. The DEK decrypts every `*.enc` file as AES-256-GCM framed `nonce(12
   bytes) || ciphertext || tag(16 bytes)`. That covers `stored-accounts.json.enc`
   (which holds the live API token) and `cache-v6.json.enc`.
5. With the token, call Granola's API for canonical content:
   - `POST /v2/get-documents` lists meetings.
   - `POST /v1/get-document-panels` returns the AI summary panel (the "Summary"
     panel becomes the `## Notes` section, converted from Granola's
     ProseMirror JSON to markdown).
   - `POST /v1/get-document-transcript` returns the verbatim transcript.

Secrets (keychain password, DEK, API token) stay in memory. The script never
prints or writes them.

## Note format

Each file matches the existing notes: an `H1` title, a metadata block (date,
document id, created-at, attendees, content source, segment count), the AI
summary as `## Notes`, an optional "Chat with meeting transcript" share link,
then `## Verbatim transcript` with one line per segment as
`**[MM:SS] Speaker (source):** text`. Microphone segments are labelled with the
meeting creator's first name; everything else is "Other participant".

## Known limits

- Token freshness: the script uses the token Granola last cached. If it has
  expired, open the Granola app once so it refreshes, then rerun. The script
  says so plainly rather than failing silently.
- Share link: the "Chat with meeting transcript" URL only exists in Granola's
  live cache, which the running app rewrites often. The script attaches it when
  it can match it to the meeting and otherwise omits the line. It never guesses
  a link.
- `--all` overwrites existing files and can drop a share link that was captured
  by hand earlier. Default mode never overwrites, so prefer it.
- Speaker names: Granola does not attribute speakers in these transcripts, so
  segments are split only by audio source (microphone vs system). Treat the
  non-microphone speaker as "the other participant", not a specific person.
- Two very short May recordings are marked `valid_meeting: false` by Granola and
  are skipped even under `--all`; they are already in the repo.

## Names

Granola's people enrichment is sometimes wrong (it returned
`Armaan Priyadarshan.29`) or missing (`Shamitd`). The `NAME_MAP` near the top of
`export.js` pins the correct names for known colleagues, grounded in the repo's
own records, not invented. Add an email to that map when a new recurring
attendee shows up wrong. The script also strips a trailing Dartmouth class-year
suffix (`.29`) on its own.

## Acceptance checks

- `--list` authenticates and prints all documents with an `in-repo` or `NEW`
  tag, ending with a count.
- A default run on a clean checkout reproduces every committed note byte for
  byte, except for share-link lines that depend on the volatile cache.
- No secret value appears in stdout or in any written file.

## Changelog

- 1.0.0 (2026-06-16): first version. Built while exporting the Blackwell /
  Public Goods kickoff note. Verified it reproduces that note exactly apart from
  the cache-sourced share link.
