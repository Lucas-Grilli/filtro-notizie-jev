# Caso 02 — Radar di annunci di lavoro

**Cosa fa.** Due volte a settimana cerca collaborazioni nel campo dell'AI (formazione, consulenza, automazioni) su Indeed e LinkedIn, in italiano e in inglese, degli ultimi 14 giorni. Jev giudica ogni annuncio; su Telegram arrivano solo quelli sopra soglia, divisi in verdi e arancioni. Nessuna candidatura automatica.

## Pipeline

[JobSpy](https://github.com/speedyapply/JobSpy) (7 ricerche, fino a 12 risultati ciascuna, con e senza filtro remoto) → deduplica per URL → scarta gli annunci senza data verificabile o senza descrizione → riusa i voti degli annunci già visti e invariati → Jev sugli annunci nuovi o cambiati → fasce → Telegram solo per gli annunci mai inviati.

Le ricerche sono per parola chiave ("formatore AI", "consulenza AI", "AI trainer contractor"...), e come ogni ricerca per parola chiave riportano di tutto. Dal giro italiano del 26/09/2026:

| Annuncio trovato | Voto "è davvero un lavoro sull'AI" |
|---|---|
| Chef de rang con minimo 2 anni di esperienza | 0,01 |
| Operaio elettricista | 0,01 |
| Store manager | 0,01 |
| Bando per il reclutamento, Accademia di Belle Arti | 0,42 |

Una regex su "AI" o "intelligenza artificiale" nella descrizione ne avrebbe lasciati passare una parte (molti annunci citano l'AI tra i "plus"); Jev li mette a zero.

## Cosa legge Jev

L'annuncio intero, perché lingua, contratto e remoto si capiscono solo dalla descrizione:

```
Title: ...
Company: ...
Location: ...
Source: indeed
Posted date: 2026-09-24
Description: <descrizione completa>
```

~1.550 token per chiamata in media, fino a ~3.200. Giro italiano del 26/09: 85 annunci, 132.312 token.

## Domande

```python
questions = {
    "italian_language": "Is the main job posting written primarily in Italian, rather than English or another language with just a few Italian words?",
    # nel giro inglese: "english_language": "Is the main job posting written primarily in English, rather than another language with a few English words?"
    "ai_collaboration": "Is the work actually about artificial intelligence, AI tools, training, consulting, or applied AI workflows, rather than a role that only mentions AI in passing?",
    "external_collaboration": "Does the posting clearly allow an independent freelancer, partita IVA/P.IVA, outside contractor, external consultant or business-to-business collaboration? Explicit P.IVA, 'this is a contractor position', or Italian 'Contratto di lavoro: Collaborazione' are strong yes signals, even if direct employment is also offered. A fixed-term employee contract, temporary internal hire, Workday employee application, employee benefits or 'hire to retire' language alone do not prove independent contracting. If contract type is unspecified, express uncertainty. Permanent employment only is a strong no.",
    "skills_fit": "Judge the actual work, not whether this applicant meets every credential. Strong yes for practical AI training, teaching AI tools to schools or adults, instructional design for nontechnical AI users, external AI consulting, business-process optimization using AI, or accessible AI workflows and automations. If several optional course topics are listed, assess whether an AI teaching assignment can be chosen independently. Strong no if a core requirement is programming instruction or years of hands-on software development, Python engineering, agent/RAG coding, data pipelines, model development, machine learning research, data science, generic data labeling, model evaluation or voice recording.",
    "remote_eligible": "Does the posting explicitly allow the work to be done remotely without an on-site requirement? Treat country or residency restrictions and missing location detail as uncertainty.",
}
```

Le domande lunghe non sono nate così: sono cresciute a ogni errore visto nei report (v. sotto, "Tarare le domande").

## Fasce

- Tutte e quattro le prime domande ≥ 0,75, altrimenti l'annuncio resta solo nel JSON tecnico.
- **Verde**: anche `remote_eligible` ≥ 0,75.
- **Arancione**: remoto sotto 0,75. Adatto, ma da verificare (spesso è in presenza).

Esempio vero: "Formatore AI Generativa (Scuole)" ha lingua 0,99, tema 0,97, collaborazione 0,96, competenze 0,86, remoto 0,02. È un ottimo annuncio in presenza: con un unico voto finale sarebbe sparito, con le domande separate si vede perché.

## Voti riusati

Gli annunci restano online per settimane: senza memoria, il giro del giovedì ripagherebbe quasi tutti quelli del lunedì. I voti si salvano per annuncio e si riusano finché URL e descrizione non cambiano; quando cambiano le domande, si riparte da una memoria nuova, per non mescolare voti dati a domande diverse.

## Tarare le domande

Quando un voto non convince, non si rifà il giro: si rivalutano solo gli annunci ambigui con la domanda nuova e si salva il voto vecchio accanto al nuovo. Dal registro del 26/09/2026:

| Annuncio | Domanda cambiata | Prima | Dopo |
|---|---|---|---|
| Formatore/Formatrice Intelligenza Artificiale e Didattica | collaborazione esterna | 0,63 | 0,96 |
| Formatore AI Generativa (Scuole) | competenze | 0,70 | 0,86 |
| Formatori per corsi Canva, AI, Coding | competenze | 0,44 | 0,80 |

Cosa è cambiato nelle domande: la collaborazione ha imparato che "Contratto di lavoro: Collaborazione" è un sì forte; le competenze hanno imparato a giudicare il lavoro e non il curriculum del candidato, e che in un bando con più corsi quello sull'AI si può scegliere da solo. Un annuncio tecnico che chiedeva anni di sviluppo software è sceso sotto soglia, come doveva.

## Codice della chiamata

```python
def score_with_jev(item, key, questions):
    state = "\n".join((
        "Title: " + item["title"], "Company: " + item["company"],
        "Location: " + item["location"], "Source: " + item["site"],
        "Posted date: " + item["posted_date"],
        "Description: " + item["description"],
    ))
    payload = {"model": "jev-latest", "state": state,
               "questions": {k: {"type": "noul", "instructions": v} for k, v in questions.items()}}
    answer = request_json("https://api.typesafe.ai/v1/systemone", payload, key)
    values = answer.get("answers", {})
    item["jev"] = {name: round(float(values.get(name, {}).get("noul", 0)), 3) for name in payload["questions"]}
    item["jev_model"] = answer.get("model")
    item["jev_input_tokens"] = answer.get("usage", {}).get("input_tokens", 0)
```

Chi chiama registra l'errore sull'annuncio (`item["jev_error"]`) e passa al successivo.
