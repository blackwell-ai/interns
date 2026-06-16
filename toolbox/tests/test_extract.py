"""Offline smoke tests: extract parsing + digest helpers (no network, no LLM)."""

import json

from toolbox.primitives.extract import cli as extract
from toolbox.primitives.llm import cli as llm_cli


def _page(url, payload, label="", status=200):
    return {"url": url, "label": label, "status": status, "text": json.dumps(payload)}


def test_extract_hn_algolia():
    payload = {"hits": [
        {"objectID": "1", "title": "Agentic commerce protocol", "url": "https://x.com",
         "author": "pg", "points": 100, "num_comments": 20, "created_at": "2026-06-15T00:00:00Z"},
    ]}
    items = extract._parse_page(_page("https://hn.algolia.com/api/v1/search", payload), 4000)
    assert len(items) == 1
    it = items[0]
    assert it["source"] == "Hacker News"
    assert it["url"] == "https://news.ycombinator.com/item?id=1"  # discussion permalink
    assert it["link"] == "https://x.com"  # outbound link preserved
    assert "Agentic commerce protocol" in it["text"]


def test_extract_reddit_listing_drops_stickied():
    payload = {"data": {"children": [
        {"kind": "t3", "data": {"title": "My store is invisible to ChatGPT",
                                 "selftext": "help", "permalink": "/r/ecommerce/abc",
                                 "subreddit": "ecommerce", "author": "merch",
                                 "score": 5, "num_comments": 3, "created_utc": 1.0}},
        {"kind": "t3", "data": {"title": "pinned mod post", "stickied": True,
                                 "permalink": "/x", "subreddit": "ecommerce"}},
    ]}}
    items = extract._parse_page(_page("https://www.reddit.com/r/ecommerce", payload), 4000)
    assert len(items) == 1  # the stickied post is dropped
    assert items[0]["source"] == "r/ecommerce"
    assert items[0]["url"] == "https://www.reddit.com/r/ecommerce/abc"


def test_extract_skips_non200_and_garbage():
    assert extract._parse_page({"url": "u", "status": 403, "text": "<html>blocked"}, 4000) == []
    assert extract._parse_page({"url": "u", "status": 200, "text": "not json"}, 4000) == []


def test_extract_items_command_writes_jsonl(tmp_path):
    pages = tmp_path / "pages.jsonl"
    payload = {"hits": [{"objectID": "9", "title": "AI shopping agents", "points": 1}]}
    pages.write_text(json.dumps({"url": "https://hn.algolia.com/x", "status": 200,
                                 "text": json.dumps(payload)}) + "\n")
    out = tmp_path / "items.jsonl"
    extract.items(in_=str(pages), out=str(out), max_chars=4000)
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert lines[0]["title"] == "AI shopping agents"


def test_digest_sanitize_strips_dashes():
    assert "—" not in llm_cli._sanitize("a — b")
    assert "–" not in llm_cli._sanitize("a – b")
    assert llm_cli._sanitize("plain hyphen-ok") == "plain hyphen-ok"


def test_digest_empty_input_writes_placeholder_without_llm(tmp_path):
    rel = tmp_path / "relevant.jsonl"
    rel.write_text("")  # nothing cleared the bar
    out = tmp_path / "digest.md"
    llm_cli.digest(in_=str(rel), out=str(out), brain_dir="", reviewed=0,
                   reviewed_from="", date="2026-06-15", model="")
    md = out.read_text()
    assert "Researcher digest, 2026-06-15" in md
    assert "Nothing cleared the relevance bar" in md


_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Reddit eCommerce</title>
  <entry>
    <author><name>/u/merch</name></author>
    <category term="ecommerce" label="r/ecommerce"/>
    <content type="html">&lt;p&gt;My store is invisible to ChatGPT, help&lt;/p&gt;</content>
    <link href="https://www.reddit.com/r/ecommerce/comments/abc/title/"/>
    <published>2026-06-15T00:00:00+00:00</published>
    <title>My store is invisible to ChatGPT</title>
  </entry>
</feed>"""


def test_extract_reddit_rss_atom():
    items = extract._parse_page(
        {"url": "https://www.reddit.com/r/ecommerce", "label": "r/ecommerce",
         "status": 200, "text": _ATOM}, 4000)
    assert len(items) == 1
    it = items[0]
    assert it["source"] == "r/ecommerce"
    assert it["author"] == "merch"  # /u/ prefix stripped, not char-stripped
    assert it["url"] == "https://www.reddit.com/r/ecommerce/comments/abc/title/"
    assert "invisible to ChatGPT" in it["text"]  # HTML entities decoded, tags stripped
    assert "<p>" not in it["text"]


def test_extract_reddit_rss_truncated_is_unparsed_not_crash():
    truncated = _ATOM[: len(_ATOM) // 2]  # XML cut mid-document
    assert extract._parse_page(
        {"url": "https://www.reddit.com/r/x", "status": 200, "text": truncated}, 4000) == []


def test_discord_message_to_item():
    from toolbox.primitives.discord import cli as dc
    assert dc.message_to_item({"author": {"bot": True}, "content": "a real sentence here"}, "L", "G") is None
    assert dc.message_to_item({"author": {"username": "a"}, "content": "Very"}, "L", "G") is None  # chatter
    it = dc.message_to_item(
        {"id": "9", "channel_id": "5", "author": {"username": "merch", "global_name": "Merch"},
         "content": "<@123> agents are <:fire:1> changing checkout flows", "timestamp": "2026-06-16T00:00:00Z"},
        "Catena #news", "42")
    assert it["author"] == "Merch"
    assert it["url"] == "https://discord.com/channels/42/5/9"
    assert "<@123>" not in it["text"] and ":fire:" in it["text"]
    assert it["source"] == "Catena #news"
    # link-only body falls back to the embed title/description
    it2 = dc.message_to_item(
        {"author": {"username": "x"}, "content": "https://t.co/x",
         "embeds": [{"title": "Stripe ships agent checkout", "description": "new ACP feature"}]}, "L", "G")
    assert it2 and "Stripe ships agent checkout" in it2["text"]


def test_digest_sources_section_lists_each_source_with_count():
    md = llm_cli._sources_section([
        {"source": "r/ecommerce"}, {"source": "r/ecommerce"},
        {"source": "Hacker News"}, {"label": "X @OpenAI"},
    ])
    assert "## Sources indexed" in md
    assert "- r/ecommerce (2)" in md
    assert "- Hacker News (1)" in md
    assert "- X @OpenAI (1)" in md  # falls back to label when source missing


def test_filter_batch_keeps_only_relevant_indices(tmp_path, monkeypatch):
    from toolbox.core import llm

    items = tmp_path / "items.jsonl"
    items.write_text("\n".join(json.dumps({"title": t, "text": t}) for t in ["a", "b", "c"]) + "\n")
    out = tmp_path / "rel.jsonl"

    def fake_parse(prompt, schema, model=None):  # one batch call, no network
        assert "[0]" in prompt and "[2]" in prompt  # all items listed for judging
        return schema(items=[
            {"index": 0, "relevant": True, "reason": "r0", "summary": "s0"},
            {"index": 1, "relevant": False},
            {"index": 2, "relevant": True, "reason": "r2", "summary": "s2"},
        ])

    monkeypatch.setattr(llm, "parse", fake_parse)
    llm_cli.filter_(in_=str(items), out=str(out), criteria="x", field="text", model="", batch=25)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["text"] for r in rows] == ["a", "c"]  # index 1 dropped
    assert rows[0]["reason"] == "r0" and rows[1]["summary"] == "s2"
