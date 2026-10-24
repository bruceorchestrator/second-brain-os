---
topic: llm-wiki-pattern
updated: 2026-10-24
tags: [memory, method, karpathy]
---

> Andrej Karpathy's "LLM wiki" pattern, which `memory/` implements. Instead of searching raw
> documents again for every question, the AI keeps a wiki of compiled, cross-linked pages that
> grows with every source. The owner picks sources and makes decisions; the AI does the
> bookkeeping. Keep this page: it explains the system to every new session.

## Three layers
- **Raw sources:** immutable copies of what was read. The AI reads them and never edits them. Here: `memory/raw/`.
- **The wiki:** pages the AI writes and maintains, one per topic, cross-linked with `[[topic]]`, contradictions flagged on the page. Here: `memory/wiki/`, catalog `wiki/INDEX.md`.
- **The schema:** the document that tells the AI what the knowledge base is about and how it is organised. Here: `CLAUDE.md` and `.claude/rules/memory-loop.md`.

## Three operations
- **Ingest:** save the source, read it, update every page it touches, log it. Here: `/ingest`.
- **Query:** answer from the wiki pages with references to them; a good answer can become a new page. Here: read `wiki/INDEX.md` first, then the pages.
- **Lint:** a periodic health check for contradictions, stale claims, orphan pages and missing links. Here: `/lint`.

## Index and log
The gist pairs the wiki with a catalog (links with one-line summaries) and an append-only,
dated log. Here: `wiki/INDEX.md` and `memory/daily/`.

## Why not search the documents each time
Search starts from zero on every question. A wiki keeps what was already worked out,
deduplicated and linked, so each new source builds on the last one.

## What this system adds
- `STATE.md`: what matters now. The wiki holds what is known; STATE holds what is current.
- `learnings/`: lessons from the owner's corrections, so a mistake is made once.
- `agents/`: one folder per recurring job. Agents read this memory and never keep a copy of it (`agents/README.md`).

## Sources
- Andrej Karpathy, "LLM Wiki" gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
