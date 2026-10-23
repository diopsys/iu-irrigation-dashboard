"""Eigenen Abschnitt „irrigation_unlimited:“ in configuration.yaml finden und
auskommentieren.

Rein zeilenweise (kein YAML-Laden und -Schreiben), damit Kommentare,
!include, !secret und Formatierung der übrigen Datei unverändert bleiben.
Der Abschnitt beginnt mit „irrigation_unlimited:“ ganz links und endet vor
der nächsten Zeile, die wieder ganz links beginnt (Kommentare ganz links
gehören nur dazu, wenn danach noch eingerückte Zeilen des Abschnitts folgen).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

_START_RE = re.compile(r"^﻿?irrigation_unlimited\s*:")
MARKE = "# IU Irrigation Dashboard:"


def _leer(zeile: str) -> bool:
    return not zeile.strip()


def _eingerueckt(zeile: str) -> bool:
    return zeile[:1] in (" ", "\t")


def iu_abschnitt(text: str) -> tuple[int, int] | None:
    """Zeilenbereich [von, bis) des Abschnitts (0-basiert) oder None."""
    zeilen = text.splitlines()
    von = next((i for i, z in enumerate(zeilen) if _START_RE.match(z)), None)
    if von is None:
        return None
    bis = von + 1
    for i in range(von + 1, len(zeilen)):
        z = zeilen[i]
        if _eingerueckt(z) and not _leer(z):
            bis = i + 1
        elif not (_leer(z) or z.startswith("#")):
            break
    return von, bis


def auszug(text: str, bereich: tuple[int, int], rand: int = 3) -> str:
    """Anfang und Ende des Abschnitts mit Zeilennummern (für die Anzeige)."""
    zeilen = text.splitlines()
    von, bis = bereich
    nummern = list(range(von, bis))
    if len(nummern) > 2 * rand + 1:
        nummern = nummern[:rand] + [None] + nummern[-rand:]
    breite = len(str(bis))
    return "\n".join("…" if i is None else f"{i + 1:>{breite}}  {zeilen[i]}" for i in nummern)


def auskommentieren(text: str, bereich: tuple[int, int], hinweis: str) -> str:
    """Abschnitt mit „# “ versehen, Hinweiszeile davor; Zeilenenden bleiben."""
    zeilen = text.splitlines(keepends=True)
    von, bis = bereich
    ende = "\r\n" if zeilen[von].endswith("\r\n") else "\n"
    neu = [f"{MARKE} {hinweis}{ende}"]
    for z in zeilen[von:bis]:
        inhalt = z.rstrip("\r\n")
        neu.append(z if _leer(inhalt) else "# " + inhalt.lstrip("﻿") + z[len(inhalt):])
    if not neu[-1].endswith(("\n", "\r")):
        neu[-1] += ende
    return "".join(zeilen[:von] + neu + zeilen[bis:])


def finden(pfad: Path) -> tuple[str, tuple[int, int]] | None:
    """Text und Bereich des Abschnitts in der Datei. (Im Executor aufrufen.)"""
    try:
        # newline="": Zeilenenden nicht umwandeln (CRLF bleibt beim Zurückschreiben)
        with pfad.open(encoding="utf-8", newline="") as datei:
            text = datei.read()
    except OSError:
        return None
    bereich = iu_abschnitt(text)
    return (text, bereich) if bereich else None


def beheben(pfad: Path, erwartet: str | None = None) -> tuple[Path, tuple[int, int]] | None:
    """Sicherung anlegen und den Abschnitt auskommentieren. Mit „erwartet“
    (Auszug aus der Anzeige) nur, wenn sich der Abschnitt seither nicht
    geändert hat. Gibt Sicherungsdatei und Bereich zurück. (Im Executor.)"""
    gefunden = finden(pfad)
    if not gefunden:
        return None
    text, bereich = gefunden
    if erwartet is not None and auszug(text, bereich) != erwartet:
        return None
    zeit = datetime.now().strftime("%Y%m%d-%H%M%S")
    sicherung = pfad.with_name(f"{pfad.name}.iu_backup_{zeit}")
    neu = auskommentieren(text, bereich, f"commented out {zeit}, backup {sicherung.name}")
    if iu_abschnitt(neu) is not None:
        return None
    sicherung.write_bytes(pfad.read_bytes())
    # newline="" schreibt die Zeilenenden so, wie sie im Text stehen
    with pfad.open("w", encoding="utf-8", newline="") as datei:
        datei.write(neu)
    return sicherung, bereich
