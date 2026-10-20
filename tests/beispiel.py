"""Beispielanlage für die Tests: zwei Controller mit Pumpe, einer am
Wasseranschluss mit Zähler und Preisen, mehrere Sequenzen, alle Arten von
Startzeiten, eine Zone als Wasserhahn."""

import sys
from pathlib import Path

STAMM = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STAMM))

from custom_components.iu_irrigation_dashboard import einstellungen as ein  # noqa: E402


def beispiel() -> dict:
    return ein.pruefen({
        "version": 2,
        "controller": [
            {
                "id": "c1", "name": "Garden",
                "pumpe": {"entity_id": "switch.garden_pump", "leistung": "sensor.garden_pump_power", "tagbetrieb": False,
                          "energie": "sensor.garden_pump_energy", "strompreis_kwh": 0.32},
                "zonen": [
                    {"id": "lawn", "name": "Lawn", "ventile": ["switch.valve_lawn"], "standard_min": 20},
                    {"id": "beds", "name": "Beds", "ventile": ["switch.valve_beds", "valve.beds_2"], "standard_min": 15, "faktor": 50},
                    {"id": "hedge", "name": "Hedge", "ventile": ["switch.valve_hedge"], "standard_min": 25, "leistung_mm_h": 12},
                    {"id": "tap", "name": "Greenhouse", "ventile": ["switch.valve_greenhouse"], "standard_min": 10,
                     "wasserhahn": True, "betrieb": "wasserhahn", "regen": False},
                ],
                "sequenzen": [
                    {"id": "s1", "name": "Morning",
                     "zonen": [{"zone": "lawn"}, {"zone": "beds", "dauer_min": 10}, {"zone": "hedge", "aktiv": False}, {"zone": "tap"}],
                     "plaene": [
                         {"key": "summer", "name": "Summer", "monate": ["jun", "jul", "aug"], "tage": ["mon", "wed", "fri"],
                          "zeit": {"bezug": "sonnenaufgang", "versatz_min": -45}, "laufzeit": 100},
                         {"key": "spring", "name": "Spring", "monate": ["apr", "may"], "tage": ["sat"],
                          "zeit": {"bezug": "sonnenaufgang", "versatz_min": 90}, "laufzeit": 80},
                     ]},
                    {"id": "s2", "name": "Evening", "pause_s": 5, "wetter": False,
                     "zonen": [{"zone": "beds", "dauer_min": 7}, {"zone": "lawn"}],
                     "plaene": [
                         {"key": "dusk", "name": "Dusk", "monate": ["jul"], "tage": ["tue"],
                          "zeit": {"bezug": "sonnenuntergang", "versatz_min": 30}},
                         {"key": "fixed", "name": "Fixed", "monate": ["aug"], "tage": ["sun"],
                          "zeit": {"bezug": "uhrzeit", "uhrzeit": "05:30"}},
                     ]},
                ],
            },
            {
                "id": "c2", "name": "Front yard",
                "pumpe": {"entity_id": "switch.front_pump"},
                "zonen": [{"id": "front", "name": "Front lawn", "ventile": ["switch.valve_front"], "standard_min": 15}],
                "sequenzen": [{"id": "s3", "name": "Front", "zonen": [{"zone": "front"}],
                               "plaene": [{"key": "all", "name": "All year", "monate": ein.MONATE, "tage": ["thu"]}]}],
            },
            {
                "id": "c3", "name": "Patio", "anschluss": "leitung",
                "wasser": {"zaehler": "sensor.water_meter", "grundpreis_monat": 2.5, "preis_m3": 2.1, "abwasser_m3": 2.6},
                "zonen": [{"id": "pots", "name": "Pots", "ventile": ["valve.pots"], "standard_min": 5},
                          {"id": "herbs", "name": "Herbs", "ventile": ["switch.valve_herbs"], "standard_min": 8,
                           "wasserhahn": True, "betrieb": "wasserhahn"}],
                "sequenzen": [{"id": "s4", "name": "Patio", "zonen": [{"zone": "pots"}, {"zone": "herbs"}],
                               "plaene": [{"key": "daily", "name": "Daily", "monate": ["jun", "jul"], "tage": ein.WOCHENTAGE,
                                           "zeit": {"bezug": "uhrzeit", "uhrzeit": "07:00"}}]}],
            },
        ],
        "wetter": {"regen": "sensor.rain_total", "regenrate": "sensor.rain_rate", "prognose": "weather.home",
                   "temperatur": "sensor.outdoor_temperature", "feuchte": "sensor.outdoor_humidity",
                   "wind": "sensor.wind_speed", "strahlung": "sensor.solar_radiation"},
    })
