<h1 align="center">Filtro notizie con Jev</h1>

<p align="center"><b>Dai feed RSS a una classifica corta delle notizie che ti servono davvero: la regex scarta il sicuramente fuori tema, Jev giudica il resto come farebbe una persona.</b></p>

<p align="center">Non un'altra regex più lunga: è la regex che avete già, più un giudice che capisce il significato del titolo.</p>

<p align="center">
  <img alt="Licenza" src="https://img.shields.io/badge/licenza-MIT-blue.svg">
  <img alt="Stato" src="https://img.shields.io/badge/stato-in%20produzione%20su%20Poltronave-brightgreen.svg">
</p>

<p align="center">
  <a href="#il-problema">Il problema</a> ·
  <a href="#regex-contro-jev-la-differenza">Regex contro Jev</a> ·
  <a href="#come-funziona">Come funziona</a> ·
  <a href="#provarlo-in-5-minuti">Provarlo</a> ·
  <a href="#integrarlo-nel-vostro-codice">Integrarlo</a> ·
  <a href="#adattarlo-al-vostro-tema">Adattarlo</a> ·
  <a href="#scelte-di-progetto">Scelte</a> ·
  <a href="#limiti">Limiti</a> ·
  <a href="#usarlo-con-unai">Usarlo con un'AI</a>
</p>

> È il motore che sceglie le notizie per [Poltronave](https://poltronave.it) (post quotidiano su X e articolo settimanale del blog), estratto e reso configurabile per qualsiasi tema.

---

## Il problema

Se filtrate le notizie con una regex, ve ne accorgete presto: una regex controlla **se una parola c'è**, non **di cosa parla** il titolo. Ne escono due errori opposti:

- **passano cose fuori tema** perché contengono la parola giusta nel senso sbagliato;
- **passano cose in tema ma inutili**: opinioni, interviste, "potrebbe", "si valuta", che contengono tutte le parole giuste ma non sono un fatto.

Allungare la regex non li risolve. Per il primo errore aggiungete eccezioni che rompono altri casi; per il secondo una regex non ha proprio gli strumenti, perché "è un fatto o un'opinione?" non è una questione di parole.

Questo motore tiene la regex (è gratis ed è ottima per scartare il sicuramente fuori tema) e aggiunge dopo un secondo passo: **Jev**, un modello che risponde a domande sì/no su un testo con una probabilità da 0 a 1.

## Regex contro Jev: la differenza

Esempi veri, dal giro del 29/09/2026 sulla configurazione "conti pubblici". Tutti questi titoli **passano la regex**:

| Titolo | Parola che ha fatto passare la regex | Cosa dice Jev | Esito |
|---|---|---|---|
| Southwest Airlines Co.: BMO Capital conferma il rating Buy | `rating` | conti pubblici **0,01** | scartata: è il rating di un'azienda americana, non dello Stato |
| TPL Linea – nuova manovra tariffaria per gli abbonamenti studenti | `manovra` | conti pubblici **0,03** | scartata: è una manovra sulle tariffe di un'azienda di trasporti locale |
| Caro carburanti, Di Paola: «I fondi della manovra vadano a famiglie e imprese» | `manovra` | fatto concreto **0,08** | scartata: in tema, ma è una dichiarazione, non una decisione |
| Calendario aste titoli di Stato ottobre 2026: Bot, Btp e Ccteu | `btp` | fatto concreto 0,39 | sotto soglia: in tema, ma è un calendario, non una notizia |
| Spread Btp-Bund risale a 94 punti | `spread` | conti pubblici 0,98 · fatto 0,62 · cifra 0,86 | **tenuta**, ripresa da 2+ testate |
| Rialzo spread Btp-Bund e variazione rendimenti a settembre | `spread` | conti pubblici 0,98 · fatto 0,77 · cifra 0,83 | **tenuta**, prima in classifica (8 testate) |

Quel giro: **379 titoli letti → 252 passano la regex → 158 storie → 12 giudicate da Jev → 4 "forti"**. Senza Jev, le 252 arrivano tutte a valle (a voi, o a un modello che scrive).

In sintesi:

| | Solo regex | Regex + Jev |
|---|---|---|
| Cosa controlla | se una parola compare | cosa significa il titolo, rispetto a una domanda scritta in italiano o inglese |
| Omonimi ("rating" di un'azienda, "manovra" tariffaria) | passano | scartati |
| Fatto contro opinione | non distinguibili | una domanda apposta (`fatto_concreto`) |
| Ordine dei risultati | nessuno, o per data | punteggio da 0 a 1 |
| Cambiare criterio | riscrivere la regex e sperare | riscrivere una frase |
| Costo | zero | una chiamata API per storia (non per titolo) |
| Determinismo | totale | probabilità: vanno lette come "dove guardare", non come prove |

Il beneficio misurato su Poltronave: dopo, a valle c'è un modello (Claude/Nemotron) che scrive il post. Passargli la classifica corta invece dei feed interi ha portato il giro **da circa 80 richieste e 11 milioni di token a meno di 60 richieste e circa 4 milioni** (27/09/2026). Se a valle ci siete voi e non un modello, il guadagno è in tempo di lettura.

---

## Come funziona

```
 Google News (ricerche)  +  feed RSS delle testate
                 │
                 ▼
 1. RACCOGLI     tutti i titoli delle ultime N ore                    379 titoli
                 │
                 ▼
 2. PREFILTRA    regex sul titolo — gratis, butta il sicuro fuori tema 252
                 │
                 ▼
 3. RAGGRUPPA    titoli della stessa storia insieme (parole in comune) 158 storie
                 │  prima le storie riprese da più testate
                 ▼
 4. GIUDICA      Jev: 3 domande sì/no per storia, una sola chiamata    12 giudicate
                 │  (solo le prime --max-jev storie: tetto di spesa)
                 ▼
 5. CLASSIFICA   punteggio dai voti + soglie + minimo di testate       4 forti
```

Ogni passo costa più del precedente, quindi si scarta il prima possibile: la regex non costa niente e toglie un terzo dei titoli; il raggruppamento fa sì che Jev giudichi una storia una volta sola anche se la riportano otto testate.

**Le domande a Jev** (configurazione conti pubblici):

| Nome | Ruolo | Domanda, in breve |
|---|---|---|
| `conti_pubblici` | obbligatoria, soglia 0,6 | riguarda i conti pubblici italiani? (non aziende, non enti locali, non altri paesi) |
| `fatto_concreto` | obbligatoria, soglia 0,6 | è un fatto verificabile (dato ufficiale, misura approvata, decisione di rating)? non opinioni, interviste, voci |
| `cifra_verificabile` | bonus | c'è una cifra controllabile su una fonte primaria? |

**Il punteggio**: prodotto delle obbligatorie × (0,5 + bonus/2). Esempio: 0,98 × 0,77 × (0,5 + 0,83/2) = 0,69. Una storia senza la cifra non va a zero, vale la metà.

**"Forte"** vuol dire: tutte le obbligatorie sopra soglia **e** almeno 2 testate diverse. Il secondo vincolo è una regola editoriale di Poltronave (un fatto si pubblica solo se confermato da due fonti indipendenti) e si cambia nel config (`min_testate`).

### Cos'è Jev

Jev è un modello di [TypeSafe](https://api.typesafe.ai/docs) fatto per una cosa sola: rispondere a domande su un testo con un numero, non con una frase. Gli mandate:

```json
{
  "model": "jev-latest",
  "state": "Headline: Spread Btp-Bund risale a 94 punti\nOutlets: ANSA, SoldiOnline.it\nDate: 2026-09-28",
  "questions": {
    "conti_pubblici": {"type": "noul", "instructions": "Does this news item concern Italian national public finances? ..."},
    "fatto_concreto": {"type": "noul", "instructions": "Is this a concrete, verifiable event? ..."}
  }
}
```

e risponde (token d'esempio):

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "conti_pubblici": {"type": "noul", "noul": 0.98},
    "fatto_concreto": {"type": "noul", "noul": 0.62}
  },
  "usage": {"input_tokens": 180, "output_tokens": 6}
}
```

`noul` è il tipo "sì/no": il numero è la probabilità del sì. Nessun testo da interpretare, nessun "Certo! Ecco la mia analisi...": un numero per domanda, che si confronta con una soglia come qualsiasi altro numero. È questo che lo rende comodo dentro un programma rispetto a un chatbot generico. L'API ha anche domande a scelta multipla (`choice`) e a punteggio su scala (`score`); qui usiamo solo `noul`.

---

## Provarlo in 5 minuti

Serve Python 3.8+. Nessuna libreria da installare: solo libreria standard.

```bash
git clone https://github.com/Lucas-Grilli/filtro-notizie-jev.git
cd filtro-notizie-jev
```

**Senza chiave** (solo regex e raggruppamento — è più o meno quello che fate già):

```bash
python filtro_notizie.py --config esempi/conti_pubblici.json --senza-jev
```

**Con Jev**: copiate `.env.example` in `.env` e metteteci la chiave (`TYPESAFE_API_KEY=...`). Ognuno usa la propria chiave Jev: si crea un account su [console.typesafe.ai](https://console.typesafe.ai/) e si genera lì. Poi:

```bash
python filtro_notizie.py --config esempi/conti_pubblici.json
```

Lanciate i due comandi uno dopo l'altro e confrontate: è il modo più rapido per vedere la differenza sul vostro tema.

Opzioni:

| Opzione | Default | Cosa fa |
|---|---|---|
| `--config` | — | il file del tema (obbligatorio) |
| `--ore` | 30 | finestra temporale |
| `--max-jev` | 12 | tetto di chiamate a Jev per giro (una per storia): è il vostro tetto di spesa |
| `--mostra` | 8 | quante storie stampare |
| `--json` | — | output JSON, per passarlo a un altro programma |
| `--senza-jev` | — | salta Jev, nessuna chiave richiesta |

Il riepilogo `# titoli letti … -> passano la regex … -> storie … -> valutate da Jev …` esce su stderr, così `--json > out.json` resta JSON pulito.

---

## Integrarlo nel vostro codice

Tre livelli, dal più leggero. **Partite dal primo.**

### Livello 1 — tenete tutto com'è, aggiungete Jev dopo la vostra regex

Vi serve una sola funzione, `chiedi_a_jev`. Copiatela o importatela:

```python
from filtro_notizie import chiedi_a_jev, chiave_jev

DOMANDE = {
    "in_tema": "Does this news item concern <il vostro tema>? Reject <cosa gli somiglia ma non lo è>.",
    "fatto_concreto": "Is this a concrete, verifiable event? Reject opinions, interviews, rumors.",
}

chiave = chiave_jev()
for notizia in notizie_che_passano_la_vostra_regex:          # il vostro codice di oggi
    voti = chiedi_a_jev("Headline: " + notizia["titolo"], DOMANDE, chiave)
    if voti["in_tema"] >= 0.6 and voti["fatto_concreto"] >= 0.6:
        tenute.append(notizia)
```

Una chiamata per notizia, tutte le domande dentro la stessa chiamata. Se avete tante notizie simili, passate al livello 2 per raggrupparle prima.

### Livello 2 — usate i pezzi che vi servono

Ogni passo è una funzione separata, si prende singolarmente:

| Funzione | Entra | Esce |
|---|---|---|
| `carica_config(percorso)` | file JSON | config con la regex già compilata |
| `raccogli(config, ore)` | config | lista di `{titolo, fonte, data, link}` |
| `prefiltra(items, config)` | lista | lista più corta |
| `raggruppa(items, config)` | lista | storie `{titolo, fonti, voci, ultima}`, ordinate per numero di testate |
| `chiedi_a_jev(state, domande, chiave)` | testo + `{nome: domanda}` | `{nome: probabilità}` |
| `stato_storia(storia)` | storia | il testo che Jev legge |
| `punteggio(voti, config)` / `e_forte(storia, config)` | voti | numero / sì-no |
| `gia_coperta(titolo, gia_pubblicati, chiave)` | titolo + i vostri titoli usciti | `True` se l'avete già raccontata |

Esempio: avete già il vostro lettore di feed, volete solo raggruppamento + Jev:

```python
import filtro_notizie as fn

config = fn.carica_config("esempi/mio_tema.json")
items = [{"titolo": t, "fonte": f, "data": d, "link": l} for (t, f, d, l) in i_vostri_titoli]  # data: datetime con fuso
storie = fn.raggruppa(fn.prefiltra(items, config), config)
domande = {k: d["domanda"] for k, d in config["domande"].items()}
for s in storie[:12]:
    s["jev"] = fn.chiedi_a_jev(fn.stato_storia(s), domande, fn.chiave_jev())
    s["punteggio"] = fn.punteggio(s["jev"], config)
```

### Livello 3 — tutto il giro, da un altro programma

```bash
python filtro_notizie.py --config esempi/mio_tema.json --json > classifica.json
```

oppure in Python `storie, stat = fn.filtra(config, ore=30, max_jev=12, chiave=fn.chiave_jev())`. Su Poltronave gira così su una VPS, lanciato da un timer di systemd ogni giorno alle 13:00.

### Il doppione: già scritta?

`gia_coperta` risolve un problema che con la regex non si risolve: "questa notizia l'abbiamo già raccontata?". Due titoli sullo stesso fatto spesso non condividono nessuna parola ("Deficit al 3,1%" / "Conti pubblici, il disavanzo sfora il target"). Si passa a Jev il titolo nuovo e l'elenco dei vostri titoli usciti: risponde sì solo se è lo stesso evento o la stessa cifra, non lo stesso tema generico. Su Poltronave è stata aggiunta il 27/09, quando il giro del blog stava per riscrivere l'articolo sul deficit al 3,1% già uscito.

---

## Adattarlo al vostro tema

Il codice non contiene niente di specifico: tutto il tema vive in un file JSON. Copiate `esempi/modello.json` e compilate:

| Campo | Cosa ci va | Consiglio |
|---|---|---|
| `google_news.ricerche` | ricerche in sintassi Google (`OR`, virgolette) | 3-6 ricerche, larghe: il filtro stretto lo fa Jev |
| `feed_diretti` | RSS delle testate | i link di Google News sono impacchettati e non si aprono da script; quelli diretti portano all'articolo vero |
| `testate` | dominio → nome | unifica "ansa.it" e "ANSA" nel conteggio delle testate |
| `prefiltro_regex` | la vostra regex di oggi | **larga**: deve solo buttare il sicuro fuori tema. Se esclude qualcosa di buono, Jev non lo vedrà mai |
| `parole_vuote` | parole che tutti i titoli del tema condividono | senza, tutte le notizie del tema finiscono nella stessa "storia" |
| `domande` | nome → `ruolo` (`obbligatoria`/`bonus`), `soglia`, `domanda` | vedi sotto |
| `min_testate` | quante testate diverse servono per "forte" | 1 se vi basta una fonte |

**Come scrivere una buona domanda a Jev** (è la parte che conta di più):

1. **Una domanda, un criterio.** "È in tema *e* è un fatto?" si divide in due domande: così vedete quale delle due ha fallito e mettete soglie diverse.
2. **Dite cosa scartare, non solo cosa tenere.** "Reject company news, local administrations and other countries" è ciò che ha buttato il rating di Southwest Airlines. I casi-trappola che la vostra regex fa passare oggi sono esattamente le frasi da mettere dopo "Reject".
3. **In inglese** rende in modo più stabile (le domande di Poltronave sono in inglese, i titoli in italiano: funziona).
4. **Tarate le soglie sui dati, non a occhio**: fate un giro con `--mostra 30`, guardate dove cadono le notizie che avreste tenuto voi, spostate la soglia lì. 0,6 è il punto di partenza di Poltronave, non una costante.

---

## Scelte di progetto

- **La regex resta, davanti.** È gratis e deterministica: tutto ciò che si può scartare con certezza non deve costare una chiamata. Jev serve per ciò che una regex non sa decidere.
- **Jev giudica storie, non titoli.** Otto testate sullo stesso fatto sono una chiamata, non otto. E il numero di testate diventa un segnale in più (una storia ripresa da tanti è più probabilmente vera e rilevante).
- **Domande separate, punteggio moltiplicato.** Con la moltiplicazione basta un "no" netto su una domanda obbligatoria per affondare la storia: un fatto concretissimo ma fuori tema vale zero, come deve.
- **Un tetto esplicito di chiamate (`--max-jev`).** Il costo per giro è limitato per costruzione, non dipende da quante notizie escono quel giorno.
- **Probabilità, non verdetti.** Il motore produce una classifica e un'etichetta "forte"; decidere resta a valle (a voi, o a un passaggio che apre gli articoli e verifica i fatti).
- **Solo libreria standard.** Niente `pip install`: si copia il file dove serve e funziona.

## Limiti

- **Jev legge solo il titolo** (più gli altri titoli della stessa storia). Non apre l'articolo: se il titolo è fuorviante, il voto lo sarà.
- **Controlla il tema, non i verbi.** Esempio reale di Poltronave: un post ha scritto "Moody's promuove l'Italia" quando Moody's aveva solo confermato il rating. La notizia era giustamente in tema e concreta; l'errore stava nel verbo, e i fatti si verificano aprendo le fonti, non con Jev.
- **Il raggruppamento è a parole in comune**, non a significato: due titoli sullo stesso fatto scritti in modo molto diverso restano storie separate. Di solito non è grave (le giudica entrambe), ma costa una chiamata in più.
- **Google News RSS** non è un'API ufficiale: può cambiare formato o rallentare. I feed diretti delle testate sono più stabili.
- **Costo di Jev**: TypeSafe non pubblica un listino nella documentazione dell'API; ogni risposta riporta i token usati (`usage`). Su Poltronave il giro quotidiano fa al massimo 12 chiamate da poche centinaia di token l'una. Controllate il consumo nella vostra console TypeSafe prima di alzare `--max-jev`.

## Usarlo con un'AI

Se usate un assistente di programmazione (Claude Code, Cursor, Copilot, ChatGPT), c'è [AGENTS.md](AGENTS.md): istruzioni scritte per un'AI, con il contratto delle funzioni, i vincoli da non rompere e i passi per integrare il motore nel vostro codice. Basta dirgli:

> Leggi AGENTS.md e integra il filtro Jev nel nostro codice, dopo la regex che già usiamo in `<vostro file>`.

L'AI legge il file e sa cosa fare; voi controllate il diff. Se non l'avete mai fatto: è il modo più rapido per avere un primo pezzo funzionante da rivedere, invece di partire da zero.

## File

```
filtro_notizie.py        il motore: pipeline + CLI, un solo file
esempi/conti_pubblici.json  configurazione reale di Poltronave
esempi/modello.json      da copiare per il vostro tema
.env.example             dove va la chiave (copiare in .env)
AGENTS.md                istruzioni per assistenti AI
```

## Contatto

Domande, errori, un tema che non torna: aprite una [issue](https://github.com/Lucas-Grilli/filtro-notizie-jev/issues).

## Licenza

MIT, v. [LICENSE](LICENSE).
