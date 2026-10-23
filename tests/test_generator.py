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


# Schreibweisen, die IU akzeptiert: einzelne Einträge ohne „-“, Listen oder
# Einzelwerte, Zeiten als Text, Sonnenstand oder cron
EINZELN = """
controllers:
  all_zones_config:
    show:
      timeline: true
  name: Beregnung
  zones:
    - name: Terrasse
      entity_id: switch.valve_1
    - name: Rasen
      entity_id: [switch.valve_3, switch.valve_3b]
  sequences:
    - delay: "00:01"
      schedules:
        - name: Sunrise
          time:
            sun: sunrise
      zones:
        - zone_id: 2
        - zone_id: 1
"""

GEMISCHT = """
controllers:
  name: Garten
  entity_id: switch.pump
  preamble: 5
  zones:
    name: Beet
    entity_id: switch.valve_beet
  sequences:
    name: Morgens
    delay: {seconds: 30}
    zones:
      zone_id: 1
      duration: "00:15"
    schedules:
      - name: Früh
        time: "05:30"
        weekday: mon
        month: jun
      - name: Abend
        time: {sun: sunset, before: "00:30"}
      - name: Cron
        time: {cron: "0 4 * * *"}
"""


def schreibweisen():
    for mit_schema in (True, False):
        art = "mit IU-Schema" if mit_schema else "ohne IU-Schema"
        gesperrt = "custom_components.irrigation_unlimited.schema"
        alt = sys.modules.get(gesperrt)
        if not mit_schema:
            sys.modules[gesperrt] = None  # → ImportError
        try:
            e = ein.aus_iu_konfig(loader.parse_yaml(EINZELN))["controller"]
            pruefe(f"Übernahme Controller ohne „-“ ({art})",
                   len(e) == 1 and e[0]["name"] == "Beregnung"
                   and [(z["name"], z["ventile"]) for z in e[0]["zonen"]]
                   == [("Terrasse", ["switch.valve_1"]), ("Rasen", ["switch.valve_3", "switch.valve_3b"])]
                   and [sz["zone"] for sz in e[0]["sequenzen"][0]["zonen"]] == ["c1z2", "c1z1"]
                   and e[0]["sequenzen"][0]["pause_s"] == 60
                   and e[0]["sequenzen"][0]["plaene"][0]["zeit"]["bezug"] == "sonnenaufgang")
            g = ein.aus_iu_konfig(loader.parse_yaml(GEMISCHT))["controller"]
            s = g[0]["sequenzen"][0] if g else {}
            p = s.get("plaene", [])
            pruefe(f"Übernahme gemischter Schreibweisen ({art})",
                   len(g) == 1 and g[0]["pumpe"]["entity_id"] == "switch.pump" and g[0]["pumpe"]["vorlauf_s"] == 5
                   and [z["name"] for z in g[0]["zonen"]] == ["Beet"] and g[0]["zonen"][0]["standard_min"] == 15
                   and s["pause_s"] == 30 and len(p) == 3
                   and p[0]["zeit"] == {"bezug": "uhrzeit", "versatz_min": 120, "uhrzeit": "05:30"}
                   and p[0]["tage"] == ["mon"] and p[0]["monate"] == ["jun"]
                   and p[1]["zeit"]["bezug"] == "sonnenuntergang" and p[1]["zeit"]["versatz_min"] == -30
                   and p[2]["zeit"]["uhrzeit"] == "06:00")
        except Exception as err:  # noqa: BLE001
            pruefe(f"Übernahme Schreibweisen ({art})", False, repr(err))
        finally:
            if alt is None:
                sys.modules.pop(gesperrt, None)
            else:
                sys.modules[gesperrt] = alt


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

    c1, c2, c3 = z["controllers"]
    pruefe("3 Controller, 2 + 1 + 1 Sequenzen", len(c1["sequences"]) == 2 and len(c2["sequences"]) == 1 and len(c3["sequences"]) == 1)
    pruefe("Wasseranschluss: ohne Pumpe, Vor-/Nachlauf in IU",
           not {"entity_id", "entity_states", "check_back", "preamble", "postamble"} & set(c3) and len(c3["zones"]) == 2)
    pruefe("Wasseranschluss: kein Wasserhahn-Betrieb", daten["controller"][2]["zonen"][1]["wasserhahn"] is False
           and c3["sequences"][0]["zones"][1]["enabled"] is True)
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
           and zu["sequenzen"]["s2"].endswith("c1_s2") and zu["zonen"]["pots"].endswith("c3_z1"))
    umgestellt = copy.deepcopy(daten)
    umgestellt["controller"][0]["anschluss"] = "leitung"
    u = iu_yaml.erzeugen(ein.pruefen(umgestellt))["controllers"][0]
    pruefe("Pumpe → Wasseranschluss: Pumpe nicht mehr in IU, Einstellung bleibt",
           "entity_id" not in u and ein.pruefen(umgestellt)["controller"][0]["pumpe"]["entity_id"] == "switch.garden_pump")
    ohne = copy.deepcopy(daten)
    ohne["controller"][0]["pumpe"]["entity_id"] = None
    pruefe("Pumpe ohne Schalter fehlt in IU", [c["name"] for c in iu_yaml.erzeugen(ein.pruefen(ohne))["controllers"]] == ["Front yard", "Patio"])

    # 2. Übernahme der erzeugten Konfiguration
    neu = ein.aus_iu_konfig(z)
    pruefe("Übernahme: ohne Pumpe → Wasseranschluss", [c["anschluss"] for c in neu["controller"]] == ["pumpe", "pumpe", "leitung"])
    for alt_c, neu_c in zip(daten["controller"], neu["controller"]):
        pruefe(f"Übernahme {alt_c['name']}: Pumpe, Zonen, Ventile",
               neu_c["pumpe"].get("entity_id") == alt_c["pumpe"].get("entity_id")
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
    schreibweisen()
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
        ("unbekannter Anschluss", lambda d: d["controller"][2].update(anschluss="brunnen")),
        ("negativer Wasserpreis", lambda d: d["controller"][2]["wasser"].update(preis_m3=-1)),
        ("Logo-Link javascript:", lambda d: d.update(anzeige={"logo_link": "javascript:alert(1)"})),
        ("Logo-Link //host", lambda d: d.update(anzeige={"logo_link": "//example.org"})),
    ):
        d = copy.deepcopy(daten)
        kaputt(d)
        try:
            ein.pruefen(d)
            pruefe(f"abgewiesen: {name}", False)
        except vol.Invalid as err:
            pruefe(f"abgewiesen: {name}", True, str(err)[:70])
    for ziel in ("/local_tunet_dev", "https://example.org/x"):
        d = copy.deepcopy(daten)
        d["anzeige"] = {"logo_link": ziel}
        pruefe(f"Logo-Link erlaubt: {ziel}", ein.pruefen(d)["anzeige"]["logo_link"] == ziel)
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
