# Caso 03 — Post social: chi chiede ciò che vendiamo

**Cosa fa.** Ogni mattina cerca su X, Reddit e LinkedIn chi si lamenta di un problema o chiede una soluzione che rientra in uno dei servizi in vendita. Jev decide se l'autore è un potenziale cliente; su Telegram arrivano solo le persone nuove sopra soglia. Si risponde nel thread, a mano.

## Pipeline

Per ogni servizio: 4–6 ricerche sulle API social → scarti meccanici → memoria dei post già giudicati → Jev sui post nuovi, 6 in parallelo → punteggio e soglia del servizio → Telegram.

Scarti meccanici prima di Jev, tutti gratis:
- autori esclusi (i propri account);
- post più vecchi della finestra del servizio (7 giorni);
- testo sotto i 40 caratteri, link esclusi;
- doppioni per URL e per contenuto (lo stesso post in più subreddit);
- post già giudicati negli ultimi 90 giorni.

Giro del 30/09/2026 su un servizio: 101 post trovati, 39 nuovi, giudicati da Jev, zero sopra soglia, circa 0,004 $ fra API social e Jev. Il giorno prima, primo giro senza memoria: 125 post giudicati.

## Cosa legge Jev

```
Platform: r/<subreddit> | x | linkedin
Date: 2026-09-29
Author: <nome>
Title: <titolo, se c'è>
Post: <testo, tagliato a 3.000 caratteri>
```

~800 token per chiamata.

## Domande

Tre comuni a tutti i servizi, una specifica per servizio.

```json
{
 "buyer_not_seller": "Is the author someone who has this problem themselves or wants to obtain a solution for their own business or work, rather than a freelancer, agency, tool maker, course seller or content creator promoting their own offer or product?",
 "concrete_request": "Does the post contain a concrete request: asking to hire someone, asking for quotes or recommendations for a solution, stating a budget, or describing an active attempt to solve the problem that is not working?",
 "non_technical": "Does the author appear to lack the technical skills or the time to build this solution entirely by themselves?"
}
```

Domanda del servizio (esempio: rendere economici i flussi AI):

> Would a ready-made system or a done-for-you setup that moves this author's recurring AI workflows (Claude Code, agents, automations, API calls) onto free or very cheap models via OpenRouter, with a paid model only as fallback and automatic checks that block the errors cheap models make, directly solve the cost problem this author describes?

La prima domanda comune è quella che conta di più sui social: gran parte dei post che contengono "looking for a demo video" o "API costs too high" sono di chi **vende** quella cosa. Una ricerca per parole chiave non li distingue; Jev sì.

## Punteggio

```python
score = j["buyer_not_seller"] * j["fit"] * max(j["concrete_request"], j["non_technical"])
tenuto = min(j["buyer_not_seller"], j["fit"]) >= 0.6 and score >= soglia_del_servizio   # 0,45–0,55
```

`max(concrete_request, non_technical)`: basta che chieda qualcosa di concreto **oppure** che non sappia farselo da solo.

## Un file per servizio

```json
{
  "codice": "SRV03",
  "nome": "AI a costo quasi zero",
  "finestra_giorni": 7,
  "soglia": 0.5,
  "domanda_fit": "Would a ready-made system ... directly solve the cost problem this author describes?",
  "ricerche": [
    {"piattaforma": "x",
     "query": "(\"API bill\" OR \"API costs\" OR \"token costs\" OR \"too expensive\") (Claude OR OpenAI OR \"Claude Code\" OR LLM) -filter:retweets"}
  ]
}
```

Aggiungere un servizio = aggiungere un file. Il codice non cambia.

## Spesa

- Tetto per giro: 0,10 $, e 0,02 $ per singola chiamata alle API social.
- Costo Jev stimato dai token: somma di `usage.input_tokens` × 4,2e-08 $ (stima usata nel nostro codice, non un listino ufficiale).
- Il giro si ferma quando raggiunge il tetto e lo scrive nel report.

## Codice della chiamata, con tentativi

```python
def jev_score(p, questions, key):
    state = f"Platform: {p['where']}\nDate: {p['date']}\nAuthor: {p['author']}\nTitle: {p['title']}\nPost: {p['text']}"
    q = {k: {"type": "noul", "instructions": v} for k, v in questions.items()}
    for attempt in range(3):
        try:
            answer = post_json(JEV_URL, {"model": "jev-latest", "state": state, "questions": q},
                               {"Authorization": "Bearer " + key}, timeout=60)
            p["jev"] = {k: round(float(answer.get("answers", {}).get(k, {}).get("noul", 0)), 3) for k in q}
            p["jev_tokens"] = answer.get("usage", {}).get("input_tokens", 0)
            return p
        except Exception as error:
            p["jev_error"] = str(error)[:200]
            time.sleep(2 * (attempt + 1))
    return p
```

Chiamate in parallelo:

```python
with concurrent.futures.ThreadPoolExecutor(6) as ex:
    scored = list(ex.map(lambda p: jev_score(p, questions, jev_key), new))
```
