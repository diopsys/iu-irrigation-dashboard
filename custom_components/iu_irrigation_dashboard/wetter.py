"""Wetter und Wasserbilanz.

Bodenspeicher je Zone B (mm, ≤ Speicher S): täglich (für den Vortag)
    B ← min(S, B + wirksam × Regen − ET₀)     (Regen nur bei „Regen wirkt“)
ein Lauf schreibt die verteilte Menge gut:
    B ← min(S, B + Minuten / Standardminuten × R)
Faktor der Zone (0 … max):
    Bedarf = −B + ET₀(Prognose 24 h) − wirksam × (Regen heute + Prognose 24 h)
    Faktor = Bedarf / R,  R = Beregnungsleistung × Standardzeit oder Referenz
Regenmengen über 100 mm/Tag gelten als Messfehler (Zählersprung).
Mit der smarten Laufzeit (experimentell, smart.py) je Zone mit Kc, eigenem
Speicher (0 = voll, −S = leer) und Laufzeit in Minuten; am Wasserzähler wird
jede gemeldete Menge sofort gutgeschrieben (Liter ÷ Fläche).

Laufdaten (Bilanz, verarbeitete Tage, Zähler, letzte Läufe) liegen in
.storage/beregnung.laufdaten.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import et0, smart
from .const import LAUFDATEN_KEY

_LOGGER = logging.getLogger(__name__)

MAX_NACHHOLEN_TAGE = 14
REGEN_MESSFEHLER_MM = 100
BILANZ_MIN = -100.0


def _zahl(wert: Any) -> float | None:
    try:
        f = float(wert)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _wind_ms(wert: float, einheit: str | None) -> float:
    einheit = (einheit or "km/h").lower()
    if einheit in ("m/s",):
        return wert
    if einheit in ("mph",):
        return wert * 0.44704
    if einheit in ("kn", "knots"):
        return wert * 0.514444
    return wert / 3.6


def _temp_c(wert: float, einheit: str | None) -> float:
    return (wert - 32) * 5 / 9 if (einheit or "").endswith("F") else wert


class Wasserbilanz:
    """Laufdaten und Wetterberechnung (eine Instanz je Integration)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store = Store(hass, 1, LAUFDATEN_KEY)
        self.daten: dict[str, Any] = {
            "letzter_tag": None,      # zuletzt verarbeiteter Tag (ISO)
            "regen_mitternacht": None,  # Regenzähler um 0 Uhr
            "tage": [],               # [{tag, et0, regen}] die letzten 30 Tage
            "bilanz": {},             # zone_id → mm
            "minuten": {},            # zone_id → Laufminuten gesamt
            "wasser_l": {},           # zone_id → Liter gesamt (Wasserzähler)
            "durchfluss": {},         # zone_id → [L/min der letzten Läufe] (Wasserzähler)
            "laeufe": {},             # seq_id/ctl_id → letzter Lauf
            "anzahl": {"automatik": 0, "manuell": 0},
        }
        # aktuelle Werte (nicht gespeichert)
        self.aktuell: dict[str, Any] = {}

    async def async_laden(self) -> None:
        gespeichert = await self._store.async_load()
        if gespeichert:
            self.daten.update(gespeichert)

    def speichern(self) -> None:
        self._store.async_delay_save(lambda: self.daten, 10)

    # ── Tageswerte aus der Langzeitstatistik ──────────────────────────
    async def _statistik(self, ids: list[str], start: datetime, ende: datetime, periode: str,
                         typen: set[str]) -> dict[str, list[dict[str, Any]]]:
        from homeassistant.components.recorder import get_instance  # pylint: disable=import-outside-toplevel
        from homeassistant.components.recorder.statistics import (  # pylint: disable=import-outside-toplevel
            statistics_during_period,
        )

        ids = [i for i in ids if i]
        if not ids:
            return {}
        return await get_instance(self.hass).async_add_executor_job(
            statistics_during_period, self.hass, start, ende, set(ids), periode, None, typen
        )

    def _einheit(self, entity_id: str | None) -> str | None:
        state = self.hass.states.get(entity_id) if entity_id else None
        return state.attributes.get("unit_of_measurement") if state else None

    def _standort(self, wetter: dict[str, Any]) -> tuple[float, float]:
        hoehe = wetter.get("hoehe_m")
        return self.hass.config.latitude, float(hoehe if hoehe is not None else (self.hass.config.elevation or 0))

    async def tag_auswerten(self, tag: date, wetter: dict[str, Any]) -> dict[str, float] | None:
        """ET₀ und Regen eines vergangenen Tages (None, wenn Daten fehlen)."""
        start = dt_util.start_of_local_day(tag)
        ende = start + timedelta(days=1)
        ids = [wetter.get(k) for k in ("temperatur", "feuchte", "wind", "strahlung")]
        werte = await self._statistik(ids, start, ende, "day", {"mean", "min", "max"})
        regen = await self._statistik([wetter.get("regen")], start, ende, "day", {"change"})

        def erster(eid: str | None) -> dict[str, Any] | None:
            liste = werte.get(eid) if eid else None
            return liste[0] if liste else None

        t, rh, wind, rs = (erster(wetter.get(k)) for k in ("temperatur", "feuchte", "wind", "strahlung"))
        regen_mm = 0.0
        if wetter.get("regen") and regen.get(wetter["regen"]):
            regen_mm = max(0.0, _zahl(regen[wetter["regen"]][0].get("change")) or 0.0)
        if regen_mm > REGEN_MESSFEHLER_MM:
            _LOGGER.warning("Regen %s: %.0f mm gilt als Messfehler", tag, regen_mm)
            regen_mm = 0.0
        if not t or t.get("min") is None or t.get("max") is None:
            return {"et0": None, "regen": regen_mm}
        breite, hoehe = self._standort(wetter)
        te = self._einheit(wetter.get("temperatur"))
        tmin, tmax = _temp_c(t["min"], te), _temp_c(t["max"], te)
        tag_im_jahr = tag.timetuple().tm_yday
        if rs and rs.get("mean") is not None:
            rs_mj = rs["mean"] * 0.0864
        else:
            # ohne Einstrahlungssensor: aus der Temperaturspanne (FAO-56 Gl. 50)
            ra = et0.extraterrestrische_strahlung(tag_im_jahr, breite)
            rs_mj = et0.strahlung_aus_temperatur(ra, tmin, tmax, hoehe, wetter.get("krs", 0.16))
        wert = et0.et0_tag(
            tmin, tmax,
            (rh or {}).get("mean") or 70.0,
            _wind_ms((wind or {}).get("mean") or 0.0, self._einheit(wetter.get("wind"))),
            rs_mj, tag_im_jahr, breite, hoehe,
            wind_messhoehe_m=wetter.get("wind_hoehe_m", 2.0),
            rh_min=(rh or {}).get("min"), rh_max=(rh or {}).get("max"),
        )
        return {"et0": round(wert, 2), "regen": round(regen_mm, 1)}

    async def nachholen(self, einstellungen: dict[str, Any]) -> bool:
        """Alle noch nicht verarbeiteten Tage bis gestern in die Bilanz
        übernehmen. True, wenn sich etwas geändert hat."""
        wetter = einstellungen["wetter"]
        if not wetter.get("temperatur"):
            # ohne Temperatur keine Verdunstung – Tage nicht als verarbeitet
            # buchen, damit sie nach dem Eintragen der Quellen nachgeholt werden
            return False
        heute = dt_util.now().date()
        gestern = heute - timedelta(days=1)
        # erster Start: die letzten 14 Tage, damit die Bilanz nicht bei 0 beginnt
        letzter = (date.fromisoformat(self.daten["letzter_tag"]) if self.daten["letzter_tag"]
                   else gestern - timedelta(days=MAX_NACHHOLEN_TAGE))
        tag = max(letzter + timedelta(days=1), gestern - timedelta(days=MAX_NACHHOLEN_TAGE - 1))
        geaendert = False
        while tag <= gestern:
            werte = await self.tag_auswerten(tag, wetter)
            if werte is not None:
                self._tag_buchen(tag, werte, einstellungen)
                geaendert = True
            tag += timedelta(days=1)
        if geaendert:
            self.daten["letzter_tag"] = gestern.isoformat()
            self.speichern()
        return geaendert

    def _tag_buchen(self, tag: date, werte: dict[str, float], einstellungen: dict[str, Any]) -> None:
        wetter = einstellungen["wetter"]
        et0_tag = werte["et0"]
        if et0_tag is None:
            # ohne Wetterdaten: Vortag als Schätzung
            et0_tag = self.daten["tage"][-1]["et0"] if self.daten["tage"] else 0.0
        self.daten["tage"] = [t for t in self.daten["tage"] if t["tag"] != tag.isoformat()][-29:] + [
            {"tag": tag.isoformat(), "et0": et0_tag, "regen": werte["regen"]}
        ]
        wirksam = wetter["regen_wirksam"] / 100
        mit_smart = smart.aktiv(einstellungen)
        for ctl in einstellungen["controller"]:
            for zone in ctl["zonen"]:
                b = self.daten["bilanz"].get(zone["id"], 0.0)
                regen = wirksam * werte["regen"] if zone["regen"] else 0.0
                if mit_smart:
                    # 0 = Boden voll, mehr versickert; höchstens der Speicher fehlt
                    b = smart.bilanz_begrenzen(b + regen - zone["smart"]["kc"] * et0_tag, zone, wetter)
                else:
                    b = max(BILANZ_MIN, min(wetter["speicher_mm"], b + regen - et0_tag))
                self.daten["bilanz"][zone["id"]] = round(b, 2)

    def lauf_gutschreiben(self, zone: dict[str, Any], minuten: float, einstellungen: dict[str, Any],
                          gutschrift: bool = True) -> None:
        """Gelaufene Minuten einer Zone: Zähler und Bodenspeicher. Ohne
        gutschrift nur der Zähler (die Menge kommt später vom Wasserzähler)."""
        zid = zone["id"]
        self.daten["minuten"][zid] = round(self.daten["minuten"].get(zid, 0.0) + minuten, 1)
        if gutschrift:
            wetter = einstellungen["wetter"]
            if smart.aktiv(einstellungen):
                mm = smart.gutschrift_mm(zone, minuten, wetter, self.daten["durchfluss"].get(zid))
            else:
                mm = minuten / max(1, zone["standard_min"]) * self.referenz(zone, wetter)
            self._gutschreiben(zone, mm, einstellungen)
        self.speichern()

    def wasser_gutschreiben(self, zone: dict[str, Any], mm: float, einstellungen: dict[str, Any]) -> None:
        """Gemessene Wassermenge eines Laufs (Liter ÷ Fläche) gutschreiben."""
        self._gutschreiben(zone, mm, einstellungen)
        self.speichern()

    def _gutschreiben(self, zone: dict[str, Any], mm: float, einstellungen: dict[str, Any]) -> None:
        wetter = einstellungen["wetter"]
        b = self.daten["bilanz"].get(zone["id"], 0.0) + mm
        if smart.aktiv(einstellungen):
            b = smart.bilanz_begrenzen(b, zone, wetter)
        else:
            b = min(wetter["speicher_mm"], b)
        self.daten["bilanz"][zone["id"]] = round(b, 2)

    def durchfluss_messen(self, zone_id: str, liter: float, minuten: float) -> None:
        """Durchfluss eines Laufs (L/min) für die gemessene Beregnungsleistung."""
        if liter <= 0 or minuten < 1:
            return
        liste = self.daten["durchfluss"].setdefault(zone_id, [])
        liste.append(round(liter / minuten, 2))
        del liste[:-smart.MESSUNGEN_MAX]
        self.speichern()

    @staticmethod
    def referenz(zone: dict[str, Any], wetter: dict[str, Any]) -> float:
        """Wassermenge (mm) der Standardlaufzeit dieser Zone."""
        if zone.get("leistung_mm_h"):
            return zone["leistung_mm_h"] * zone["standard_min"] / 60
        return wetter["referenz_mm"]

    # ── Heute und Prognose ────────────────────────────────────────────
    async def aktualisieren(self, einstellungen: dict[str, Any]) -> None:
        """Regen heute, Prognose 24 h und Faktoren je Zone neu berechnen."""
        hass = self.hass
        wetter = einstellungen["wetter"]
        jetzt = dt_util.now()

        # Regen heute = Zählerstand − Stand um Mitternacht
        regen_heute = 0.0
        stand = _zahl(hass.states.get(wetter["regen"]).state) if wetter.get("regen") and hass.states.get(wetter["regen"]) else None
        if stand is not None:
            mitternacht = self.daten.get("regen_mitternacht")
            if mitternacht is None or stand < mitternacht:
                self.daten["regen_mitternacht"] = mitternacht = stand
            regen_heute = max(0.0, stand - mitternacht)
            if regen_heute > REGEN_MESSFEHLER_MM:
                regen_heute = 0.0

        prognose = await self._prognose(wetter, jetzt)
        regnet = False
        if wetter.get("regensensor"):
            s = hass.states.get(wetter["regensensor"])
            regnet = s is not None and s.state == "on"
        if wetter.get("regenrate"):
            rate = _zahl(hass.states.get(wetter["regenrate"]).state) if hass.states.get(wetter["regenrate"]) else None
            regnet = regnet or bool(rate and rate > 0)

        et0_prog = prognose.get("et0")
        if et0_prog is None:
            et0_prog = self.daten["tage"][-1]["et0"] if self.daten["tage"] else 0.0
        wirksam = wetter["regen_wirksam"] / 100
        max_f = wetter["max_faktor"] / 100
        mit_smart = smart.aktiv(einstellungen)
        faktoren: dict[str, dict[str, Any]] = {}
        for ctl in einstellungen["controller"]:
            for zone in ctl["zonen"]:
                b = self.daten["bilanz"].get(zone["id"], 0.0)
                if mit_smart:
                    faktoren[zone["id"]] = smart.planen(
                        zone, b, regen_heute + prognose.get("regen", 0.0), regnet, wetter,
                        self.daten["durchfluss"].get(zone["id"]))
                    continue
                regen = wirksam * (regen_heute + prognose.get("regen", 0.0)) if zone["regen"] else 0.0
                bedarf = -b + et0_prog - regen
                r = self.referenz(zone, wetter)
                f = 0.0 if (zone["regen"] and regnet) else max(0.0, min(max_f, bedarf / r))
                faktoren[zone["id"]] = {"bilanz": round(b, 1), "bedarf": round(bedarf, 1),
                                        "referenz": round(r, 1), "faktor": round(f, 2)}
        self.aktuell = {
            "zeit": jetzt.isoformat(),
            "regen_heute": round(regen_heute, 1),
            "regnet": regnet,
            "et0_gestern": self.daten["tage"][-1]["et0"] if self.daten["tage"] else None,
            "et0_prognose": round(et0_prog, 2),
            "regen_prognose": round(prognose.get("regen", 0.0), 1),
            "prognose_stunden": prognose.get("stunden", []),
            "tage": self.daten["tage"][-14:],
            "zonen": faktoren,
        }

    async def _prognose(self, wetter: dict[str, Any], jetzt: datetime) -> dict[str, Any]:
        """ET₀ und Regen (Menge × Wahrscheinlichkeit) der nächsten 24 h."""
        if not wetter.get("prognose"):
            return {}
        try:
            antwort = await self.hass.services.async_call(
                "weather", "get_forecasts", {"type": "hourly"},
                target={"entity_id": wetter["prognose"]}, blocking=True, return_response=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Wetterprognose nicht verfügbar: %s", err)
            return {}
        eintraege = (antwort or {}).get(wetter["prognose"], {}).get("forecast") or []
        ende = jetzt + timedelta(hours=24)
        temp, feuchte, wind, wolken, stunden = [], [], [], [], []
        regen = 0.0
        for e in eintraege:
            t = dt_util.parse_datetime(str(e.get("datetime")))
            if t is None:
                continue
            if len(stunden) < 48 and t + timedelta(hours=1) > jetzt:
                stunden.append([dt_util.as_local(t).isoformat(), _zahl(e.get("precipitation")) or 0.0,
                                int(_zahl(e.get("precipitation_probability")) or 0)])
            if not (t + timedelta(hours=1) > jetzt and t < ende):
                continue
            menge = _zahl(e.get("precipitation")) or 0.0
            wahrsch = _zahl(e.get("precipitation_probability"))
            regen += menge * ((wahrsch if wahrsch is not None else 100) / 100)
            for liste, schluessel in ((temp, "temperature"), (feuchte, "humidity"),
                                      (wind, "wind_speed"), (wolken, "cloud_coverage")):
                w = _zahl(e.get(schluessel))
                if w is not None:
                    liste.append(w)
        erg: dict[str, Any] = {"regen": regen, "stunden": stunden}
        if len(temp) >= 6:
            breite, hoehe = self._standort(wetter)
            tag_im_jahr = jetzt.timetuple().tm_yday
            ra = et0.extraterrestrische_strahlung(tag_im_jahr, breite)
            rs = et0.strahlung_aus_bewoelkung(ra, hoehe, sum(wolken) / len(wolken) if wolken else 50)
            einheit_wind = (self.hass.states.get(wetter["prognose"]).attributes.get("wind_speed_unit")
                            if self.hass.states.get(wetter["prognose"]) else "km/h")
            erg["et0"] = et0.et0_tag(
                min(temp), max(temp), sum(feuchte) / len(feuchte) if feuchte else 70.0,
                _wind_ms(sum(wind) / len(wind) if wind else 0.0, einheit_wind),
                rs, tag_im_jahr, breite, hoehe, wind_messhoehe_m=10.0,
            )
        return erg

    def tageswechsel(self, einstellungen: dict[str, Any]) -> None:
        """Um Mitternacht: Regenzähler-Stand merken (Regen heute ab 0)."""
        regen = einstellungen["wetter"].get("regen")
        state = self.hass.states.get(regen) if regen else None
        self.daten["regen_mitternacht"] = _zahl(state.state) if state else None
        self.speichern()
