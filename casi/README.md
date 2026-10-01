# Casi reali

Tre automazioni che usano Jev ogni giorno o ogni settimana, su una VPS, senza revisione umana prima del risultato. Stesso motore (una chiamata `noul` per elemento), tre materiali diversi. Leggetele come esempi da copiare: la regola generale è in [GUIDA-JEV.md](../GUIDA-JEV.md).

| Caso | Cosa giudica | Domande | Quando gira | Cosa ne esce |
|---|---|---|---|---|
| [01 Notizie](01_notizie.md) | storie da feed RSS (titoli) | 3 + 1 per i doppioni | ogni giorno 13:00, martedì 9:00 | la notizia su cui Poltronave scrive il post del giorno e l'articolo del blog |
| [02 Annunci di lavoro](02_annunci_lavoro.md) | annunci Indeed e LinkedIn (descrizione intera) | 5 | lunedì e giovedì | digest Telegram con annunci verdi (remoti) e arancioni (da verificare) |
| [03 Post social](03_post_social.md) | post Reddit, X, LinkedIn | 3 comuni + 1 per servizio | ogni mattina | su Telegram solo le persone che chiedono ciò che vendiamo |

Cosa hanno in comune:

- la raccolta non la fa Jev (feed RSS, JobSpy, API social);
- tutto ciò che si scarta con certezza si scarta prima (regex, date, doppioni, cache);
- domande separate, punteggio moltiplicato, soglia per domanda;
- ogni voto viene salvato, anche degli scarti, per tarare;
- un errore di Jev su un elemento non ferma il giro.
