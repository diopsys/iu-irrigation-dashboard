"""Smarte Laufzeit je Zone (experimentell, smart.py).

Aufruf (im Repo-Stamm):  python tests/test_smart.py

Planung je Zone (Gießweise, Schwelle, Beregnungsleistung je Quelle,
Höchstlaufzeit, Durchgänge), Bilanz mit Kc und eigenem Speicher, Gutschrift
gemessener Mengen, IU-Sequenz mit Durchgängen und Prozente je Eintrag –
und dass ohne den Schalter alles wie bisher bleibt.
"""
import asyncio
import copy
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from beispiel import ein  # setzt auch sys.path
from custom_components.iu_irrigation_dashboard import iu_yaml, smart  # noqa: E402
from custom_components.iu_irrigation_dashboard import steuerung as st  # noqa: E402
from custom_components.iu_irrigation_dashboard import wetter as we  # noqa: E402

fehler = 0


def pruefe(name, bedingung, info=""):
    global fehler
    print(f"{'ok    ' if bedingung else 'FEHLER'}  {name}{('  ' + str(info)) if info else ''}")
    if not bedingung:
        fehler += 1


def nah(a, b, d=0.05):
    return a is not None and abs(a - b) < d


class Zustaende(dict):
    def get(self, eid, standard=None):  # noqa: D401
        return super().get(eid, standard)


KONFIG = Path(tempfile.mkdtemp(prefix="iu_smart_"))
hass = SimpleNamespace(states=Zustaende(), data={},
                       config=SimpleNamespace(latitude=52.5, elevation=30, config_dir=str(KONFIG),
                                              path=lambda *a: str(KONFIG / "_".join(a))))

RASEN = {"typ": "rasen", "kc": 0.8, "speicher_mm": 20, "giessweise": "schwelle", "schwelle_prozent": 50,
         "flaeche_m2": 196, "leistung_quelle": "durchfluss", "durchfluss_l_min": 11.57, "max_min": 180,
         "aufteilen": True, "durchgang_min": 60, "sickerpause_min": 10}
roh = {
    "version": 2,
    "smart": {"aktiv": True},
    "controller": [{
        "id": "c1", "name": "Garten", "anschluss": "leitung", "wasser": {"zaehler": "sensor.wasser"},
        "zonen": [
            {"id": "rasen", "name": "Rasen", "ventile": ["switch.rasen"], "standard_min": 30, "smart": RASEN},
            {"id": "kuebel", "name": "Kübel", "ventile": ["switch.kuebel"], "standard_min": 10, "regen": False,
             "smart": {"typ": "gemuese", "kc": 1.0, "speicher_mm": 10, "giessweise": "bedarf",
                       "flaeche_m2": 5, "leistung_quelle": "zaehler", "max_min": 20}},
            {"id": "alt", "name": "Ohne Angaben", "ventile": ["switch.alt"], "standard_min": 20},
        ],
        "sequenzen": [{"id": "s1", "name": "Morgens", "zonen": [{"zone": "rasen"}, {"zone": "kuebel"}, {"zone": "alt"}],
                       "plaene": [{"key": "alle", "name": "Alle", "monate": ein.MONATE, "tage": ["mon"], "laufzeit": 100}]}],
    }],
    "wetter": {"regen": "sensor.rain_total", "temperatur": "sensor.t"},
}
daten = ein.pruefen(copy.deepcopy(roh))
W = daten["wetter"]
rasen, kuebel, alt = daten["controller"][0]["zonen"]

# ── Planung je Zone ──────────────────────────────────────────────────
pruefe("Standard: smart aus, Kc 1, Gießweise bedarf",
       not smart.aktiv(ein.pruefen({})) and alt["smart"]["kc"] == 1.0 and alt["smart"]["giessweise"] == "bedarf")
l, q = smart.leistung(rasen, None)
pruefe("Leistung aus Durchfluss: 11,57 L/min ÷ 196 m² = 3,54 mm/h", nah(l, 3.54, 0.01) and q == "durchfluss", (l, q))
p = smart.planen(rasen, -6.0, 0, False, W)
pruefe("Schwelle: Defizit 6 < 10 mm → übersprungen", p["minuten"] == 0 and p["grund"] == "unter_schwelle", p["grund"])
pruefe("Überschuss zählt nicht: Bilanz +10 = voll, Defizit 0",
       smart.planen(rasen, 10.0, 0, False, W)["defizit"] == 0 and smart.planen(rasen, 10.0, 0, False, W)["grund"] == "unter_schwelle")
p = smart.planen(rasen, -12.0, 0, False, W)
# bis voll auffüllen: 12 mm ÷ 3,54 mm/h = 203 min → höchstens 180
pruefe("über der Schwelle: auffüllen bis voll, Bedarf 12 mm", nah(p["bedarf"], 12.0) and p["grund"] == "begrenzt", p)
pruefe("Höchstlaufzeit 180 min, 3 Durchgänge à 60", p["minuten"] == 180 and p["durchgaenge"] == 3)
pruefe("Menge und Liter: 180 min × 3,54 mm/h = 10,6 mm ≈ 2083 L", nah(p["mm"], 10.6, 0.1) and abs(p["liter"] - 2083) < 15, p)
pruefe("Defizit höchstens der Speicher (−32 → 20 mm)", smart.planen(rasen, -32.0, 0, False, W)["defizit"] == 20.0)
p = smart.planen(rasen, -12.0, 20, False, W)
pruefe("Regen (20 mm, 80 % wirksam) deckt den Bedarf", p["minuten"] == 0 and p["grund"] == "regen_deckt", p["bedarf"])
p = smart.planen(rasen, -12.0, 3, False, W)
pruefe("Tief gießen: Rest nach Regen (12 − 2,4 = 9,6) unter der Schwelle → warten", p["minuten"] == 0 and p["grund"] == "regen_deckt", p)
pruefe("es regnet → übersprungen", smart.planen(rasen, -12.0, 0, True, W)["grund"] == "regnet")

# Kübel: Quelle Wasserzähler, erst ab 3 Messungen
p = smart.planen(kuebel, -2.0, 0, True, W)
pruefe("ohne Messung: Referenz 3 mm in 10 min = 18 mm/h", p["quelle"] == "referenz" and nah(p["leistung"], 18), p)
pruefe("Zone ohne Regen läuft auch bei Regen", p["minuten"] > 0)
pruefe("2 Messungen reichen nicht", smart.leistung(kuebel, [2.0, 2.0])[1] == "referenz" or smart.leistung(kuebel, [2.0, 2.0])[0] is None)
l, q = smart.leistung(kuebel, [2.0, 9.0, 2.2, 1.8, 2.0])
pruefe("Median 2,0 L/min × 60 ÷ 5 m² = 24 mm/h (Ausreißer egal)", nah(l, 24, 0.5) and q == "zaehler", (l, q))
p = smart.planen(kuebel, -6.0, 0, False, W, [2.0, 2.0, 2.0])
pruefe("Gießweise bedarf: 6 mm ÷ 24 mm/h = 15 min", nah(p["minuten"], 15, 0.1) and p["durchgaenge"] == 1, p)
pruefe("Gießweise bedarf: Boden voll → kein Bedarf", smart.planen(kuebel, 0.0, 0, False, W)["grund"] == "kein_bedarf")

# ── Bilanz mit Kc und eigenem Speicher ───────────────────────────────
b = we.Wasserbilanz(hass)
b.speichern = lambda: None
b._tag_buchen(date(2026, 7, 1), {"et0": 5.0, "regen": 0.0}, daten)
pruefe("Tagesbilanz Rasen: −0,8 × 5 = −4", b.daten["bilanz"]["rasen"] == -4.0, b.daten["bilanz"])
pruefe("Tagesbilanz ohne Angaben: Kc 1 → −5", b.daten["bilanz"]["alt"] == -5.0)
b._tag_buchen(date(2026, 7, 2), {"et0": 1.0, "regen": 50.0}, daten)
pruefe("viel Regen: Boden voll (0), der Rest versickert", b.daten["bilanz"]["rasen"] == 0.0 and b.daten["bilanz"]["alt"] == 0.0,
       b.daten["bilanz"])
for tag in range(3, 13):
    b._tag_buchen(date(2026, 7, tag), {"et0": 4.0, "regen": 0.0}, daten)
pruefe("10 trockene Tage: Defizit höchstens der eigene Speicher (Rasen 20, sonst 10 mm)",
       b.daten["bilanz"]["rasen"] == -20.0 and b.daten["bilanz"]["alt"] == -10.0, b.daten["bilanz"])

# Beispiel aus der Prüfung: 20 mm Speicher, Schwelle 50 %, 4 mm ET₀ – nach starkem Regen
b.daten["bilanz"]["rasen"] = 0.0
tage = 0
while smart.planen(rasen, b.daten["bilanz"]["rasen"], 0, False, W)["minuten"] == 0 and tage < 30:
    tage += 1
    b._tag_buchen(date(2026, 8, tage), {"et0": 4.0, "regen": 0.0}, daten)
p = smart.planen(rasen, b.daten["bilanz"]["rasen"], 0, False, W)
pruefe("nach starkem Regen läuft der Rasen am 4. Tag (Defizit 12,8 ≥ 10), nicht erst am 11.",
       tage == 4 and nah(p["defizit"], 12.8), (tage, p["defizit"]))
b.daten["bilanz"]["rasen"] = -12.0
b.daten["minuten"]["rasen"] = 0
b.lauf_gutschreiben(rasen, 60, daten, gutschrift=False)
pruefe("ohne Gutschrift: nur Minuten", b.daten["bilanz"]["rasen"] == -12.0 and b.daten["minuten"]["rasen"] == 60)
b.wasser_gutschreiben(rasen, 1176 / 196, daten)
pruefe("gemessene Menge: 1176 L ÷ 196 m² = 6 mm", b.daten["bilanz"]["rasen"] == -6.0, b.daten["bilanz"]["rasen"])
b.lauf_gutschreiben(rasen, 60, daten)
pruefe("Gutschrift aus Minuten × Leistung: 60 min × 3,54 = 3,5 mm", nah(b.daten["bilanz"]["rasen"], -2.46, 0.02),
       b.daten["bilanz"]["rasen"])
b.wasser_gutschreiben(rasen, 8.0, daten)
pruefe("Gutschrift über voll hinaus versickert (höchstens 0)", b.daten["bilanz"]["rasen"] == 0.0)
b.durchfluss_messen("kuebel", 30, 15)
b.durchfluss_messen("kuebel", 0, 15)
b.durchfluss_messen("kuebel", 5, 0.5)
pruefe("Messung: 30 L in 15 min = 2 L/min; leere und zu kurze Läufe zählen nicht", b.daten["durchfluss"]["kuebel"] == [2.0])
for _ in range(8):
    b.durchfluss_messen("kuebel", 20, 10)
pruefe("höchstens 5 Messungen", len(b.daten["durchfluss"]["kuebel"]) == smart.MESSUNGEN_MAX)

# ── ohne Temperatur keine Tage buchen (Fix: ET₀ = 0 nach der Einrichtung) ──
b2 = we.Wasserbilanz(hass)
b2.speichern = lambda: None
ohne_t = copy.deepcopy(daten)
ohne_t["wetter"]["temperatur"] = None
pruefe("ohne Temperatursensor: nichts gebucht", asyncio.run(b2.nachholen(ohne_t)) is False and b2.daten["letzter_tag"] is None
       and b2.daten["tage"] == [])

# ── IU-Sequenz mit Durchgängen ───────────────────────────────────────
eintraege = smart.iu_eintraege(daten["controller"][0], daten["controller"][0]["sequenzen"][0], True)
pruefe("Durchgänge verschränkt: Rasen, Kübel, Alt, Rasen, Rasen",
       [(sz["zone"], r) for sz, r in eintraege] == [("rasen", 0), ("kuebel", 0), ("alt", 0), ("rasen", 1), ("rasen", 2)])
seq = iu_yaml.erzeugen(daten)["controllers"][0]["sequences"][0]["zones"]
pruefe("IU: 5 Einträge, Sickerpause 10 min nach Rasen-Durchgang 1 und 2, nicht nach dem letzten",
       [z["zone_id"] for z in seq] == ["1", "2", "3", "1", "1"]
       and [z.get("delay") for z in seq] == ["00:10:00", None, None, "00:10:00", None], seq)
try:
    from custom_components.irrigation_unlimited.schema import IRRIGATION_SCHEMA
    try:
        IRRIGATION_SCHEMA(iu_yaml.erzeugen(daten))
        pruefe("IU-Schema mit Durchgängen und Sickerpause", True)
    except Exception as err:  # noqa: BLE001
        pruefe("IU-Schema mit Durchgängen und Sickerpause", False, err)
except ImportError:
    print("–       IU-Schema übersprungen (Irrigation Unlimited nicht unter custom_components/)")
aus = copy.deepcopy(roh)
aus["smart"]["aktiv"] = False
ohne = copy.deepcopy(roh)
ohne.pop("smart")
for z in ohne["controller"][0]["zonen"]:
    z.pop("smart", None)
pruefe("smart aus: IU-Datei gleich wie ganz ohne smarte Einstellungen",
       iu_yaml.als_text(iu_yaml.erzeugen(ein.pruefen(aus))) == iu_yaml.als_text(iu_yaml.erzeugen(ein.pruefen(ohne))))

# ── Prozente je Eintrag ──────────────────────────────────────────────
s = st.Beregnung.__new__(st.Beregnung)
s.hass, s.daten, s.bilanz = hass, daten, b
s.hass.states = Zustaende()
b.aktuell = {"zonen": {
    "rasen": smart.planen(rasen, -12.0, 0, False, W),           # 180 min, 3 Durchgänge
    "kuebel": smart.planen(kuebel, -6.0, 0, False, W, [2.0] * 3),  # 6 mm ÷ 24 mm/h = 15 min
    "alt": smart.planen(alt, -3.0, 0, False, W),                # 3 mm ÷ 9 mm/h = 20 min
}}
erg = s.soll_prozente()["s1"]
pruefe("Rasen je Durchgang 60 min von 30 = 200 %", [e[2] for e in erg["eintraege"]] == [200, 150, 100, 200, 200], erg["eintraege"])
pruefe("Zone: Gesamtminuten und Durchgänge", erg["zonen"]["rasen"]["minuten"] == 180 and erg["zonen"]["rasen"]["durchgaenge"] == 3)
b.aktuell["zonen"]["rasen"] = smart.planen(rasen, -11.0, 0, False, W)  # 11 mm ÷ 3,54 = 186 → 180
b.aktuell["zonen"]["rasen"]["minuten"], b.aktuell["zonen"]["rasen"]["durchgaenge"] = 70.0, 2
erg = s.soll_prozente()["s1"]
pruefe("2 von 3 Durchgängen: 35 min = 117 %, dritter aus", [(e[1], e[2]) for e in erg["eintraege"] if e[0] in (1, 4, 5)]
       == [(True, 117), (True, 117), (False, 0)], erg["eintraege"])
daten["wetter"]["grundfaktor"] = 50
erg = s.soll_prozente()["s1"]
pruefe("Grundfaktor 50 % halbiert die Minuten", erg["zonen"]["kuebel"]["minuten"] == 7.5)
daten["wetter"]["grundfaktor"] = 100


# ── Gutschrift je Zählermeldung ──────────────────────────────────────
from datetime import datetime, timedelta, timezone  # noqa: E402

t0 = datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc)
s._wasser_segmente = {"sensor.wasser": [["rasen", t0, t0 + timedelta(minutes=20)]]}
s._melden = lambda: None
b.daten["bilanz"]["rasen"] = -10.0
b.daten["wasser_l"]["rasen"] = 0.0


def stand(wert, zeit):
    return SimpleNamespace(state=str(wert), attributes={"unit_of_measurement": "m³"}, last_updated=zeit, last_reported=zeit)


s._zaehler_geaendert("sensor.wasser", stand(100.000, t0), stand(100.098, t0 + timedelta(minutes=10)))
pruefe("Zählermeldung: 98 L ÷ 196 m² = 0,5 mm sofort gutgeschrieben", b.daten["bilanz"]["rasen"] == -9.5, b.daten["bilanz"]["rasen"])
# langsamer Zähler: meldet den Rest erst 2 h nach dem Lauf – wird trotzdem verbucht
s._zaehler_geaendert("sensor.wasser", stand(100.098, t0 + timedelta(minutes=10)), stand(100.196, t0 + timedelta(hours=2)))
pruefe("späte Meldung des Zählers wird noch gutgeschrieben (−9,5 + 0,5 = −9)", b.daten["bilanz"]["rasen"] == -9.0,
       b.daten["bilanz"]["rasen"])
pruefe("Liter je Zone mitgezählt", b.daten["wasser_l"]["rasen"] == 196.0, b.daten["wasser_l"]["rasen"])

sys.exit(1 if fehler else 0)
