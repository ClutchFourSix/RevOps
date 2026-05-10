# RevOps Hidden Job Radar

A lightweight hidden job market intelligence system.

The goal is to identify companies likely to need:

- lead generation
- outbound sales
- appointment setting
- RevOps help
- recruiting support
- CRM/process cleanup

...before they publicly post jobs.

## How It Works

The scanner:

1. Searches public web sources
2. Looks for expansion/growth signals
3. Scores those signals with weighted keywords
4. Builds a ranked leads file
5. Runs automatically every 6 hours via GitHub Actions

## Structure

```text
scanner/
  main.py

data/
  keywords.json
  sources.json
  leads.json

.github/workflows/
  scan.yml
```

## Run Locally

```bash
python scanner/main.py
```

Results are written to:

```text
data/leads.json
```

## Cloudflare Deployment Idea

This repo was designed so the dashboard can later be served using:

- Cloudflare Pages
- Cloudflare Workers
- or a static HTML dashboard

## Example Use Cases

- Hidden job market prospecting
- RevOps consulting
- B2B lead generation
- Sales intelligence
- Market expansion tracking
- Pre-hiring business intelligence
