"""Wasserverbrauch am Wasseranschluss je Zone aus einem Wasserzähler.

Ein Zähler meldet seinen Stand in Abständen (z. B. alle 5 min). Die Menge
zwischen zwei Ständen wird auf die Zonen verteilt, die in diesem Zeitraum
liefen – anteilig nach ihrer Laufzeit darin. Läuft keine Zone, ist es beim
Hauptzähler Verbrauch des Hauses und zählt nicht.

Zeitraum = letzte Meldung des alten Stands (last_reported) bis zum neuen
Stand. So zählt ein Zähler, der stundenlang denselben Stand meldet, nur die
Zeit seit seiner letzten Meldung.
"""

from __future__ import annotations

from datetime import datetime

# Liter je Einheit des Zählers
LITER_JE_EINHEIT = {
    "L": 1.0, "l": 1.0,
    "m³": 1000.0, "m3": 1000.0,
    "gal": 3.785411784,
    "ft³": 28.316846592, "ft3": 28.316846592,
    "CCF": 2831.6846592,
}

# Sprung je Meldung, der sicher ein Messfehler ist (Liter)
MAX_SPRUNG_L = 5000.0


def liter(wert: str | float | None, einheit: str | None) -> float | None:
    """Zählerstand in Liter; None ohne gültigen Wert oder Einheit."""
    faktor = LITER_JE_EINHEIT.get(einheit or "")
    try:
        zahl = float(wert)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return zahl * faktor if faktor else None


def verteilen(segmente: list[list], von: datetime, bis: datetime, menge: float) -> dict[str, float]:
    """Menge auf die Zonen verteilen, anteilig nach ihrer Laufzeit in [von, bis].

    segmente: [[zone_id, start, ende | None], …] (ende None = läuft noch)
    """
    if menge <= 0 or bis <= von:
        return {}
    anteile: dict[str, float] = {}
    for zone_id, start, ende in segmente:
        a, b = max(start, von), min(ende or bis, bis)
        if b > a:
            anteile[zone_id] = anteile.get(zone_id, 0.0) + (b - a).total_seconds()
    summe = sum(anteile.values())
    if not summe:
        return {}
    return {zone_id: menge * s / summe for zone_id, s in anteile.items()}


def aufraeumen(segmente: list[list], bis: datetime) -> list[list]:
    """Abgeschlossene Segmente vor bis entfernen (sind verteilt)."""
    return [s for s in segmente if s[2] is None or s[2] > bis]
