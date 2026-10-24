# memory/raw/

Immutable copies of external sources: articles, docs pages, transcripts, repo READMEs,
pasted text. `/ingest` writes them; wiki pages cite them.

- One file per source: `YYYY-MM-DD_short-slug.md`, frontmatter with `source_type`,
  `source_url`, `ingested` and `tags`, then the extracted content.
- Never edit or rename a file here. A correction is a new file with a `-correction` suffix.
- Never store credentials or private personal data here, and stage files here one by one:
  raw dumps are the first thing a careless `git add` would publish.
