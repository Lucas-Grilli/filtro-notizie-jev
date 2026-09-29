#!/usr/bin/env python3
"""Filtro notizie con Jev: dai feed RSS a una classifica corta di storie che valgono.

Pipeline, in quest'ordine (ogni passo costa meno del successivo, quindi si scarta il prima possibile):
  1. raccogli     - legge Google News (ricerche) e feed RSS diretti delle testate
  2. prefiltra    - regex sul titolo: gratis, butta cio' che di sicuro e' fuori tema
  3. raggruppa    - unisce i titoli della stessa storia, cosi' Jev la giudica una volta sola
  4. giudica      - Jev risponde alle domande del config con una probabilita' da 0 a 1
  5. classifica   - punteggio dai voti, soglie, minimo di testate

Uso:
  python filtro_notizie.py --config esempi/conti_pubblici.json            # classifica leggibile
  python filtro_notizie.py --config esempi/conti_pubblici.json --json     # per un altro programma
  python filtro_notizie.py --config esempi/conti_pubblici.json --senza-jev  # solo regex + raggruppamento, nessuna chiave

La chiave va in TYPESAFE_API_KEY (ambiente o file .env accanto a questo script).
Solo libreria standard, Python 3.8+.
"""

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODELLO = "jev-latest"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


# ---------------------------------------------------------------- config e chiave

def carica_config(percorso):
    with open(percorso, encoding="utf-8") as f:
        c = json.load(f)
    c["_tema"] = re.compile(c["prefiltro_regex"], re.I)
    c["_vuote"] = set(c.get("parole_vuote", []))
    return c


def chiave_jev():
    """TYPESAFE_API_KEY dall'ambiente, altrimenti da un .env accanto allo script."""
    chiave = os.getenv("TYPESAFE_API_KEY", "")
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not chiave and os.path.exists(env):
        for riga in open(env, encoding="utf-8"):
            if riga.strip().startswith("TYPESAFE_API_KEY="):
                chiave = riga.split("=", 1)[1].strip().strip('"').strip("'")
    return chiave


# ---------------------------------------------------------------- 1. raccogli

def norm(s):
    """Minuscolo, senza accenti e punteggiatura: serve a confrontare titoli."""
    s = unicodedata.normalize("NFD", html.unescape(s).lower())
    return re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def _leggi_feed(url):
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=25) as r:
        return ET.fromstring(r.read())


def raccogli(config, ore):
    """Tutti i titoli delle ultime `ore` ore, da Google News e dai feed diretti."""
    gn = config.get("google_news", {})
    giorni = max(1, -(-ore // 24))  # Google News ragiona a giorni: si arrotonda per eccesso, poi si taglia per ora
    urls = ["https://news.google.com/rss/search?q={}+when:{}d&hl={}&gl={}&ceid={}:{}".format(
        quote_plus(q), giorni, gn.get("lingua", "it"), gn.get("paese", "IT"), gn.get("paese", "IT"), gn.get("lingua", "it"))
        for q in gn.get("ricerche", [])] + list(config.get("feed_diretti", []))
    testate = config.get("testate", {})
    soglia = datetime.now(timezone.utc) - timedelta(hours=ore)
    out = []
    for url in urls:
        try:
            radice = _leggi_feed(url)
        except Exception as e:
            print("feed non letto: {} ({})".format(url, e), file=sys.stderr)
            continue
        for it in radice.iter("item"):
            titolo = (it.findtext("title") or "").strip()
            fonte = (it.findtext("source") or "").strip()
            # Google News mette la testata in coda al titolo: "Titolo - Testata"
            if " - " in titolo and not fonte:
                titolo, fonte = titolo.rsplit(" - ", 1)
            elif fonte and titolo.endswith(" - " + fonte):
                titolo = titolo[: -len(" - " + fonte)]
            link = it.findtext("link") or ""
            dominio = urlparse(link).netloc.replace("www.", "")
            if dominio and "news.google.com" not in dominio:
                fonte = testate.get(dominio, fonte or dominio)
            fonte = testate.get(fonte.lower().replace("www.", ""), fonte)  # "ansa.it" e "ANSA" sono la stessa testata
            try:
                data = parsedate_to_datetime(it.findtext("pubDate") or "")
            except (TypeError, ValueError):
                continue
            if data.tzinfo is None:
                data = data.replace(tzinfo=timezone.utc)
            if data >= soglia and titolo:
                out.append({"titolo": titolo, "fonte": fonte or "?", "data": data, "link": link})
    return out


# ---------------------------------------------------------------- 2. prefiltra

def prefiltra(items, config):
    """Il filtro certo e gratuito: se il titolo non tocca il tema, Jev non viene pagato per leggerlo."""
    return [it for it in items if config["_tema"].search(it["titolo"])]


# ---------------------------------------------------------------- 3. raggruppa

def raggruppa(items, config):
    """Unisce i titoli della stessa storia (parole in comune). Prima le storie riprese da piu' testate."""
    gruppi = []
    for it in sorted(items, key=lambda x: x["data"]):
        parole = {w for w in norm(it["titolo"]).split() if len(w) > 3 or w.isdigit()} - config["_vuote"]
        if not parole:
            continue
        for g in gruppi:
            comuni = parole & g["parole"]
            if len(comuni) >= 3 and len(comuni) / min(len(parole), len(g["parole"])) >= 0.5:
                # si confronta sempre col primo titolo del gruppo: allargarlo a ogni aggiunta lo fa inghiottire tutto
                g["voci"].append(it)
                break
        else:
            gruppi.append({"parole": parole, "voci": [it]})
    for g in gruppi:
        g["fonti"] = sorted({v["fonte"] for v in g["voci"]})
        g["titolo"] = g["voci"][-1]["titolo"]
        g["ultima"] = g["voci"][-1]["data"]
    return sorted(gruppi, key=lambda g: (len(g["fonti"]), g["ultima"]), reverse=True)


# ---------------------------------------------------------------- 4. giudica (Jev)

def chiedi_a_jev(state, domande, chiave, timeout=35):
    """Chiamata generica a Jev. `domande` = {nome: testo della domanda si/no}. Torna {nome: probabilita' 0-1}.

    Una sola chiamata risponde a tutte le domande sullo stesso `state`.
    """
    payload = {"model": JEV_MODELLO, "state": state,
               "questions": {k: {"type": "noul", "instructions": v} for k, v in domande.items()}}
    req = Request(JEV_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
                  headers={"Authorization": "Bearer " + chiave, "Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        risposta = json.load(r)
    valori = risposta.get("answers", {})
    return {k: round(float(valori.get(k, {}).get("noul", 0)), 2) for k in domande}


def stato_storia(storia):
    """Il testo che Jev legge: titolo, altri titoli della stessa storia, testate, data."""
    return "Headline: {}\nOther headlines on the same story: {}\nOutlets: {}\nDate: {}".format(
        storia["titolo"], " | ".join(v["titolo"] for v in storia["voci"][:-1][-4:]),
        ", ".join(storia["fonti"]), storia["ultima"].date().isoformat())


def gia_coperta(titolo, gia_pubblicati, chiave):
    """Facoltativo: Jev dice se la notizia e' gia' raccontata da un tuo contenuto uscito (stesso evento o cifra,
    non solo stesso tema). Una regex qui non funziona: due titoli sullo stesso fatto non condividono le parole."""
    if not gia_pubblicati:
        return False
    state = "News headline: {}\nAlready published:\n{}".format(titolo, "\n".join("- " + t for t in gia_pubblicati))
    domanda = {"gia_coperta": "Does one of the already published items already cover this same news event or the "
                              "same official figure? Answer yes only for the same event or number, not for the same "
                              "broad topic."}
    return chiedi_a_jev(state, domanda, chiave)["gia_coperta"] >= 0.5


# ---------------------------------------------------------------- 5. classifica

def punteggio(voti, config):
    """Prodotto delle domande obbligatorie, ognuna bonus pesa tra 0,5 e 1 (senza bonus la storia vale la meta')."""
    p = 1.0
    for nome, d in config["domande"].items():
        p *= voti[nome] if d.get("ruolo", "obbligatoria") == "obbligatoria" else 0.5 + voti[nome] / 2
    return round(p, 2)


def e_forte(storia, config):
    """Criterio d'ingresso: ogni obbligatoria sopra la sua soglia e almeno N testate diverse."""
    ok = all(storia["jev"][nome] >= d.get("soglia", 0.6)
             for nome, d in config["domande"].items() if d.get("ruolo", "obbligatoria") == "obbligatoria")
    return ok and len(storia["fonti"]) >= config.get("min_testate", 2)


def filtra(config, ore=30, max_jev=12, chiave=None):
    """L'intera pipeline. Torna (storie valutate ordinate per punteggio, statistiche)."""
    grezzi = raccogli(config, ore)
    sul_tema = prefiltra(grezzi, config)
    gruppi = raggruppa(sul_tema, config)
    stat = {"titoli_letti": len(grezzi), "passano_regex": len(sul_tema), "storie": len(gruppi), "valutate_da_jev": 0}
    if not chiave:
        return gruppi, stat
    domande = {k: d["domanda"] for k, d in config["domande"].items()}
    valutate = []
    for g in gruppi[:max_jev]:
        try:
            g["jev"] = chiedi_a_jev(stato_storia(g), domande, chiave)
        except Exception as e:
            print("Jev non ha risposto su: {} ({})".format(g["titolo"], e), file=sys.stderr)
            continue
        g["punteggio"] = punteggio(g["jev"], config)
        g["forte"] = e_forte(g, config)
        valutate.append(g)
    stat["valutate_da_jev"] = len(valutate)
    stat["forti"] = sum(1 for g in valutate if g["forte"])
    return sorted(valutate, key=lambda g: g["punteggio"], reverse=True), stat


def in_json(storia):
    diretti = [v["link"] for v in storia["voci"] if "news.google.com" not in v["link"]]
    return {"titolo": storia["titolo"], "testate": storia["fonti"], "ultima": storia["ultima"].isoformat(),
            "punteggio": storia.get("punteggio"), "forte": storia.get("forte"), "jev": storia.get("jev"),
            "altri_titoli": [v["titolo"] for v in storia["voci"][:-1]][-3:],
            "link": diretti[-2:] or [storia["voci"][-1]["link"]]}


# ---------------------------------------------------------------- CLI

def main():
    a = argparse.ArgumentParser(description="Filtro notizie con Jev")
    a.add_argument("--config", required=True, help="file JSON del tema, v. esempi/")
    a.add_argument("--ore", type=int, default=30, help="finestra in ore (default 30)")
    a.add_argument("--max-jev", type=int, default=12, help="tetto di chiamate a Jev, una per storia (default 12)")
    a.add_argument("--mostra", type=int, default=8, help="quante storie stampare (default 8)")
    a.add_argument("--json", action="store_true", help="output JSON per un altro programma")
    a.add_argument("--senza-jev", action="store_true", help="solo regex e raggruppamento, nessuna chiave")
    args = a.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # accenti leggibili anche nel terminale di Windows

    config = carica_config(args.config)
    chiave = None if args.senza_jev else chiave_jev()
    if not args.senza_jev and not chiave:
        sys.exit("TYPESAFE_API_KEY mancante: mettila nell'ambiente o in .env (v. .env.example), oppure usa --senza-jev")

    storie, stat = filtra(config, args.ore, args.max_jev, chiave)
    print("# titoli letti {titoli_letti} -> passano la regex {passano_regex} -> storie {storie} -> valutate da Jev "
          "{valutate_da_jev}".format(**stat), file=sys.stderr)

    if args.json:
        print(json.dumps([in_json(g) for g in storie[: args.mostra]], ensure_ascii=False, indent=1))
        return
    for g in storie[: args.mostra]:
        testa = "{:.2f} {}".format(g["punteggio"], "FORTE" if g["forte"] else "     ") if "jev" in g else "  -  "
        print("{}  {}  [{} testate: {}]  {}".format(
            testa, g["ultima"].strftime("%d/%m %H:%M"), len(g["fonti"]), ", ".join(g["fonti"][:4]), g["titolo"]))
        if "jev" in g:
            print("      " + ", ".join("{} {}".format(k, v) for k, v in g["jev"].items()))
        print("      " + in_json(g)["link"][-1][:160])


if __name__ == "__main__":
    main()
