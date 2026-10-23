"""Eigenen Abschnitt irrigation_unlimited: in configuration.yaml finden und
auskommentieren.

Aufruf (im Repo-Stamm):  python tests/test_konfig_yaml.py

1. Bereich des Abschnitts: eingerückte Zeilen, Leerzeilen und Kommentare
   gehören dazu, ein Kommentar ganz links vor dem nächsten Abschnitt nicht;
   !include als einzelne Zeile; eingerückt (z. B. in packages) zählt nicht.
2. Auskommentieren: übrige Datei bleibt Zeichen für Zeichen gleich,
   Zeilenenden (CRLF) bleiben, YAML ergibt dieselbe Konfiguration ohne IU.
3. Beheben in einer Datei: Sicherung, nichts geändert, wenn sich der
   Abschnitt seit der Anzeige geändert hat.
"""
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.iu_irrigation_dashboard import konfig_yaml as k  # noqa: E402

fehler = 0


def pruefe(name, bedingung, info=""):
    global fehler
    print(f"{'ok    ' if bedingung else 'FEHLER'}  {name}{('  ' + str(info)) if info else ''}")
    if not bedingung:
        fehler += 1


KONFIG = """\
# Loads default set of integrations. Do not remove.
default_config:

homeassistant:
  packages: !include_dir_named packages

irrigation_unlimited:
  controllers:
    - name: Garten
      # Pumpe im Keller
      entity_id: switch.pumpe

      zones:
        - name: Rasen
          entity_id: switch.rasen
# ── Sensoren ──
sensor:
  - platform: time_date
"""

# 1. Bereich
bereich = k.iu_abschnitt(KONFIG)
zeilen = KONFIG.splitlines()
pruefe("Abschnitt gefunden", bereich == (6, 15), bereich)
pruefe("Kommentar vor sensor: bleibt draußen", zeilen[bereich[1]] == "# ── Sensoren ──")
pruefe("ohne Abschnitt → None", k.iu_abschnitt(KONFIG.replace("irrigation_unlimited:", "iu_alt:")) is None)
pruefe("eingerückt (Package) zählt nicht",
       k.iu_abschnitt("homeassistant:\n  packages:\n    x:\n      irrigation_unlimited:\n        a: 1\n") is None)
einzeilig = "default_config:\nirrigation_unlimited: !include iu.yaml\nsensor: !include s.yaml\n"
pruefe("!include als einzelne Zeile", k.iu_abschnitt(einzeilig) == (1, 2), k.iu_abschnitt(einzeilig))
am_ende = "default_config:\nirrigation_unlimited:\n  controllers: []\n\n# Ende"
pruefe("am Dateiende, ohne Zeilenende", k.iu_abschnitt(am_ende) == (1, 3), k.iu_abschnitt(am_ende))
pruefe("mit BOM in Zeile 1", k.iu_abschnitt("\ufeffirrigation_unlimited:\n  a: 1\n") == (0, 2))

auszug = k.auszug(KONFIG, bereich)
pruefe("Auszug: Anfang, …, Ende mit Zeilennummern",
       auszug.splitlines()[0] == " 7  irrigation_unlimited:" and "…" in auszug
       and auszug.splitlines()[-1].endswith("entity_id: switch.rasen"), "\n" + auszug)

# 2. Auskommentieren
neu = k.auskommentieren(KONFIG, bereich, "test")
pruefe("danach kein Abschnitt mehr", k.iu_abschnitt(neu) is None)
pruefe("Zeilen davor unverändert", neu.startswith("\n".join(zeilen[:6]) + "\n"))
pruefe("Zeilen danach unverändert", neu.endswith("\n".join(zeilen[15:]) + "\n"))
pruefe("Hinweiszeile davor", neu.splitlines()[6] == f"{k.MARKE} test")
pruefe("Leerzeilen bleiben leer", "\n\n# " in neu.split(k.MARKE)[1])
alt, ohne = yaml.safe_load(KONFIG.replace("!include_dir_named ", "")), yaml.safe_load(neu.replace("!include_dir_named ", ""))
alt.pop("irrigation_unlimited")
pruefe("YAML ohne IU gleich", alt == ohne, ohne)
crlf = KONFIG.replace("\n", "\r\n")
neu_crlf = k.auskommentieren(crlf, k.iu_abschnitt(crlf), "test")
pruefe("CRLF bleibt", neu_crlf.count("\r\n") == neu_crlf.count("\n") and neu_crlf.replace("\r\n", "\n") == neu)
neu_ende = k.auskommentieren(am_ende, k.iu_abschnitt(am_ende), "test")
pruefe("am Dateiende", neu_ende == f"default_config:\n{k.MARKE} test\n# irrigation_unlimited:\n#   controllers: []\n\n# Ende",
       repr(neu_ende))

# 3. Beheben in einer Datei
with tempfile.TemporaryDirectory() as tmp:
    pfad = Path(tmp) / "configuration.yaml"
    pfad.write_bytes(crlf.encode())
    gefunden = k.finden(pfad)
    pruefe("finden", gefunden is not None and gefunden[1] == (6, 15))
    pruefe("geänderter Abschnitt → nichts tun", k.beheben(pfad, "anders") is None and pfad.read_bytes() == crlf.encode()
           and not list(Path(tmp).glob("*.iu_backup_*")))
    ergebnis = k.beheben(pfad, k.auszug(gefunden[0], gefunden[1]))
    sicherungen = list(Path(tmp).glob("configuration.yaml.iu_backup_*"))
    pruefe("beheben", ergebnis is not None and ergebnis[1] == (6, 15))
    pruefe("Sicherung = Original", len(sicherungen) == 1 and sicherungen[0].read_bytes() == crlf.encode())
    inhalt = pfad.read_bytes().decode()
    pruefe("Datei auskommentiert, CRLF erhalten", k.iu_abschnitt(inhalt) is None and "\r\n# irrigation_unlimited:\r\n" in inhalt
           and inhalt.count("\n") == inhalt.count("\r\n"))
    pruefe("Hinweis nennt die Sicherung", sicherungen[0].name in inhalt)
    pruefe("zweites Mal → nichts mehr zu tun", k.beheben(pfad) is None)
    pruefe("fehlende Datei → None", k.finden(Path(tmp) / "fehlt.yaml") is None)

print("\nAlles in Ordnung." if not fehler else f"\n{fehler} Fehler.")
sys.exit(1 if fehler else 0)
