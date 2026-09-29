# AGENTS.md — istruzioni per assistenti AI

You are integrating a news filter into an existing codebase. The humans you work for are experienced programmers who rarely use AI tools: explain each change in plain words in your summary, keep diffs small and reviewable, and never replace their existing regex filter — add to it.

## What this repo is

`filtro_notizie.py` (single file, Python 3.8+, standard library only) turns RSS feeds into a short ranked list of relevant news stories:

1. `raccogli(config, ore)` — read Google News searches + direct RSS feeds → `[{titolo, fonte, data, link}]` (`data` is a timezone-aware `datetime`)
2. `prefiltra(items, config)` — cheap regex on the title (`config["prefiltro_regex"]`), drops certain off-topic items
3. `raggruppa(items, config)` — groups titles of the same story by shared words → `[{titolo, fonti, voci, ultima}]`, sorted by number of distinct outlets
4. `chiedi_a_jev(state, domande, chiave)` — one HTTP call to Jev (TypeSafe API) answering several yes/no questions about `state` → `{name: probability 0..1}`
5. `punteggio(voti, config)` + `e_forte(storia, config)` — score = product of mandatory answers × Π(0.5 + bonus/2); "forte" = every mandatory answer ≥ its `soglia` AND `len(fonti) >= min_testate`

`filtra(config, ore, max_jev, chiave)` runs all five and returns `(stories, stats)`. `gia_coperta(titolo, gia_pubblicati, chiave)` asks Jev whether a headline is already covered by previously published titles (same event or figure, not same topic).

All topic-specific data lives in a JSON config (`esempi/conti_pubblici.json` = real production config, `esempi/modello.json` = template). The code has no topic knowledge.

## Jev API contract (verified against https://api.typesafe.ai/openapi.json)

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer $TYPESAFE_API_KEY
Content-Type: application/json

{"model": "jev-latest",
 "state": "<string or object: the content every question refers to>",
 "questions": {"<name>": {"type": "noul", "instructions": "<yes/no question>"}}}

→ {"model": "jev-1.x.x",
   "answers": {"<name>": {"type": "noul", "noul": 0.98}},
   "usage": {"input_tokens": int, "output_tokens": int}}
```

- `noul` = probability of "yes". Other types exist (`choice` with `criteria` {name: description}; `score` with ordered `criteria` list) — do not introduce them unless asked.
- All questions for one item go in ONE request.
- `GET /v1/models` lists available models.

## Integration procedure

1. **Find their current filter.** Locate where they apply the regex to news titles. Do not modify the regex except to make it broader if asked; it must only drop *certain* off-topic items.
2. **Default to the smallest integration (Level 1 in README):** after their regex, call `chiedi_a_jev` per item (or per story if you also add `raggruppa`) with 2–3 questions, keep items whose mandatory answers ≥ threshold. Import from `filtro_notizie.py` or copy `chiedi_a_jev` verbatim if they prefer no dependency.
3. **Write the questions with them, not for them.** Ask the humans: what is on-topic, and which false positives does the regex let through today. Put those false positives after "Reject …" in the question. One criterion per question. English questions work fine on Italian titles.
4. **Cap the calls.** Always keep a maximum number of Jev calls per run (like `--max-jev`, default 12), applied after sorting, so cost per run is bounded.
5. **Handle failure per item.** A Jev timeout/HTTP error must skip that item and log to stderr, never crash the run or silently keep the item.
6. **Show evidence.** Run their pipeline with and without Jev on the same window and show them the items Jev dropped with their scores. That comparison is what convinces them.

## Hard rules

- Each user brings their own Jev key (create it at https://console.typesafe.ai/). The API key comes only from the environment or a git-ignored `.env` (`TYPESAFE_API_KEY`). Never hardcode it, never log it, never commit `.env`.
- Keep the regex before Jev. Never send every raw title to Jev.
- Treat Jev answers as probabilities that rank and filter. Do not present them as fact verification: Jev reads only the headline text.
- Thresholds (0.6 default) are starting points; tune them on real runs (`--mostra 30`), not by guessing.
- Standard library only, unless the target codebase already uses `requests`/`httpx` — then match their style.
- Do not change `esempi/conti_pubblici.json`: it mirrors a production config. Create a new config file for their topic.

## Quick checks

```bash
python filtro_notizie.py --config esempi/conti_pubblici.json --senza-jev   # no key needed: fetch + regex + grouping
python filtro_notizie.py --config esempi/conti_pubblici.json --json       # needs TYPESAFE_API_KEY
python -c "import filtro_notizie as f; print(f.chiedi_a_jev('Headline: test', {'q':'Is this a test?'}, f.chiave_jev()))"
```

Expected output of the first command on stderr: `# titoli letti N -> passano la regex N -> storie N -> valutate da Jev 0`.
