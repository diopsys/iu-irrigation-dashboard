"""Einstellungen: Aufbau, Prüfung, Übernahme einer vorhandenen IU-Konfiguration.

Mehrere Controller (je eine Pumpe) mit Zonen und Sequenzen, Sequenzen mit
eigenen Plänen; Wetter/Wasserbilanz global. Alle Einstellungen liegen als
ein JSON-Objekt im HA-Speicher (.storage/iu_irrigation_dashboard.einstellungen)
und werden im Panel bearbeitet.

controller[]: id, name, pumpe{…, tagbetrieb}, zonen[], sequenzen[]
  zonen[]:     id, name, ventile[], standard_min, wasserhahn, betrieb,
               regen, faktor, leistung_mm_h (optional)
  sequenzen[]: id, name, pause_s, wetter, zonen[{zone, dauer_min, aktiv}],
               plaene[{key, name, monate, tage, zeit{bezug, versatz_min,
               uhrzeit}, laufzeit}]
wetter: Quellen, Standort, Wasserbilanz-Parameter, aktiv, grundfaktor
iu: historie
"""

from __future__ import annotations

import logging
import re
import uuid
from copy import deepcopy
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import BETRIEB_BEREGNUNG, BETRIEB_WASSERHAHN, IU_DOMAIN, MONATE, WOCHENTAGE

_LOGGER = logging.getLogger(__name__)

_ENTITY = vol.Any(None, cv.entity_id)
_SCHLUESSEL = vol.All(cv.string, vol.Match(r"^[a-z0-9]+(_[a-z0-9]+)*$"))

BEZUG_AUFGANG = "sonnenaufgang"
BEZUG_UNTERGANG = "sonnenuntergang"
BEZUG_UHRZEIT = "uhrzeit"

STANDARD_WETTER = {
    "aktiv": True,
    "grundfaktor": 100,
    "regen": None,
    "regenrate": None,
    "regensensor": None,
    "prognose": None,
    "temperatur": None,
    "feuchte": None,
    "wind": None,
    "strahlung": None,
    "wind_hoehe_m": 2.0,
    "hoehe_m": None,
    "referenz_mm": 3.0,
    "speicher_mm": 10.0,
    "regen_wirksam": 80,
    "max_faktor": 200,
    "krs": 0.16,
}

STANDARD = {
    "version": 2,
    "controller": [],
    "wetter": STANDARD_WETTER,
    "iu": {"historie": False},
}

_ID = vol.All(cv.string, vol.Match(r"^[a-z0-9]+$"))
_UHRZEIT = vol.All(cv.string, vol.Match(r"^([01]\d|2[0-3]):[0-5]\d$"))

ZEIT_SCHEMA = vol.Schema(
    {
        vol.Optional("bezug", default=BEZUG_AUFGANG): vol.In([BEZUG_AUFGANG, BEZUG_UNTERGANG, BEZUG_UHRZEIT]),
        # negativ = vor Sonnenauf-/-untergang
        vol.Optional("versatz_min", default=120): vol.All(vol.Coerce(int), vol.Range(min=-720, max=720)),
        vol.Optional("uhrzeit", default="06:00"): _UHRZEIT,
    }
)

PLAN_SCHEMA = vol.Schema(
    {
        vol.Required("key"): _SCHLUESSEL,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=30)),
        vol.Optional("monate", default=[]): [vol.In(MONATE)],
        vol.Optional("tage", default=[]): [vol.In(WOCHENTAGE)],
        vol.Optional("zeit", default={}): ZEIT_SCHEMA,
        vol.Optional("laufzeit", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=200)),
    }
)

SEQ_ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("zone"): _ID,
        vol.Optional("dauer_min", default=None): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=240))),
        vol.Optional("aktiv", default=True): cv.boolean,
    }
)

SEQUENZ_SCHEMA = vol.Schema(
    {
        vol.Required("id"): _ID,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=40)),
        vol.Optional("pause_s", default=1): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
        vol.Optional("wetter", default=True): cv.boolean,
        vol.Optional("zonen", default=[]): [SEQ_ZONE_SCHEMA],
        vol.Optional("plaene", default=[]): [PLAN_SCHEMA],
    }
)

ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("id"): _ID,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=40)),
        vol.Required("ventile"): vol.All(cv.ensure_list, [cv.entity_id], vol.Length(min=1)),
        vol.Optional("standard_min", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=240)),
        vol.Optional("wasserhahn", default=False): cv.boolean,
        vol.Optional("betrieb", default=BETRIEB_BEREGNUNG): vol.In([BETRIEB_WASSERHAHN, BETRIEB_BEREGNUNG]),
        vol.Optional("regen", default=True): cv.boolean,
        vol.Optional("faktor", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=300)),
        vol.Optional("leistung_mm_h", default=None): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0.1, max=200))),
    }
)

PUMPE_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): _ENTITY,
        vol.Optional("leistung"): _ENTITY,
        vol.Optional("energie"): _ENTITY,
        vol.Optional("schwelle_w", default=50): vol.All(vol.Coerce(float), vol.Range(min=0, max=5000)),
        vol.Optional("vorlauf_s", default=2): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
        vol.Optional("nachlauf_s", default=2): vol.All(vol.Coerce(int), vol.Range(min=0, max=600)),
        # Pumpe von Sonnenauf- bis -untergang an (z. B. für Wasserhähne)
        vol.Optional("tagbetrieb", default=False): cv.boolean,
    }
)

CONTROLLER_SCHEMA = vol.Schema(
    {
        vol.Required("id"): _ID,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=40)),
        vol.Optional("pumpe", default={}): PUMPE_SCHEMA,
        vol.Optional("zonen", default=[]): [ZONE_SCHEMA],
        vol.Optional("sequenzen", default=[]): [SEQUENZ_SCHEMA],
    }
)

WETTER_SCHEMA = vol.Schema(
    {
        vol.Optional("aktiv", default=True): cv.boolean,
        vol.Optional("grundfaktor", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=200)),
        **{vol.Optional(k, default=STANDARD_WETTER[k]): _ENTITY
           for k in ("regen", "regenrate", "regensensor", "prognose", "temperatur", "feuchte", "wind", "strahlung")},
        vol.Optional("wind_hoehe_m", default=2.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=30)),
        vol.Optional("hoehe_m", default=None): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=-100, max=5000))),
        vol.Optional("referenz_mm", default=3.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=50)),
        vol.Optional("speicher_mm", default=10.0): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Optional("regen_wirksam", default=80): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Optional("max_faktor", default=200): vol.All(vol.Coerce(int), vol.Range(min=100, max=400)),
        # Einstrahlung aus der Temperaturspanne, wenn kein Sensor eingetragen ist
        vol.Optional("krs", default=0.16): vol.All(vol.Coerce(float), vol.Range(min=0.05, max=0.3)),
    }
)

SCHEMA = vol.Schema(
    {
        vol.Optional("version", default=2): 2,
        vol.Optional("controller", default=[]): [CONTROLLER_SCHEMA],
        vol.Optional("wetter", default={}): WETTER_SCHEMA,
        vol.Optional("iu", default={}): vol.Schema({vol.Optional("historie", default=False): cv.boolean},
                                                   extra=vol.REMOVE_EXTRA),
    },
    extra=vol.REMOVE_EXTRA,
)


def pruefen(daten: dict[str, Any]) -> dict[str, Any]:
    """Einstellungen (Version 2) prüfen und normalisieren (wirft vol.Invalid)."""
    daten = SCHEMA(deepcopy(daten))
    ids: set[str] = set()

    def eindeutig(wert: str, art: str) -> None:
        if wert in ids:
            raise vol.Invalid(f"{art}-ID {wert} ist doppelt")
        ids.add(wert)

    for ctl in daten["controller"]:
        eindeutig(ctl["id"], "Controller")
        zonen_ids = set()
        for zone in ctl["zonen"]:
            eindeutig(zone["id"], "Zonen")
            zonen_ids.add(zone["id"])
            if not zone["wasserhahn"]:
                zone["betrieb"] = BETRIEB_BEREGNUNG
        for seq in ctl["sequenzen"]:
            eindeutig(seq["id"], "Sequenz")
            for sz in seq["zonen"]:
                if sz["zone"] not in zonen_ids:
                    raise vol.Invalid(f"Sequenz „{seq['name']}“: Zone {sz['zone']} gehört nicht zu „{ctl['name']}“")
            keys = [p["key"] for p in seq["plaene"]]
            if len(keys) != len(set(keys)):
                raise vol.Invalid(f"Sequenz „{seq['name']}“: Plan-Schlüssel doppelt")
            gesehen: dict[str, str] = {}
            for plan in seq["plaene"]:
                plan["monate"] = [m for m in MONATE if m in plan["monate"]]
                plan["tage"] = [t for t in WOCHENTAGE if t in plan["tage"]]
                for monat in plan["monate"]:
                    if monat in gesehen:
                        raise vol.Invalid(f"Sequenz „{seq['name']}“: Monat {monat} ist in „{gesehen[monat]}“ "
                                          f"und „{plan['name']}“")
                    gesehen[monat] = plan["name"]
    # eine Pumpe gehört zu genau einem Controller
    pumpen = [c["pumpe"].get("entity_id") for c in daten["controller"] if c["pumpe"].get("entity_id")]
    if len(pumpen) != len(set(pumpen)):
        raise vol.Invalid("Eine Pumpe ist mehreren Controllern zugeordnet")
    return daten


def neue_id(praefix: str) -> str:
    return praefix + uuid.uuid4().hex[:8]


# ══ Übernahme einer vorhandenen IU-Konfiguration (erster Start) ══════

def _liste(wert: Any) -> list[str]:
    if wert is None:
        return []
    if isinstance(wert, (list, tuple)):
        return [str(w) for w in wert]
    return [str(wert)]


def _sekunden(wert: Any, standard: int) -> int:
    try:
        return round(cv.time_period(wert).total_seconds())
    except (vol.Invalid, TypeError, ValueError):
        return standard


def _schluessel(text: str) -> str:
    text = text.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "plan"


def _plan_zeit(zeit: Any) -> dict[str, Any]:
    """IU-Startzeit (HH:MM[:SS] oder {sun, before|after}) → zeit."""
    if isinstance(zeit, dict):
        bezug = BEZUG_UNTERGANG if str(zeit.get("sun", "sunrise")) == "sunset" else BEZUG_AUFGANG
        if zeit.get("before") is not None:
            versatz = -_sekunden(zeit["before"], 0) // 60
        else:
            versatz = _sekunden(zeit.get("after", 0), 0) // 60
        return {"bezug": bezug, "versatz_min": max(-720, min(720, versatz)), "uhrzeit": "06:00"}
    sek = _sekunden(zeit, 6 * 3600) % 86400
    return {"bezug": BEZUG_UHRZEIT, "versatz_min": 120, "uhrzeit": f"{sek // 3600:02d}:{sek % 3600 // 60:02d}"}


def aus_iu_konfig(iu: dict[str, Any] | None, hass: HomeAssistant | None = None) -> dict[str, Any]:
    """Einstellungen aus einer IU-Konfiguration (Inhalt unter irrigation_unlimited:).

    Übernimmt je Controller Pumpe, Vor-/Nachlauf und Zonen, je Sequenz die
    Zonen mit Dauer und Freigabe sowie die Pläne (Monate, Tage, Startzeit).
    Ohne IU-Konfiguration bleiben die Einstellungen leer und werden im Panel
    eingetragen.
    """
    daten = deepcopy(STANDARD)
    pumpen: set[str] = set()
    for ci, c in enumerate((iu or {}).get("controllers") or [], start=1):
        cid = f"c{ci}"
        pumpe_ids = _liste(c.get("entity_id"))
        pumpe = pumpe_ids[0] if pumpe_ids and pumpe_ids[0] not in pumpen else None
        if pumpe:
            pumpen.add(pumpe)
        ctl: dict[str, Any] = {
            "id": cid,
            "name": str(c.get("name") or f"Controller {ci}")[:40],
            "pumpe": {"entity_id": pumpe, "vorlauf_s": min(600, _sekunden(c.get("preamble"), 2)),
                      "nachlauf_s": min(600, _sekunden(c.get("postamble"), 2))},
            "zonen": [],
            "sequenzen": [],
        }
        if pumpe and hass is not None:
            objekt = pumpe.split(".", 1)[1]
            for feld, kandidaten in (("leistung", ("_energy_power", "_power")), ("energie", ("_energy_total", "_energy"))):
                for endung in kandidaten:
                    if hass.states.get(f"sensor.{objekt}{endung}"):
                        ctl["pumpe"][feld] = f"sensor.{objekt}{endung}"
                        break

        # Zonen: IU nummeriert nach Position; zone_id ist optional
        nach_iu_id: dict[str, str] = {}
        for zi, z in enumerate(c.get("zones") or [], start=1):
            ventile = _liste(z.get("entity_id"))
            if not ventile:
                continue
            zid = f"{cid}z{zi}"
            nach_iu_id[str(z.get("zone_id", zi))] = zid
            nach_iu_id.setdefault(str(zi), zid)
            ctl["zonen"].append({
                "id": zid,
                "name": re.sub(r"\s+", " ", str(z.get("name") or f"Zone {zi}")).strip()[:40],
                "ventile": ventile,
            })

        # Sequenzen: Standardlaufzeit einer Zone = ihre erste Dauer in einer Sequenz
        standard: dict[str, int] = {}
        for si, s in enumerate(c.get("sequences") or [], start=1):
            seq_dauer = _sekunden(s.get("duration"), 20 * 60) // 60 or 20
            eintraege = []
            for sz in s.get("zones") or []:
                minuten = max(1, min(240, _sekunden(sz.get("duration"), seq_dauer * 60) // 60 or seq_dauer))
                for iu_id in _liste(sz.get("zone_id")):
                    zid = nach_iu_id.get(iu_id)
                    if zid is None:
                        continue
                    standard.setdefault(zid, minuten)
                    eintraege.append({"zone": zid, "dauer_min": minuten, "aktiv": sz.get("enabled", True) is not False})
            plaene = []
            gesehen: set[str] = set()
            for pi, p in enumerate(s.get("schedules") or [], start=1):
                key = _schluessel(str(p.get("schedule_id") or p.get("name") or f"plan{pi}"))
                while key in {x["key"] for x in plaene}:
                    key = f"{key}_{pi}"
                monate = [m for m in (_liste(p.get("month")) or MONATE) if m in MONATE and m not in gesehen]
                gesehen.update(monate)
                aktiv = p.get("enabled", True) is not False
                plaene.append({
                    "key": key,
                    "name": str(p.get("name") or f"Plan {pi}")[:30],
                    "monate": monate if aktiv else [],
                    "tage": [t for t in (_liste(p.get("weekday")) or WOCHENTAGE) if t in WOCHENTAGE],
                    "zeit": _plan_zeit(p.get("time")),
                })
            ctl["sequenzen"].append({
                "id": f"{cid}s{si}",
                "name": str(s.get("name") or f"Sequenz {si}")[:40],
                "pause_s": min(600, _sekunden(s.get("delay"), 1)),
                "zonen": eintraege,
                "plaene": plaene,
            })
        for zone in ctl["zonen"]:
            zone["standard_min"] = standard.get(zone["id"], 20)
        # Dauer = Standard → leer (folgt der Standardlaufzeit der Zone)
        for seq in ctl["sequenzen"]:
            for sz in seq["zonen"]:
                if sz["dauer_min"] == standard.get(sz["zone"]):
                    sz["dauer_min"] = None
        daten["controller"].append(ctl)
    return pruefen(daten)


async def bestand_uebernehmen(hass: HomeAssistant) -> dict[str, Any]:
    """Erste Einstellungen aus der IU-Konfiguration in configuration.yaml
    (samt Packages); ohne sie leer."""
    from homeassistant import config as conf_util  # pylint: disable=import-outside-toplevel

    try:
        conf = await conf_util.async_hass_config_yaml(hass)
        iu = conf.get(IU_DOMAIN)
        return aus_iu_konfig(iu if isinstance(iu, dict) else None, hass)
    except Exception as err:  # noqa: BLE001 – Übernahme ist optional
        _LOGGER.warning("Vorhandene Irrigation-Unlimited-Konfiguration nicht übernommen: %s", err)
        return deepcopy(STANDARD)


def laden(gespeichert: dict[str, Any], hass: HomeAssistant | None = None) -> dict[str, Any]:  # noqa: ARG001
    """Gespeicherte Einstellungen laden (wirft vol.Invalid)."""
    return pruefen(gespeichert)
