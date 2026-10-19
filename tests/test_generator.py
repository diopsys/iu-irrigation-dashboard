"""Einstellungen prüfen, IU-Konfiguration erzeugen und wieder übernehmen.

Aufruf (im Repo-Stamm):  python tests/test_generator.py [--yaml]

1. Beispielanlage → IU-Konfiguration (YAML hin und zurück, IU-Schema, falls
   custom_components/irrigation_unlimited daneben liegt), Zuordnung der
   IU-Entitäten.
2. Übernahme: die erzeugte IU-Konfiguration ergibt wieder dieselbe Anlage.
3. Ungültige Einstellungen werden abgewiesen.
"""
import copy
import sys

import voluptuous as vol

from beispiel import beispiel, ein  # setzt auch sys.path
from homeassistant.util.yaml import loader

from custom_components.iu_irrigation_dashboard import iu_yaml

fehler = 0


def pruefe(name, bedingung, info=""):
    global fehler
    print(f"{'ok    ' if bedingung else 'FEHLER'}  {name}{('  ' + str(info)) if info else ''}")
    if not bedingung:
        fehler += 1


def main():
    daten = beispiel()
    konfig = iu_yaml.erzeugen(daten)
    text = iu_yaml.als_text(konfig)
    if "--yaml" in sys.argv:
        print(text)
    z = loader.parse_yaml(text)["irrigation_unlimited"]
    pruefe("YAML hin und zurück", z == konfig)
    try:
        from custom_components.irrigation_unlimited.schema import IRRIGATION_SCHEMA
        try:
            IRRIGATION_SCHEMA(z)
            pruefe("IU-Schema", True)
        except vol.Invalid as err:
            pruefe("IU-Schema", False, err)
    except ImportError:
        print("–       IU-Schema übersprungen (Irrigation Unlimited nicht unter custom_components/)")

    c1, c2 = z["controllers"]
    pruefe("2 Controller, 2 + 1 Sequenzen", len(c1["sequences"]) == 2 and len(c2["sequences"]) == 1)
    pruefe("Zone mit zwei Ventilen", c1["zones"][1]["entity_id"] == ["switch.valve_beds", "valve.beds_2"])
    s1, s2 = c1["sequences"]
    pruefe("eigene Dauer je Sequenz", s1["zones"][1]["duration"] == "00:10:00" and s2["zones"][0]["duration"] == "00:07:00")
    pruefe("abgeschaltete Zone", s1["zones"][2]["enabled"] is False)
    pruefe("Wasserhahn nicht in der Automatik", s1["zones"][3]["enabled"] is False)
    pruefe("vor Sonnenaufgang", s1["schedules"][0]["time"] == {"sun": "sunrise", "before": "00:45:00"})
    pruefe("nach Sonnenaufgang", s1["schedules"][1]["time"] == {"sun": "sunrise", "after": "01:30:00"})
    pruefe("nach Sonnenuntergang", s2["schedules"][0]["time"] == {"sun": "sunset", "after": "00:30:00"})
    pruefe("feste Uhrzeit", s2["schedules"][1]["time"] == "05:30:00")
    pruefe("Pumpe schaltet IU nur ein", c1["entity_states"] == "on" and c1["check_back"] == {"states": "on"})
    zu = iu_yaml.zuordnung(daten)
    pruefe("Zuordnung", zu["controller"]["c2"].endswith("c2_m") and zu["zonen"]["front"].endswith("c2_z1")
           and zu["sequenzen"]["s2"].endswith("c1_s2"))

    # 2. Übernahme der erzeugten Konfiguration
    neu = ein.aus_iu_konfig(z)
    for alt_c, neu_c in zip(daten["controller"], neu["controller"]):
        pruefe(f"Übernahme {alt_c['name']}: Pumpe, Zonen, Ventile",
               neu_c["pumpe"]["entity_id"] == alt_c["pumpe"]["entity_id"]
               and [(x["name"], x["ventile"]) for x in neu_c["zonen"]] == [(x["name"], x["ventile"]) for x in alt_c["zonen"]])
        for alt_s, neu_s in zip(alt_c["sequenzen"], neu_c["sequenzen"]):
            alt_z = {zz["id"]: zz for zz in alt_c["zonen"]}
            neu_z = {zz["id"]: zz for zz in neu_c["zonen"]}
            dauer = lambda c, sz: sz["dauer_min"] or c[sz["zone"]]["standard_min"]  # noqa: E731
            pruefe(f"Übernahme {alt_s['name']}: Zonen, Dauer",
                   [(alt_z[x["zone"]]["name"], dauer(alt_z, x)) for x in alt_s["zonen"]]
                   == [(neu_z[x["zone"]]["name"], dauer(neu_z, x)) for x in neu_s["zonen"]])
            pruefe(f"Übernahme {alt_s['name']}: Pläne",
                   [(p["name"], p["monate"], p["tage"], p["zeit"]["bezug"], p["zeit"]["versatz_min"] if p["zeit"]["bezug"] != "uhrzeit" else p["zeit"]["uhrzeit"]) for p in alt_s["plaene"]]
                   == [(p["name"], p["monate"], p["tage"], p["zeit"]["bezug"], p["zeit"]["versatz_min"] if p["zeit"]["bezug"] != "uhrzeit" else p["zeit"]["uhrzeit"]) for p in neu_s["plaene"]])
    pruefe("ohne IU-Konfiguration leer", ein.aus_iu_konfig(None)["controller"] == [])
    pruefe("Wetterquellen leer vorbelegt", not any(v for k, v in ein.STANDARD["wetter"].items()
                                                  if k in ("regen", "regenrate", "prognose", "temperatur")))

    # 3. ungültig
    for name, kaputt in (
        ("Zone ohne Ventil", lambda d: d["controller"][0]["zonen"][0].update(ventile=[])),
        ("fremde Zone in Sequenz", lambda d: d["controller"][1]["sequenzen"][0]["zonen"].append({"zone": "lawn"})),
        ("Monat doppelt", lambda d: d["controller"][0]["sequenzen"][0]["plaene"][1].update(monate=["jun"])),
        ("Pumpe doppelt", lambda d: d["controller"][1]["pumpe"].update(entity_id="switch.garden_pump")),
        ("Zonen-ID doppelt", lambda d: d["controller"][1]["zonen"][0].update(id="lawn")),
        ("Laufzeit über 200 %", lambda d: d["controller"][0]["sequenzen"][0]["plaene"][0].update(laufzeit=250)),
    ):
        d = copy.deepcopy(daten)
        kaputt(d)
        try:
            ein.pruefen(d)
            pruefe(f"abgewiesen: {name}", False)
        except vol.Invalid as err:
            pruefe(f"abgewiesen: {name}", True, str(err)[:70])
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
