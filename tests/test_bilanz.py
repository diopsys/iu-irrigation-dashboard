"""Wasserbilanz und Laufzeit-Prozente (ohne laufendes Home Assistant).

Aufruf (im Repo-Stamm):  python tests/test_bilanz.py
"""
import asyncio
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from beispiel import ein  # setzt auch sys.path
from custom_components.iu_irrigation_dashboard import steuerung as st  # noqa: E402
from custom_components.iu_irrigation_dashboard import wetter as we  # noqa: E402

fehler = 0


def pruefe(name, bedingung, info=""):
    global fehler
    print(f"{'ok    ' if bedingung else 'FEHLER'}  {name}{('  ' + str(info)) if info else ''}")
    if not bedingung:
        fehler += 1


class Zustaende(dict):
    def get(self, eid, standard=None):  # noqa: D401
        return super().get(eid, standard)


def zustand(wert, **attr):
    return SimpleNamespace(state=str(wert), attributes=attr)


KONFIG = Path(tempfile.mkdtemp(prefix="iu_test_"))
hass = SimpleNamespace(
    states=Zustaende(),
    config=SimpleNamespace(latitude=52.5, elevation=30, config_dir=str(KONFIG),
                           path=lambda *a: str(KONFIG / "_".join(a))),
    data={},
)

daten = ein.pruefen({
    "version": 2,
    "controller": [{
        "id": "c1", "name": "Garten",
        "pumpe": {"entity_id": "switch.pumpe"},
        "zonen": [
            {"id": "rasen", "name": "Rasen", "ventile": ["switch.rasen"], "standard_min": 20},
            {"id": "beet", "name": "Beet", "ventile": ["switch.beet"], "standard_min": 10, "faktor": 50},
            {"id": "gh", "name": "Gewächshaus", "ventile": ["switch.gh"], "standard_min": 20, "regen": False},
            {"id": "hahn", "name": "Hahn", "ventile": ["switch.hahn"], "wasserhahn": True, "betrieb": "wasserhahn"},
            {"id": "mess", "name": "Gemessen", "ventile": ["switch.mess"], "standard_min": 30, "leistung_mm_h": 12},
        ],
        "sequenzen": [{
            "id": "s1", "name": "Run 1",
            "zonen": [{"zone": z} for z in ("rasen", "beet", "gh", "hahn", "mess")],
            "plaene": [{"key": "alle", "name": "Alle", "monate": ein.MONATE, "tage": ["mon"], "laufzeit": 100}],
        }],
    }],
    "wetter": {"regen": "sensor.rain_total", "regenrate": "sensor.rain_rate"},
})

b = we.Wasserbilanz(hass)
b.speichern = lambda: None
W = daten["wetter"]

# drei trockene Tage mit 3 mm ET₀
for tag in range(1, 4):
    b._tag_buchen(date(2026, 7, tag), {"et0": 3.0, "regen": 0.0}, daten)
pruefe("trocken: Bilanz −9 mm", b.daten["bilanz"]["rasen"] == -9.0, b.daten["bilanz"]["rasen"])
# 20 mm Regen: Rasen + 0,8 × 20 − 3 = +4 (≤ Speicher 10); Gewächshaus ohne Regen −12
b._tag_buchen(date(2026, 7, 4), {"et0": 3.0, "regen": 20.0}, daten)
pruefe("Regen wirkt: Rasen +4 mm", b.daten["bilanz"]["rasen"] == 4.0, b.daten["bilanz"]["rasen"])
pruefe("Regen wirkt nicht: Gewächshaus −12 mm", b.daten["bilanz"]["gh"] == -12.0, b.daten["bilanz"]["gh"])
# Speicher begrenzt: 50 mm Regen → höchstens 10 mm
b._tag_buchen(date(2026, 7, 5), {"et0": 1.0, "regen": 50.0}, daten)
pruefe("Speicher-Grenze 10 mm", b.daten["bilanz"]["rasen"] == 10.0, b.daten["bilanz"]["rasen"])
pruefe("30 Tage höchstens", len(b.daten["tage"]) <= 30)

# Gutschrift: 20 min Rasen (Standard 20) = Referenz 3 mm
b.daten["bilanz"]["rasen"] = -6.0
b.lauf_gutschreiben(daten["controller"][0]["zonen"][0], 20, daten)
pruefe("Gutschrift Lauf: −6 + 3 = −3", b.daten["bilanz"]["rasen"] == -3.0, b.daten["bilanz"]["rasen"])
pruefe("Minutenzähler", b.daten["minuten"]["rasen"] == 20)
pruefe("Referenz aus Beregnungsleistung: 12 mm/h × 30 min = 6 mm",
       we.Wasserbilanz.referenz(daten["controller"][0]["zonen"][4], W) == 6.0)


# Faktoren: Prognose fest vorgeben
async def prognose(_w, _j):
    return {"et0": 3.0, "regen": 0.0, "stunden": []}

b._prognose = prognose
b.daten["bilanz"].update({"rasen": -3.0, "beet": 0.0, "gh": -30.0, "mess": -9.0})
b.daten["regen_mitternacht"] = 100.0
hass.states["sensor.rain_total"] = zustand(100.0)
asyncio.run(b.aktualisieren(daten))
f = {k: v["faktor"] for k, v in b.aktuell["zonen"].items()}
pruefe("Faktor Rasen (3 + 3) / 3 = 2,0", f["rasen"] == 2.0, f)
pruefe("Faktor Beet (0 + 3) / 3 = 1,0", f["beet"] == 1.0)
pruefe("Faktor Gewächshaus gedeckelt auf 200 %", f["gh"] == 2.0)
pruefe("Faktor gemessene Zone (9 + 3) / 6 = 2,0", f["mess"] == 2.0)

# Regen heute 5 mm → Rasen: (3 + 3 − 4) / 3 = 0,67; Gewächshaus unverändert
hass.states["sensor.rain_total"] = zustand(105.0)
asyncio.run(b.aktualisieren(daten))
f = {k: v["faktor"] for k, v in b.aktuell["zonen"].items()}
pruefe("Regen heute kürzt Rasen auf 0,67", f["rasen"] == 0.67, f["rasen"])
pruefe("Regen heute kürzt Gewächshaus nicht", f["gh"] == 2.0)

# es regnet gerade → Zonen mit Regen 0
hass.states["sensor.rain_rate"] = zustand(1.2)
asyncio.run(b.aktualisieren(daten))
pruefe("es regnet: Rasen 0", b.aktuell["zonen"]["rasen"]["faktor"] == 0.0)
pruefe("es regnet: Gewächshaus weiter", b.aktuell["zonen"]["gh"]["faktor"] == 2.0)
hass.states["sensor.rain_rate"] = zustand(0)
hass.states["sensor.rain_total"] = zustand(100.0)  # kein Regen heute
asyncio.run(b.aktualisieren(daten))

# Prozente je Sequenzzone – mit fest vorgegebenen Faktoren
for zid, wert in {"rasen": 0.67, "beet": 1.0, "gh": 2.0, "hahn": 1.0, "mess": 1.0}.items():
    b.aktuell["zonen"][zid]["faktor"] = wert
s = st.Beregnung.__new__(st.Beregnung)
s.hass, s.daten, s.bilanz = hass, daten, b
p = s.soll_prozente()["s1"]["zonen"]
print("  Prozente:", {k: (v["aktiv"], v["prozent"]) for k, v in p.items()})
pruefe("Rasen 67 % → 65 % (5er-Raster)", p["rasen"]["prozent"] == 65 and p["rasen"]["aktiv"])
pruefe("Beet 100 % × Zonenfaktor 50 % = 50 %", p["beet"]["prozent"] == 50)
pruefe("Wasserhahn-Zone in der Automatik aus", p["hahn"]["aktiv"] is False)
daten["wetter"]["aktiv"] = False
p = s.soll_prozente()["s1"]["zonen"]
pruefe("Wetter aus: Rasen 100 %", p["rasen"]["prozent"] == 100)
daten["wetter"]["aktiv"] = True
daten["wetter"]["grundfaktor"] = 0
p = s.soll_prozente()["s1"]["zonen"]
pruefe("Grundfaktor 0: alle Zonen aus", not any(z["aktiv"] for z in p.values()))

# ET₀: FAO-56 Beispiel 18 (Uccle, 6. Juli; 3,9 mm) – gemessen und mit Ersatz-Einstrahlung
from custom_components.iu_irrigation_dashboard import et0  # noqa: E402

kw = dict(rh_mittel=73.5, wind_ms=2.78, tag_im_jahr=187, breite_grad=50.8, hoehe_m=100,
          wind_messhoehe_m=10, rh_min=63, rh_max=84)
e_mess = et0.et0_tag(12.3, 21.5, rs_mj=22.07, **kw)
pruefe("FAO-Beispiel 18: 3,9 mm", abs(e_mess - 3.9) < 0.1, round(e_mess, 2))
ra = et0.extraterrestrische_strahlung(187, 50.8)
rs = et0.strahlung_aus_temperatur(ra, 12.3, 21.5, 100)
pruefe("Ersatz-Einstrahlung 0,16·√ΔT·Ra", abs(rs - 0.16 * (21.5 - 12.3) ** 0.5 * ra) < 0.01, round(rs, 2))
pruefe("Ersatz-Einstrahlung höchstens klarer Himmel", et0.strahlung_aus_temperatur(ra, 0, 40, 100) <= 0.752 * ra)
e_ers = et0.et0_tag(12.3, 21.5, rs_mj=rs, **kw)
pruefe("ET₀ mit Ersatz-Einstrahlung plausibel", 3.0 < e_ers < 4.2, round(e_ers, 2))


# Tag ohne Einstrahlungssensor: ET₀ aus der Temperaturspanne statt keiner Buchung
async def statistik(ids, _start, _ende, _periode, _typen):
    werte = {"sensor.t": [{"min": 12.3, "max": 21.5, "mean": 17}], "sensor.rh": [{"min": 63, "max": 84, "mean": 73.5}],
             "sensor.wind": [{"mean": 7.0}], "sensor.rain_total": [{"change": 1.5}]}
    return {i: werte[i] for i in ids if i in werte}

b._statistik = statistik
b._einheit = lambda eid: {"sensor.t": "°C", "sensor.wind": "km/h"}.get(eid)
quellen = {"temperatur": "sensor.t", "feuchte": "sensor.rh", "wind": "sensor.wind", "regen": "sensor.rain_total",
           "wind_hoehe_m": 2.0, "hoehe_m": 100, "krs": 0.16}
tag = asyncio.run(b.tag_auswerten(date(2026, 7, 6), quellen))
pruefe("ohne Einstrahlungssensor: ET₀ berechnet", tag["et0"] is not None and 2.5 < tag["et0"] < 4.5, tag)
pruefe("ohne Einstrahlungssensor: Regen", tag["regen"] == 1.5)
quellen["krs"] = 0.10
weniger = asyncio.run(b.tag_auswerten(date(2026, 7, 6), quellen))
pruefe("kleineres kRs → weniger ET₀", weniger["et0"] < tag["et0"], (weniger["et0"], tag["et0"]))
sys.exit(1 if fehler else 0)
