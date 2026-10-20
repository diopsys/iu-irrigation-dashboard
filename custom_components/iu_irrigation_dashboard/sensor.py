"""Sensoren (Namen nach HA-Sprache beim Anlegen).

Zonen          Anzahl Zonen, Attribut „zonen“
Laufzeit <Z>   Laufminuten je Zone (total_increasing → Langzeitstatistik),
               Attribut zone_id
Wasser <Z>     Liter je Zone am Wasseranschluss mit Zähler (total_increasing),
               Attribut wasser_zone
Verdunstung    ET₀ gestern (mm); Attribute: Prognose, Regen heute/24 h,
               Bilanz und Faktor je Zone
Automatik-/manuelle Läufe   Anzahl (total_increasing), Attribut laeufe
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_EINSTELLUNGEN
from .iu_yaml import zuordnung
from .steuerung import wasser_zaehler

# Namen beim Anlegen (ergeben die Entitäts-IDs); Deutsch nur bei deutscher HA-Sprache
NAMEN = {
    "de": {"zonen": "Beregnung Zonen", "laufzeit": "Beregnung Laufzeit {zone}", "wasser": "Beregnung Wasser {zone}",
           "verdunstung": "Beregnung Verdunstung",
           "automatik": "Beregnung Automatikläufe", "manuell": "Beregnung manuelle Läufe"},
    "en": {"zonen": "Irrigation zones", "laufzeit": "Irrigation run time {zone}", "wasser": "Irrigation water {zone}",
           "verdunstung": "Irrigation evapotranspiration",
           "automatik": "Irrigation automatic runs", "manuell": "Irrigation manual runs"},
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    vorhanden: set[str] = set()
    wasser_vorhanden: set[str] = set()
    namen = NAMEN["de" if (hass.config.language or "").startswith("de") else "en"]

    @callback
    def _zonen_ergaenzen() -> None:
        """Für neu angelegte Zonen Laufzeit-Sensoren anlegen, am Wasseranschluss
        mit Zähler auch Wasser-Sensoren."""
        neu = []
        for ctl in entry.runtime_data.daten["controller"]:
            for zone in ctl["zonen"]:
                if zone["id"] not in vorhanden:
                    vorhanden.add(zone["id"])
                    neu.append(LaufzeitSensor(entry, zone["id"], namen["laufzeit"].format(zone=zone["name"])))
                if wasser_zaehler(ctl) and zone["id"] not in wasser_vorhanden:
                    wasser_vorhanden.add(zone["id"])
                    neu.append(WasserSensor(entry, zone["id"], namen["wasser"].format(zone=zone["name"])))
        if neu:
            async_add_entities(neu)

    async_add_entities([ZonenSensor(entry, namen["zonen"]), VerdunstungSensor(entry, namen["verdunstung"]),
                        AnzahlSensor(entry, "automatik", namen["automatik"]),
                        AnzahlSensor(entry, "manuell", namen["manuell"])])
    _zonen_ergaenzen()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_EINSTELLUNGEN, _zonen_ergaenzen))


class _Basis(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    @property
    def _b(self):
        return self._entry.runtime_data

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_EINSTELLUNGEN, self.async_write_ha_state))


class ZonenSensor(_Basis):
    _attr_icon = "mdi:sprinkler-variant"

    def __init__(self, entry: ConfigEntry, name: str) -> None:
        super().__init__(entry)
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_zonen"

    @property
    def native_value(self) -> int:
        return sum(len(c["zonen"]) for c in self._b.daten["controller"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        zu = zuordnung(self._b.daten)
        return {
            "zonen": [
                {"id": z["id"], "name": z["name"], "controller": c["name"], "standard": z["standard_min"],
                 "nr": zu["zone_nr"].get(z["id"]), "iu": zu["zonen"].get(z["id"]),
                 "wasserhahn": z["wasserhahn"], "betrieb": z["betrieb"], "regen": z["regen"], "ventile": z["ventile"]}
                for c in self._b.daten["controller"] for z in c["zonen"]
            ]
        }


class LaufzeitSensor(_Basis):
    _attr_icon = "mdi:timer-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, entry: ConfigEntry, zone_id: str, name: str) -> None:
        super().__init__(entry)
        self._zone_id = zone_id
        self._attr_unique_id = f"{DOMAIN}_laufzeit_{zone_id}"
        # Name nur beim Anlegen – ergibt die Entitäts-ID (wie die früheren Zähler)
        self._attr_name = name

    @property
    def available(self) -> bool:
        return any(z["id"] == self._zone_id for c in self._b.daten["controller"] for z in c["zonen"])

    @property
    def native_value(self) -> float:
        return round(self._b.bilanz.daten["minuten"].get(self._zone_id, 0.0), 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Das Panel findet den Zähler über die Zonen-ID (auch nach Umbenennen)
        return {"zone_id": self._zone_id}


class WasserSensor(_Basis):
    _attr_icon = "mdi:water-outline"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_suggested_display_precision = 0

    def __init__(self, entry: ConfigEntry, zone_id: str, name: str) -> None:
        super().__init__(entry)
        self._zone_id = zone_id
        self._attr_unique_id = f"{DOMAIN}_wasser_{zone_id}"
        self._attr_name = name

    @property
    def available(self) -> bool:
        return any(z["id"] == self._zone_id and wasser_zaehler(c)
                   for c in self._b.daten["controller"] for z in c["zonen"])

    @property
    def native_value(self) -> float:
        return round(self._b.bilanz.daten["wasser_l"].get(self._zone_id, 0.0), 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Das Panel findet den Sensor über die Zonen-ID (auch nach Umbenennen)
        return {"wasser_zone": self._zone_id}


class VerdunstungSensor(_Basis):
    _attr_icon = "mdi:weather-sunny-alert"
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, name: str) -> None:
        super().__init__(entry)
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_verdunstung"

    @property
    def native_value(self) -> float | None:
        tage = self._b.bilanz.daten["tage"]
        return tage[-1]["et0"] if tage else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        a = self._b.bilanz.aktuell or {}
        return {
            "et0_prognose_24h": a.get("et0_prognose"),
            "regen_heute": a.get("regen_heute"),
            "regen_prognose_24h": a.get("regen_prognose"),
            "regnet": a.get("regnet"),
            "zonen": a.get("zonen", {}),
        }


class AnzahlSensor(_Basis):
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, entry: ConfigEntry, art: str, name: str) -> None:
        super().__init__(entry)
        self._art = art
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_anzahl_{art}"

    @property
    def native_value(self) -> int:
        return int(self._b.bilanz.daten["anzahl"].get(self._art, 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Das Panel findet den Zähler über dieses Attribut (unabhängig von der ID)
        return {"laeufe": self._art}
