# Atlas — a map of the federal funding ecosystem for university spinouts

> **Repository:** <https://github.com/elliegang-max/atlas-federal-funding-ecosystem>
>
> **MGT 409 final project — Ellie Gang.** This repo holds the app, the report
> (`report.html`) and the slide deck (`slides.html`). Canvas accepts either a
> URL or files but not both, so the link is repeated at the top of every
> document.

Atlas answers two questions that a university technology transfer office
currently answers by browsing agency websites one at a time:

1. **What does the federal funding ecosystem actually look like?** An
   interactive map of 118 federal organizations — departments, agencies,
   institutes, and the specific programmes that write checks to early-stage
   companies — showing how they nest inside each other. Click any one for its
   venture arm, check sizes, application timeline, budget, eligibility, and
   contact point.
2. **Which of them should fund *my* research?** A researcher describes their
   science and funding need in plain English and gets a ranked, sourced
   shortlist with the honest reasons each one might not work.

Built for MGT 409. Model: `gpt-6-luna` through the Portkey gateway.

---

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:8010**.

That is the whole setup. The ecosystem graph is committed to the repo at
`data/ecosystem.json`, so there is nothing to build before the app works.

### The API key

Atlas looks for `PORTKEY_API_KEY` in this order:

1. the `PORTKEY_API_KEY` environment variable
2. `.env` in the repo folder
3. `.env` in each of the three folders above the repo

So a `.env` placed one level above the cloned repo is found automatically. See
`.env.example` for the format. `PORTKEY_API_KEY` is the only key required.

The map works without a key. Only the matching agent spends tokens.

### A different port

```bash
PORT=9000 python app.py
```

---

## What costs what

| | tokens | cost |
|---|---|---|
| Browsing the map | none | $0.00 |
| One funding search | ~15,000 | ~$0.06 |
| Rebuilding the whole graph | ~475,000 | ~$2.42 |

The graph is built once and committed. Running the app never rebuilds it.

---

## Rebuilding the graph

Only needed if you change the seed list or want fresher profiles.

```bash
python -m atlas.enrich --limit 3   # smoke test, three organizations
python -m atlas.enrich             # build whatever is missing
python -m atlas.enrich --force     # rebuild everything, ~4 minutes, ~$2.42
python -m atlas.enrich --only nih,barda,arpa-h
```

The build is resumable: it skips organizations already in `data/ecosystem.json`
unless you pass `--force`.

---

## Checking the safety guards

```bash
python check_guards.py
```

Runs ten cases — prompt injection, credential extraction, role reassignment,
forged role tags, ranking manipulation, and the length limits — and reports
what each one did. Costs nothing, because every case is decided before a model
call is made.

---

## How it is put together

```
app.py                  FastAPI server, both interfaces, request guards
atlas/
  seed.py               the curated skeleton: 118 organizations, placed by hand
  schema.py             Pydantic models; the enrichment and matching contracts
  enrich.py             build step — one structured call per organization
  match.py              runtime — brief, retrieve, rank
  graph.py              loading and walking the built graph
  guard.py              injection scan, length caps, rate limit, spend ceiling
  config.py             key discovery and the Portkey client
  usage.py              token accounting, writes data/usage_log.jsonl
prompts/
  enrich.md             how to profile an organization
  brief.md              how to read a researcher's description
  rank.md               how to rank and what to be honest about
static/
  index.html            the ecosystem map (d3 radial tree)
  match.html            the matching interface
data/
  ecosystem.json        the built graph — committed
  usage_log.jsonl       every run's real token counts — gitignored
```

### Why the skeleton is hand-written

`atlas/seed.py` asserts which organizations exist and how they nest. The model
fills in details but can never add, remove, or re-parent a node. A model asked
to produce both the list of agencies *and* their details will invent an agency
that sounds entirely plausible. Fixing the skeleton means every node on the map
is one a human put there.

### Why matching is three stages, not one

Handing all 118 full profiles to the model for every question would be roughly
150,000 input tokens. Instead:

1. **brief** — one call turns free text into a structured brief
2. **retrieve** — pure Python scores all 118 nodes and keeps the best twelve
3. **rank** — one call over twelve condensed profiles

Stage 2 costs nothing and cuts the input by about 95%, for an answer that is
better rather than worse: the model reasons over a short relevant list instead
of skimming a long one.

### Switching datasets

`atlas/seed.py` is the dataset. Add or edit rows in `ROWS` — the format is
documented at the top of the file — then run `python -m atlas.enrich` to
profile the new entries. Validate the hierarchy first with:

```bash
python -m atlas.seed
```

---

## Honest limitations

- **Profiles are model-generated and can be wrong.** Every one carries its
  sources, a confidence rating, and a note saying which part is least reliable.
  The interface shows all three. Verify before acting.
- **No individual contacts are published.** The enrichment agent is instructed
  to prefer programme inboxes and public contact pages over named people,
  because a wrong name burns a first impression and program officers rotate.
  Across all 118 organizations the current build names zero individuals.
- **Figures go stale.** Award ceilings change with appropriations and between
  solicitation cycles. Each profile records when it was retrieved.
