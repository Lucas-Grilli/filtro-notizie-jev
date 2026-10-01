# Guida pratica a Jev

Tutto quello che abbiamo imparato usando Jev in produzione su tre automazioni diverse: cosa entra, cosa esce, quanto costa, come si scrivono le domande e gli schemi di codice che si ripetono. I casi completi sono in [casi/](casi/README.md).

---

## 1. Cosa fa, in una riga

Gli dai un testo (`state`) e N domande sì/no; ti restituisce N probabilità da 0 a 1. Una chiamata, un numero per domanda, niente testo libero da interpretare.

## 2. Cosa entra

```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <la vostra chiave, da console.typesafe.ai>
Content-Type: application/json
```

```json
{
  "model": "jev-latest",
  "state": "Headline: Spread Btp-Bund risale a 94 punti\nOther headlines on the same story: Lo spread tra Btp e Bund chiude in rialzo a 94 punti\nOutlets: ANSA, SoldiOnline.it\nDate: 2026-09-28",
  "questions": {
    "conti_pubblici":     {"type": "noul", "instructions": "Does this news item concern Italian national public finances ...? Reject company news, ..."},
    "fatto_concreto":     {"type": "noul", "instructions": "Is this a concrete, verifiable event ...? Reject opinions, ..."},
    "cifra_verificabile": {"type": "noul", "instructions": "Does the item report a euro amount or a figure that could be checked ...?"}
  }
}
```

- **`state`**: il contenuto da giudicare. Può essere una stringa o un oggetto JSON. Noi usiamo sempre una stringa a righe `Campo: valore`, con solo i campi che servono a rispondere alle domande (vedi §5).
- **`questions`**: un nome scelto da voi per ogni domanda. I nomi tornano identici nella risposta.
- **`model`**: `jev-latest` (stabile) o `jev-preview` (versione in prova). `GET /v1/models` li elenca.

## 3. Cosa esce

Risposta reale alla richiesta sopra (30/09/2026):

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "conti_pubblici":     {"type": "noul", "noul": 0.98},
    "fatto_concreto":     {"type": "noul", "noul": 0.73},
    "cifra_verificabile": {"type": "noul", "noul": 0.91}
  },
  "usage": {"input_tokens": 469, "output_tokens": 64}
}
```

- `noul` = probabilità del sì. Vicino a 1 sì, vicino a 0 no, intorno a 0,5 incerto.
- `model` dice la versione vera che ha risposto: salvatela insieme ai voti, se Jev cambia versione vi serve per capire perché i voti si sono spostati.
- `usage` sono i token consumati: sommateli per sapere quanto spende ogni giro.
- Altri tipi di domanda (non li usiamo, ma esistono): `choice` sceglie tra opzioni che descrivete (`criteria: {"arrabbiato": "...", "calmo": "..."}`) e restituisce la scelta con le probabilità di ognuna; `score` dà un voto su una scala ordinata che descrivete (`criteria: ["può aspettare", "questa settimana", "oggi"]`).

## 4. Quanto costa

Il consumo si misura in token. I numeri sotto sono **misurati** sui nostri giri; il prezzo per token è quello che usiamo nel codice per stimare la spesa (0,042 $ per milione di token), **non** un listino ufficiale: controllate la vostra console TypeSafe.

| Uso | Cosa legge Jev | Domande | Token per chiamata | Chiamate per giro | Token per giro | Stima $ per giro |
|---|---|---|---|---|---|---|
| Notizie ([caso 1](casi/01_notizie.md)) | titolo + altri titoli della storia | 3 | ~470 in + ~65 out | 12 (tetto) | ~6.500 | ~0,0003 |
| Annunci di lavoro ([caso 2](casi/02_annunci_lavoro.md)) | annuncio intero con descrizione | 5 | ~1.550 (max ~3.200) | 85 | 132.312 | ~0,006 |
| Post social ([caso 3](casi/03_post_social.md)) | post di Reddit/X/LinkedIn | 4 | ~800 | 39–125 | 32.000–102.000 | ~0,001–0,004 |

Cosa fa salire il costo, in ordine: **quanti elementi giudicate** (di gran lunga), la lunghezza dello `state`, la lunghezza e il numero delle domande. Per questo tutti e tre i casi scartano, raggruppano e deduplicano *prima* di chiamare Jev (vedi §6).

## 5. Come si scrive una domanda che funziona

Regole ricavate dagli errori veri, non dalla teoria.

1. **Una domanda, un criterio.** Nel radar annunci sono cinque domande separate (lingua, tema AI, collaborazione esterna, competenze, remoto) invece di "è un annuncio adatto a me?". Così un annuncio perfetto ma in presenza lo vedi come *perfetto ma in presenza* (remoto 0,02) e decidi tu cosa farne, invece di vedere solo un 0,4 senza spiegazione.
2. **Dite cosa scartare.** "Reject company news, local administrations and other countries" è la frase che ha affondato "BMO conferma il rating Buy su Southwest Airlines" (0,01). I falsi positivi che la vostra regex fa passare oggi sono esattamente il testo da mettere dopo *Reject*.
3. **Date a Jev i segnali forti che conoscete.** Nel radar la domanda sulla collaborazione esterna dava 0,63 su annunci che erano chiaramente a partita IVA. Aggiunta la frase *"Explicit P.IVA … or Italian 'Contratto di lavoro: Collaborazione' are strong yes signals"*, gli stessi annunci sono saliti a 0,95–0,96. Stessi testi, domanda migliore.
4. **Dite cosa è un no forte, e cosa è solo incertezza.** *"Permanent employment only is a strong no"* e *"If contract type is unspecified, express uncertainty"*: così un annuncio che non dice niente sta intorno a 0,5 invece di finire a caso da una parte.
5. **Giudicare il lavoro, non la persona.** *"Judge the actual work, not whether this applicant meets every credential"*: senza questa frase Jev penalizzava annunci adatti solo perché chiedevano titoli formali. Sullo stesso annuncio la domanda sulle competenze è passata da 0,44 a 0,80.
6. **In inglese.** Tutte le nostre domande sono in inglese, i testi sono in italiano o inglese: funziona e rende stabile.
7. **Nello `state` solo ciò che serve.** Se una domanda riguarda la lingua o il remoto, nello `state` deve esserci la descrizione intera; per un giudizio sul tema di una notizia basta il titolo. Più testo = più token e più rumore.
8. **Cambiata la domanda, cambiano i voti.** Se riusate i voti già dati, buttateli quando cambiate le domande (vedi §6, "Voti riusati").

## 6. Schemi di codice che si ripetono

**Filtro certo prima di Jev.** Regex, finestra temporale, lunghezza minima, autori esclusi, doppioni: tutto ciò che si decide con certezza non costa una chiamata. Casi 1 e 3.

**Una chiamata per elemento, tutte le domande dentro.** Mai una chiamata per domanda.

**Punteggio moltiplicato + soglia per domanda.**

```python
punteggio = v["tema"] * v["fatto"] * (0.5 + v["bonus"] / 2)                        # caso 1
punteggio = v["compratore"] * v["fit"] * max(v["richiesta"], v["non_tecnico"])     # caso 3
tenuto = all(v[d] >= 0.6 for d in OBBLIGATORIE) and punteggio >= SOGLIA
```

Il prodotto fa sì che un "no" netto su una domanda obbligatoria affondi l'elemento. `max(a, b)` dice "basta una delle due". `0.5 + b/2` dice "aiuta, ma senza non si va a zero".

**Fasce invece di sì/no** (caso 2): tutte le obbligatorie ≥ 0,75, poi *verde* se anche il remoto ≥ 0,75, *arancione* se sotto. Chi legge vede subito le certe e quelle da controllare.

**Tetto di chiamate e di spesa.** `--max-jev 12` nel caso 1; `tetto_giro_usd` nel caso 3, dove si somma `usage.input_tokens × prezzo` a ogni giro e ci si ferma al tetto.

**Voti riusati** (caso 2): l'elemento già visto e invariato non si paga di nuovo. Se cambia il testo si rivaluta; se cambiano le domande si riparte da zero, per non mescolare voti dati a domande diverse.

**Memoria di ciò che è già stato giudicato** (caso 3): `seen.json` con URL e contenuto normalizzato, dimenticati dopo 90 giorni. Jev paga solo i post mai visti.

**Errori per elemento, mai per giro.** Un timeout su un elemento si registra (`jev_error`) e si passa al successivo; nel caso 3 con 3 tentativi e attesa crescente. Il giro non si blocca e l'elemento non passa per sbaglio.

**Parallelo con moderazione.** Nel caso 3, 6 chiamate in parallelo (`ThreadPoolExecutor(6)`); limiti di frequenza più alti non li abbiamo misurati.

**Salvare tutto, anche gli scarti.** Tutti e tre i casi scrivono un JSON con ogni elemento e i suoi voti, compresi quelli scartati. È l'unico modo per tarare le soglie: guardate dove cadono gli elementi che avreste tenuto voi.

**Rivalutazione mirata.** Quando cambiate una domanda, non rifate tutto il giro: rivalutate solo gli elementi ambigui e salvate voto vecchio e nuovo affiancati (`rescore_log`). Così vedete se la domanda nuova sposta davvero ciò che volevate spostare.

## 7. Cosa Jev non fa

- **Non cerca.** Giudica ciò che gli date. La raccolta (feed, JobSpy, API social) è vostra.
- **Non verifica i fatti.** Legge lo `state` e basta: se il titolo mente, il voto è sbagliato. Un post di Poltronave ha scritto "Moody's promuove l'Italia" su una semplice conferma del rating; la notizia era in tema e concreta, l'errore era nel verbo, e si prende solo aprendo le fonti.
- **Non è deterministico come una regex.** Lo stesso testo può dare 0,95 una volta e 0,96 un'altra; non costruite logiche che dipendono dalla seconda cifra decimale.
- **Le soglie non sono universali.** 0,6 per le notizie, 0,75 per gli annunci, 0,45–0,55 per i post social: si tarano sui dati di ogni uso.
