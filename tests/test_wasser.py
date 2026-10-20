"""Wasserverbrauch je Zone aus einem Wasserzähler (wasser.py).

Aufruf (im Repo-Stamm):  python tests/test_wasser.py

Umrechnung der Zählerstände in Liter, Verteilung einer Menge auf die Zonen,
die im Zeitraum zwischen zwei Zählerständen liefen, und Aufräumen
abgeschlossener Läufe.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.iu_irrigation_dashboard import wasser  # noqa: E402

fehler = 0


def pruefe(name, bedingung, info=""):
    global fehler
    print(f"{'ok    ' if bedingung else 'FEHLER'}  {name}{('  ' + str(info)) if info else ''}")
    if not bedingung:
        fehler += 1


def nah(a, b):
    return abs(a - b) < 1e-6


def main():
    t0 = datetime(2026, 7, 1, 6, 0, tzinfo=timezone.utc)
    m = lambda minuten: t0 + timedelta(minutes=minuten)  # noqa: E731

    pruefe("m³ → Liter", nah(wasser.liter("731.887", "m³"), 731887))
    pruefe("L bleibt Liter", nah(wasser.liter(12.5, "L"), 12.5))
    pruefe("unbekannte Einheit / kein Wert", wasser.liter("5", "kWh") is None and wasser.liter("unavailable", "m³") is None)

    # eine Zone läuft den ganzen Zeitraum → alles
    v = wasser.verteilen([["a", m(0), None]], m(0), m(5), 40)
    pruefe("eine Zone, ganzer Zeitraum", nah(v["a"], 40), v)

    # Zone a bis Minute 2, Pause, Zone b ab Minute 3 → 2 : 2
    v = wasser.verteilen([["a", m(-10), m(2)], ["b", m(3), None]], m(0), m(5), 40)
    pruefe("zwei Zonen nacheinander anteilig", nah(v["a"], 20) and nah(v["b"], 20), v)

    # Zone nur 1 von 5 Minuten im Zeitraum → bekommt trotzdem alles (sonst lief nichts)
    v = wasser.verteilen([["a", m(4), None]], m(0), m(5), 30)
    pruefe("Zone nur teilweise im Zeitraum bekommt alles", nah(v["a"], 30), v)

    # keine Zone im Zeitraum → Haushalt, nichts verteilt
    pruefe("ohne Lauf nichts verteilt", wasser.verteilen([["a", m(-20), m(-10)]], m(0), m(5), 30) == {})
    pruefe("Menge 0 / Zeitraum leer", wasser.verteilen([["a", m(0), None]], m(0), m(5), 0) == {}
           and wasser.verteilen([["a", m(0), None]], m(5), m(5), 10) == {})

    # zwei Controller am selben Zähler gleichzeitig → je zur Hälfte
    v = wasser.verteilen([["a", m(0), None], ["b", m(0), None]], m(0), m(10), 100)
    pruefe("gleichzeitige Zonen je zur Hälfte", nah(v["a"], 50) and nah(v["b"], 50), v)

    # dieselbe Zone zweimal im Zeitraum (zwei Läufe) wird zusammengezählt
    v = wasser.verteilen([["a", m(0), m(1)], ["a", m(2), m(3)], ["b", m(4), m(6)]], m(0), m(6), 60)
    pruefe("mehrere Läufe einer Zone zusammen", nah(v["a"], 30) and nah(v["b"], 30), v)

    segmente = [["a", m(-10), m(2)], ["b", m(3), m(9)], ["c", m(4), None]]
    rest = wasser.aufraeumen(segmente, m(5))
    pruefe("Aufräumen: abgeschlossen vor dem Stand weg, laufende bleiben", [s[0] for s in rest] == ["b", "c"], rest)

    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
