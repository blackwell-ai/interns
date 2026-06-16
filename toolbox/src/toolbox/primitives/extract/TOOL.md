# extract: explode listing payloads into per-item records

No connection needed. Read-only: parses bytes already fetched by `fetch.urls`.

Why it exists: `fetch.urls` returns one row per source URL (a whole subreddit
listing or an HN Algolia blob). The relevance filter and the digest both work
per post, so we need one record per post/story. No other primitive does this.

## extract.items
- in: `pages.jsonl` ({url, status, text[, label]}) → out: `items.jsonl`
- flags: `--max-chars 4000` (cap per-item text)
- one record per post/story:
  `{source, label, title, url, link, text, author, score, comments, ts}`
  - `url` is the discussion permalink (Reddit comment thread or HN item page);
    `link` is the outbound link if the post points off-site.
  - `text` is `title + body`, the field `llm.filter` judges by default.
- payloads auto-detected by JSON shape, then URL:
  - Reddit `{data:{children:[{data}]}}` (public `.json` or `oauth.reddit.com`)
  - HN Algolia `{hits:[...]}`
- a page that is non-200 or not parseable JSON is recorded as unparsed and
  reported, never silently dropped.
