# brain/

Durable company knowledge. This is the memory every agent and human shares.

## Subfolders

- `company/` — what the company is: overview, business model, product, positioning.
  The source of truth; only deliberate edits here change what the company "is".
- `customers/` — customer calls, learnings, problems we've heard. One file per
  customer or call.
- `people/` — employees (human and agent) and key external contacts.
- `research/` — market and technical research, mostly written by the researcher
  agent: competitor notes, relevant papers, conference findings.
- `decisions/` — decision log. One file per decision: what was decided, when, why,
  and what would change our mind.

## Conventions

- One topic per file, kebab-case names, markdown.
- Start each entry with a date and a source (call, link, decision, observation).
- Edit and correct existing files rather than piling up near-duplicates.
- The brain stores knowledge, not secrets — credentials go in `credentials/`.
