# Caso 01 — Notizie per Poltronave

**Cosa fa.** Ogni giorno alle 13:00 sceglie la notizia su cui [Poltronave](https://poltronave.it) scrive il post satirico su X; il martedì sceglie se l'articolo del blog sarà d'attualità o di approfondimento. È il motore di questa repo: [filtro_notizie.py](../filtro_notizie.py), configurazione [esempi/conti_pubblici.json](../esempi/conti_pubblici.json).

## Pipeline

Google News (5 ricerche) + 8 feed RSS diretti → regex sul titolo → raggruppamento per storia → Jev sulle prime 12 storie → classifica. Giro del 29/09/2026: 379 titoli → 252 passano la regex → 158 storie → 12 giudicate → 4 forti.

## Cosa legge Jev

```
Headline: Spread Btp-Bund risale a 94 punti
Other headlines on the same story: Lo spread tra Btp e Bund chiude in rialzo a 94 punti
Outlets: ANSA, SoldiOnline.it
Date: 2026-09-28
```

Solo titoli: ~470 token in entrata per chiamata. Mettere gli altri titoli della stessa storia aiuta Jev a capire di cosa si parla quando un titolo è ambiguo.

## Domande

| Nome | Ruolo | Domanda |
|---|---|---|
| `conti_pubblici` | obbligatoria ≥ 0,6 | Does this news item concern Italian national public finances: public debt, deficit, the budget law, a tax or public spending measure, interest on the debt, the BTP-Bund spread or Italy's sovereign rating? Reject company news, markets unrelated to government bonds, local administrations and other countries. |
| `fatto_concreto` | obbligatoria ≥ 0,6 | Is this a concrete, verifiable event: an official figure released, a measure approved or formally presented, a rating decision, an official report? Reject opinions, interviews, rumors, polls and political statements without a decision. |
| `cifra_verificabile` | bonus | Does the item report a euro amount or a figure (cost, coverage, debt, deficit, rate) that could be checked against a primary source such as Banca d'Italia, ISTAT, MEF, the Parliamentary Budget Office, Corte dei conti or Eurostat? |

Punteggio = `conti_pubblici × fatto_concreto × (0,5 + cifra_verificabile/2)`. Forte = entrambe le obbligatorie ≥ 0,6 e almeno 2 testate.

## Esiti veri

| Titolo | Voti | Esito |
|---|---|---|
| Southwest Airlines Co.: BMO Capital conferma il rating Buy | conti pubblici 0,01 | scartata (passava la regex per "rating") |
| TPL Linea – nuova manovra tariffaria per gli abbonamenti studenti | conti pubblici 0,03 | scartata (passava per "manovra") |
| Caro carburanti, Di Paola: «I fondi della manovra vadano a famiglie e imprese» | fatto concreto 0,08 | scartata: dichiarazione |
| Calendario aste titoli di Stato ottobre 2026 | fatto concreto 0,39 | sotto soglia |
| Rialzo spread Btp-Bund e variazione rendimenti a settembre | 0,98 · 0,77 · 0,83 → 0,69 | prima, 8 testate |

## La quarta domanda: già scritta?

Prima di scrivere l'articolo del blog, la notizia scelta passa da un'altra domanda, con i titoli degli articoli già usciti nello `state` ([`gia_coperta`](../filtro_notizie.py)):

```
News headline: <titolo della notizia>
Already published:
- <titolo articolo 1>
- <titolo articolo 2>
```

> Does one of the already published items already cover this same news event or the same official figure? Answer yes only for the same event or number, not for the same broad topic.

Soglia 0,5. Aggiunta il 27/09/2026, quando il giro stava per riscrivere l'articolo sul deficit al 3,1% già uscito. Una regex qui non può funzionare: due titoli sullo stesso fatto spesso non hanno parole in comune, e due titoli sul debito pubblico ne hanno tante pur parlando di fatti diversi.

## Effetto misurato a valle

Il post lo scrive un modello linguistico. Passargli le 8 storie migliori invece dei feed interi ha portato il giro da circa 80 richieste e 11 milioni di token a meno di 60 richieste e circa 4 milioni (27/09/2026). Jev in quel giro costa ~6.500 token.
