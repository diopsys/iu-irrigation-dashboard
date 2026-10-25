"""Smarte Laufzeit je Zone (experimentell, Schalter smart.aktiv).

Ohne den Schalter bleibt alles wie bisher. Mit ihm rechnet jede Zone mit
eigenem Pflanzenfaktor und Bodenspeicher S und bekommt eine Laufzeit in
Minuten statt eines Faktors. Bodenmodell wie FAO-56: Bilanz B = 0 ist der
volle Boden (Feldkapazität), mehr versickert; das Defizit D = −B zählt ab
voll und kann höchstens S erreichen (mehr hält der Boden nicht):

    Bilanz täglich:         B ← clamp(B + wirksam × Regen − Kc × ET₀, −S, 0)
    Bedarf = D − wirksam × Regen(heute + Prognose)   (was nach dem Regen fehlt)
    Gießweise „bedarf“:     läuft, sobald Bedarf > 0
    Gießweise „schwelle“:   läuft erst ab D ≥ Schwelle % × S und füllt bis voll auf
    Minuten = Bedarf ÷ Beregnungsleistung (mm/h) × 60, höchstens max_min
    Durchgänge = ⌈Minuten ÷ durchgang_min⌉ (Aufteilen), höchstens MAX_DURCHGAENGE

Beregnungsleistung je nach Quelle: von Hand (mm/h), aus Durchfluss (L/min)
und Fläche (m²) oder gemessen mit dem Wasserzähler (Median der letzten
Läufe in L/min ÷ Fläche); ohne Angabe die Referenzmenge der Standardlaufzeit.

Reine Berechnung ohne Home Assistant, damit sie auch in tests/ läuft.
"""

from __future__ import annotations

import math
from statistics import median
from typing import Any

MAX_DURCHGAENGE = 4
MESSUNGEN_MAX = 5     # letzte Läufe für den Median
MESSUNGEN_MIN = 3     # ab so vielen Läufen gilt die Messung

# Voreinstellungen je Zonentyp (Kc, Bodenspeicher mm, Gießweise, Schwelle %)
ZONENTYPEN: dict[str, dict[str, Any] | None] = {
    "benutzerdefiniert": None,
    "rasen": {"kc": 0.8, "speicher_mm": 20.0, "giessweise": "schwelle", "schwelle_prozent": 50},
    "beet": {"kc": 0.6, "speicher_mm": 15.0, "giessweise": "schwelle", "schwelle_prozent": 50},
    "hecke": {"kc": 0.5, "speicher_mm": 30.0, "giessweise": "schwelle", "schwelle_prozent": 60},
    "gemuese": {"kc": 1.0, "speicher_mm": 10.0, "giessweise": "bedarf", "schwelle_prozent": 30},
}


def aktiv(daten: dict[str, Any]) -> bool:
    return bool((daten.get("smart") or {}).get("aktiv"))


def speicher(zone: dict[str, Any], wetter: dict[str, Any]) -> float:
    """Bodenspeicher der Zone in mm (sonst der allgemeine)."""
    s = zone["smart"]["speicher_mm"]
    return float(s if s is not None else wetter["speicher_mm"])


def durchfluss_gemessen(messungen: list[float] | None) -> float | None:
    """Median der letzten Messungen in L/min, erst ab MESSUNGEN_MIN Läufen."""
    werte = [m for m in (messungen or [])[-MESSUNGEN_MAX:] if m and m > 0]
    return median(werte) if len(werte) >= MESSUNGEN_MIN else None


def leistung(zone: dict[str, Any], messungen: list[float] | None) -> tuple[float | None, str]:
    """Beregnungsleistung in mm/h und woher sie stammt (zaehler, durchfluss,
    hand oder keine)."""
    sm = zone["smart"]
    flaeche = sm["flaeche_m2"]
    if sm["leistung_quelle"] == "zaehler" and flaeche:
        gemessen = durchfluss_gemessen(messungen)
        if gemessen:
            return gemessen * 60 / flaeche, "zaehler"
    if sm["leistung_quelle"] in ("durchfluss", "zaehler") and sm["durchfluss_l_min"] and flaeche:
        return sm["durchfluss_l_min"] * 60 / flaeche, "durchfluss"
    if zone.get("leistung_mm_h"):
        return float(zone["leistung_mm_h"]), "hand"
    return None, "keine"


def durchgaenge_max(zone: dict[str, Any]) -> int:
    """Höchste Zahl an Durchgängen der Zone (für die IU-Sequenz)."""
    sm = zone["smart"]
    if not sm["aufteilen"]:
        return 1
    return max(1, min(MAX_DURCHGAENGE, math.ceil(sm["max_min"] / max(1, sm["durchgang_min"]))))


def bilanz_begrenzen(bilanz: float, zone: dict[str, Any], wetter: dict[str, Any]) -> float:
    """Bilanz zwischen −S (Boden leer) und 0 (Boden voll, mehr versickert)."""
    return max(-speicher(zone, wetter), min(0.0, bilanz))


def planen(zone: dict[str, Any], bilanz: float, regen_mm: float, regnet: bool,
           wetter: dict[str, Any], messungen: list[float] | None = None) -> dict[str, Any]:
    """Laufzeit einer Zone für den nächsten Lauf.

    regen_mm: Regen heute + Prognose (noch ohne „wirksam“)."""
    sm = zone["smart"]
    s = speicher(zone, wetter)
    kc = sm["kc"]
    wirksam = wetter["regen_wirksam"] / 100
    regen = wirksam * regen_mm if zone["regen"] else 0.0
    defizit = -bilanz_begrenzen(bilanz, zone, wetter)
    schwelle = s * sm["schwelle_prozent"] / 100 if sm["giessweise"] == "schwelle" else 0.0
    bedarf = defizit - regen
    l, quelle = leistung(zone, messungen)
    if l is None:
        # ohne Angabe: Referenzmenge in der Standardlaufzeit
        l = wetter["referenz_mm"] / max(1, zone["standard_min"]) * 60
        quelle = "referenz"

    minuten = 0.0
    if zone["regen"] and regnet:
        grund = "regnet"
    elif defizit <= 0 or defizit < schwelle:
        grund = "unter_schwelle" if schwelle else "kein_bedarf"
    elif bedarf <= 0 or bedarf < schwelle:
        grund = "regen_deckt"
    else:
        minuten = bedarf / l * 60
        grund = "laeuft"
        if minuten > sm["max_min"]:
            minuten, grund = float(sm["max_min"]), "begrenzt"
    n = 0
    if minuten > 0:
        n = min(durchgaenge_max(zone), math.ceil(minuten / max(1, sm["durchgang_min"]))) if sm["aufteilen"] else 1
    mm = minuten * l / 60
    flaeche = sm["flaeche_m2"]
    return {
        "smart": True, "kc": kc, "speicher": round(s, 1), "bilanz": round(bilanz, 1), "defizit": round(defizit, 1),
        "schwelle": round(schwelle, 1), "bedarf": round(bedarf, 1), "leistung": round(l, 2), "quelle": quelle,
        "minuten": round(minuten, 1), "durchgaenge": n, "mm": round(mm, 1),
        "liter": round(mm * flaeche) if flaeche else None, "grund": grund,
        # wie bisher: Faktor bezogen auf die Standardlaufzeit
        "faktor": round(minuten / max(1, zone["standard_min"]), 2),
        "referenz": round(l * zone["standard_min"] / 60, 1),
    }


def gutschrift_mm(zone: dict[str, Any], minuten: float, wetter: dict[str, Any],
                  messungen: list[float] | None = None) -> float:
    """Wassermenge eines Laufs ohne Zählermessung (Minuten × Leistung)."""
    l, _quelle = leistung(zone, messungen)
    if l is None:
        l = wetter["referenz_mm"] / max(1, zone["standard_min"]) * 60
    return minuten * l / 60


def iu_eintraege(ctl: dict[str, Any], seq: dict[str, Any], smart_aktiv: bool) -> list[tuple[dict[str, Any], int]]:
    """Einträge der IU-Sequenz: (Sequenzzone, Durchgang). Mit Aufteilen kommt
    eine Zone mehrfach vor – erst alle ersten Durchgänge, dann die zweiten
    usw., damit das Wasser zwischen den Durchgängen einsickern kann."""
    if not smart_aktiv:
        return [(sz, 0) for sz in seq["zonen"]]
    zonen = {z["id"]: z for z in ctl["zonen"]}
    runden = {sz["zone"]: durchgaenge_max(zonen[sz["zone"]]) if sz["zone"] in zonen else 1 for sz in seq["zonen"]}
    return [(sz, r) for r in range(max(runden.values(), default=1)) for sz in seq["zonen"] if r < runden[sz["zone"]]]
