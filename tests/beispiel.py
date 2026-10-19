"""Beispielanlage für die Tests: zwei Controller, mehrere Sequenzen, alle
Arten von Startzeiten, eine Zone als Wasserhahn."""

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
                "pumpe": {"entity_id": "switch.garden_pump", "leistung": "sensor.garden_pump_power", "tagbetrieb": False},
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
        ],
        "wetter": {"regen": "sensor.rain_total", "regenrate": "sensor.rain_rate", "prognose": "weather.home",
                   "temperatur": "sensor.outdoor_temperature", "feuchte": "sensor.outdoor_humidity",
                   "wind": "sensor.wind_speed", "strahlung": "sensor.solar_radiation"},
    })
