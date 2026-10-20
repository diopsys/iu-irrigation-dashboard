"""Laufzeitkern der Beregnung (Einstellungen Version 2).

- Einstellungen (Store) und Laufdaten (Wasserbilanz) halten, Änderungen per
  Dispatcher melden
- packages/iu_irrigation_dashboard.yaml erzeugen und Irrigation Unlimited neu laden (nie
  während eines Laufs), danach durchsetzen: Zonensperren aufheben, zonenweise
  Anpassungen zurücksetzen
- Laufzeit je Sequenzzone aus Wasserbilanz × Plan-% × Grundfaktor × Zonenfaktor
  per adjust_time setzen; 0 % → Zone für diesen Lauf aus. Bremse gegen
  Rückkopplung: nicht während eines Laufs, höchstens alle 5 min je Sequenz,
  erst ab 5 %-Punkten Unterschied (Schutz vor Rückkopplung)
- je Controller mit Pumpe: Wasserhahn-Betrieb (Ventil folgt der Pumpe),
  Tagbetrieb (Pumpe Sonnenauf- bis -untergang), Pumpe 30 s nach Laufende aus
- je Controller am Wasseranschluss mit Zähler: Verbrauch je Zone (wasser.py)
- manueller Ablauf (Zonen nacheinander per manual_run, abbrechbar)
- Läufe erfassen: Minuten je Zone, Gutschrift in der Bilanz, letzter Lauf
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ANSCHLUSS_LEITUNG,
    ANWENDEN_VERZOEGERUNG,
    BETRIEB_BEREGNUNG,
    BETRIEB_WASSERHAHN,
    DOMAIN,
    EVENT_IU_NEU,
    IU_DATEI,
    IU_DOMAIN,
    MONATE,
    SIGNAL_EINSTELLUNGEN,
    STORAGE_KEY,
    STORAGE_VERSION,
    WASSERHAHN_AUS_VERZOEGERUNG,
)
from . import wasser
from .einstellungen import STANDARD, bestand_uebernehmen, laden, pruefen, pumpe_id
from .iu_yaml import (
    _hhmmss,
    als_text,
    datei_pfad,
    erzeugen,
    include_vorhanden,
    iu_controller,
    iu_sequenzen,
    pruefen_mit_iu_schema,
    schreiben,
    seq_zone_aktiv,
    seq_zone_dauer,
    vollstaendig,
    zone_nach_id,
    zuordnung,
)
from .wetter import Wasserbilanz

_LOGGER = logging.getLogger(__name__)

_IU_IN_CONFIG_RE = re.compile(r"^irrigation_unlimited\s*:", re.M)
BERECHNEN_INTERVALL = 1800       # s, Neuberechnung der Laufzeiten
MIN_ABSTAND_ANWENDEN = 300       # s je Sequenz
MIN_AENDERUNG_PROZENT = 5        # %-Punkte
PUMPE_AUS_NACH_LAUF = 30         # s
TAGBETRIEB_WIEDER_EIN = 5        # s

# Bedienwerte, die auch Nicht-Admins ändern dürfen (beregnung/aendern)
ERLAUBT = {
    "zone": {"standard_min", "betrieb"},
    "seqzone": {"aktiv", "dauer_min"},
    "plan": {"monate", "tage", "zeit", "laufzeit"},
    "pumpe": {"tagbetrieb"},
    "wetter": {"aktiv", "grundfaktor"},
}


def _an(hass: HomeAssistant, entity_id: str | None) -> bool:
    state = hass.states.get(entity_id) if entity_id else None
    return state is not None and state.state in ("on", "open", "opening")


class Beregnung:
    """Eine Instanz je Config-Entry (es gibt nur einen)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.daten: dict[str, Any] = pruefen(STANDARD)
        self.bilanz = Wasserbilanz(hass)
        self.status: dict[str, Any] = {"iu": "unbekannt", "meldung": "", "ausstehend": False,
                                       "datei": IU_DATEI, "zuletzt": None}
        self.zustand: dict[str, Any] = {}
        self._durchgesetzt = False
        self._angewendet: dict[str, dict[int, tuple[bool, int]]] = {}
        self._angewendet_zeit: dict[str, float] = {}
        self._manuell: dict[str, asyncio.Task] = {}
        self._manuell_info: dict[str, dict[str, Any]] = {}
        self._seq_start: dict[str, tuple[datetime, str | None]] = {}
        self._zonen_start: dict[str, datetime] = {}
        # je Wasserzähler: [[zone_id, start, ende | None], …] (wasser.verteilen)
        self._wasser_segmente: dict[str, list[list]] = {}
        self._timer: dict[str, Callable] = {}
        self._beobachter: list[Callable] = []
        self._dauerhaft: list[Callable] = []
        self._start_listener: Callable | None = None
        self._lock = asyncio.Lock()
        self._berechnen_lock = asyncio.Lock()

    # ── Start/Stopp ───────────────────────────────────────────────────
    async def async_start(self) -> None:
        gespeichert = await self._store.async_load()
        await self.bilanz.async_laden()
        if gespeichert:
            try:
                self.daten = laden(gespeichert, self.hass)
            except vol.Invalid as err:
                _LOGGER.error("Gespeicherte Einstellungen ungültig (%s) – Standard wird verwendet", err)
        if self.hass.state is CoreState.running:
            await self._erststart(gespeichert)
        else:

            async def _gestartet(_event: Event) -> None:
                self._start_listener = None
                await self._erststart(gespeichert)

            self._start_listener = self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _gestartet)

    async def _erststart(self, gespeichert: Any) -> None:
        if not gespeichert:
            self.daten = await bestand_uebernehmen(self.hass)
            _LOGGER.info("Einstellungen aus der vorhandenen Irrigation-Unlimited-Konfiguration übernommen")
        if not gespeichert or gespeichert.get("version", 1) != self.daten["version"]:
            await self._store.async_save(self.daten)
        self._beobachten()
        hass = self.hass
        self._dauerhaft += [
            async_track_time_interval(hass, self._zeit_berechnen, _sekunden(BERECHNEN_INTERVALL)),
            async_track_time_change(hass, self._zeit_mitternacht, hour=0, minute=0, second=5),
            async_track_time_change(hass, self._zeit_nachholen, hour=0, minute=10, second=0),
            async_track_state_change_event(hass, ["sun.sun"], self._sonne),
        ]
        # IU stellt beim Start seinen alten Zustand her → danach durchsetzen
        self._anwenden_planen(30)

    @callback
    def async_stop(self) -> None:
        for abbrechen in [*self._timer.values(), self._start_listener, *self._beobachter, *self._dauerhaft]:
            if abbrechen:
                abbrechen()
        self._timer.clear()
        self._beobachter.clear()
        self._dauerhaft.clear()
        for task in self._manuell.values():
            task.cancel()

    def _melden(self) -> None:
        self.zustand["zuordnung"] = zuordnung(self.daten)
        self.zustand["wetter"] = self.bilanz.aktuell
        self.zustand["minuten"] = self.bilanz.daten["minuten"]
        self.zustand["wasser_l"] = self.bilanz.daten["wasser_l"]
        self.zustand["laeufe"] = self.bilanz.daten["laeufe"]
        self.zustand["anzahl"] = self.bilanz.daten["anzahl"]
        self.zustand["manuell"] = self._manuell_info
        async_dispatcher_send(self.hass, SIGNAL_EINSTELLUNGEN)

    def _planen(self, name: str, verzoegerung: float, aufgabe: Callable) -> None:
        if name in self._timer:
            self._timer.pop(name)()

        async def _los(_now: datetime) -> None:
            self._timer.pop(name, None)
            await aufgabe()

        self._timer[name] = async_call_later(self.hass, verzoegerung, _los)

    # ── Einstellungen ändern ──────────────────────────────────────────
    async def async_speichern(self, neu: dict[str, Any]) -> None:
        """Komplette Einstellungen speichern (Einstellungsseite)."""
        alt_betrieb = self._betriebe()
        self.daten = pruefen(neu)
        await self._nach_aenderung(alt_betrieb)

    async def async_aendern(self, aenderungen: list[dict[str, Any]]) -> None:
        """Bedienwerte ändern (Panel, auch Nicht-Admins), siehe ERLAUBT."""
        import copy  # pylint: disable=import-outside-toplevel

        neu = copy.deepcopy(self.daten)
        for aend in aenderungen:
            art, felder = aend.get("art"), aend.get("felder") or {}
            if art not in ERLAUBT:
                raise vol.Invalid(f"Unbekannte Änderung: {art}")
            if set(felder) - ERLAUBT[art]:
                raise vol.Invalid(f"Nicht änderbar: {', '.join(sorted(set(felder) - ERLAUBT[art]))}")
            ziel = self._ziel(neu, art, aend)
            if ziel is None:
                raise vol.Invalid(f"Unbekannt: {art} {aend.get('id')} {aend.get('zone') or aend.get('key') or ''}")
            ziel.update(felder)
        await self.async_speichern(neu)

    @staticmethod
    def _ziel(daten: dict[str, Any], art: str, aend: dict[str, Any]) -> dict[str, Any] | None:
        if art == "wetter":
            return daten["wetter"]
        for ctl in daten["controller"]:
            if art == "pumpe" and ctl["id"] == aend.get("id"):
                return ctl["pumpe"]
            if art == "zone":
                zone = zone_nach_id(ctl, aend.get("id"))
                if zone:
                    return zone
            for seq in ctl["sequenzen"]:
                if seq["id"] != aend.get("id"):
                    continue
                if art == "seqzone":
                    return next((sz for sz in seq["zonen"] if sz["zone"] == aend.get("zone")), None)
                if art == "plan":
                    return next((p for p in seq["plaene"] if p["key"] == aend.get("key")), None)
        return None

    def _betriebe(self) -> dict[str, str]:
        return {z["id"]: z["betrieb"] for c in self.daten["controller"] for z in c["zonen"]}

    async def _nach_aenderung(self, alt_betrieb: dict[str, str]) -> None:
        await self._store.async_save(self.daten)
        self._beobachten()
        for ctl in self.daten["controller"]:
            # Tagbetrieb sofort umsetzen (nicht erst beim nächsten Sonnenauf-/-untergang)
            self.hass.async_create_task(self._tagbetrieb(ctl))
            for zone in ctl["zonen"]:
                if zone["wasserhahn"] and alt_betrieb.get(zone["id"]) != zone["betrieb"]:
                    self.hass.async_create_task(self._hahn_abgleichen(ctl, wechsel=zone["id"]))
        self._melden()
        self._anwenden_planen(ANWENDEN_VERZOEGERUNG)

    # ── IU-Konfiguration schreiben und laden ─────────────────────────
    @callback
    def _anwenden_planen(self, verzoegerung: float) -> None:
        self._planen("anwenden", verzoegerung, self.async_anwenden)

    def _status(self, iu: str, meldung: str = "", ausstehend: bool = False) -> None:
        self.status.update(iu=iu, meldung=meldung, ausstehend=ausstehend, zuletzt=dt_util.now().isoformat())
        self._melden()

    def _laeuft(self) -> bool:
        zu = zuordnung(self.daten)
        return any(_an(self.hass, e) for e in zu["controller"].values()) or bool(self._manuell)

    async def async_anwenden(self) -> None:
        async with self._lock:
            await self._anwenden()

    async def _anwenden(self) -> None:
        hass = self.hass
        grund = vollstaendig(self.daten)
        if grund:
            self._status("unvollstaendig", grund)
            return
        konfig = erzeugen(self.daten)
        fehler = pruefen_mit_iu_schema(hass, konfig)
        if fehler:
            _LOGGER.error("Erzeugte IU-Konfiguration ungültig: %s", fehler)
            self._status("fehler", f"Konfiguration ungültig: {fehler}")
            return

        geaendert = await hass.async_add_executor_job(schreiben, datei_pfad(hass), als_text(konfig))
        include = await hass.async_add_executor_job(include_vorhanden, hass)
        konflikt = await hass.async_add_executor_job(self._iu_in_configuration_yaml)

        if konflikt:
            self._issue("iu_konflikt")
            self._status("konflikt", "In configuration.yaml steht noch eine eigene irrigation_unlimited-"
                         "Konfiguration. Bitte entfernen und HA neu starten.")
            return
        ir.async_delete_issue(hass, DOMAIN, "iu_konflikt")
        if not include:
            self._issue("iu_include")
            self._status("include", "configuration.yaml lädt den Ordner packages/ nicht. "
                         "Ergänzen: homeassistant: packages: !include_dir_named packages")
            return
        ir.async_delete_issue(hass, DOMAIN, "iu_include")
        if IU_DOMAIN not in hass.config.components or not hass.services.has_service(IU_DOMAIN, "reload"):
            self._issue("iu_neustart")
            self._status("neustart", "Irrigation Unlimited ist noch nicht geladen – einmal Home Assistant neu starten.")
            return
        ir.async_delete_issue(hass, DOMAIN, "iu_neustart")

        if geaendert or not self._durchgesetzt:
            if self._laeuft():
                self._status("ausstehend", "Wird nach dem laufenden Lauf übernommen.", ausstehend=True)
                self._planen("anwenden", 60, self.async_anwenden)
                return
            if geaendert:
                _LOGGER.info("Beregnung: IU-Konfiguration geändert – irrigation_unlimited.reload")
                await hass.services.async_call(IU_DOMAIN, "reload", {}, blocking=True)
                await asyncio.sleep(2)
                self._beobachten()
            await self._durchsetzen()
        self._status("ok", "")

    def _iu_in_configuration_yaml(self) -> bool:
        try:
            text = Path(self.hass.config.path("configuration.yaml")).read_text(encoding="utf-8")
        except OSError:
            return False
        return bool(_IU_IN_CONFIG_RE.search(text))

    def _issue(self, key: str) -> None:
        ir.async_create_issue(self.hass, DOMAIN, key, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                              translation_key=key, translation_placeholders={"datei": IU_DATEI})

    async def _iu(self, dienst: str, daten: dict[str, Any]) -> None:
        try:
            await self.hass.services.async_call(IU_DOMAIN, dienst, daten, blocking=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("IU %s %s fehlgeschlagen: %s", dienst, daten, err)

    async def _durchsetzen(self) -> None:
        """Nach Neuladen und HA-Start: Zonensperren aufheben, zonenweise
        Anpassungen zurücksetzen, Laufzeiten neu setzen."""
        hass = self.hass
        zu = zuordnung(self.daten)
        for entity in zu["zonen"].values():
            zone = hass.states.get(entity)
            if zone is not None and zone.attributes.get("enabled") is False:
                await self._iu("enable", {"entity_id": entity})
        for ctl in iu_controller(self.daten):
            for seq in iu_sequenzen(ctl):
                entity = zu["sequenzen"].get(seq["id"])
                if entity and hass.states.get(entity) is not None:
                    await self._iu("adjust_time", {"entity_id": entity, "reset": None,
                                                   "zones": list(range(1, len(seq["zonen"]) + 1))})
                    await self._iu("adjust_time", {"entity_id": entity, "reset": None})
                    # Aussetzen nutzt die Integration nicht (0 % = Zone aus);
                    # eine alte Aussetzung (frühere Regenautomation) aufheben
                    if hass.states.get(entity).attributes.get("suspended"):
                        await self._iu("suspend", {"entity_id": entity, "reset": None})
        self._angewendet.clear()
        self._angewendet_zeit.clear()
        self._durchgesetzt = True
        hass.bus.async_fire(EVENT_IU_NEU)
        for ctl in self.daten["controller"]:
            await self._tagbetrieb(ctl)
            await self._hahn_abgleichen(ctl)
        await self.async_berechnen(erzwingen=True)

    # ── Laufzeiten aus der Wasserbilanz ───────────────────────────────
    async def _zeit_berechnen(self, _now: datetime) -> None:
        await self.async_berechnen()

    async def _zeit_nachholen(self, _now: datetime) -> None:
        await self.async_berechnen()

    async def _zeit_mitternacht(self, _now: datetime) -> None:
        self.bilanz.tageswechsel(self.daten)

    def _plan(self, seq: dict[str, Any]) -> dict[str, Any] | None:
        """Plan des nächsten Laufs (IU next_name), sonst der des Monats."""
        entity = zuordnung(self.daten)["sequenzen"].get(seq["id"])
        state = self.hass.states.get(entity) if entity else None
        naechster = state.attributes.get("next_name") if state else None
        for plan in seq["plaene"]:
            if naechster and plan["name"] == naechster:
                return plan
        monat = MONATE[dt_util.now().month - 1]
        return next((p for p in seq["plaene"] if monat in p["monate"]), None)

    def soll_prozente(self) -> dict[str, dict[str, Any]]:
        """Je Sequenz: Plan und je Sequenzzone (aktiv, %)."""
        wetter = self.daten["wetter"]
        faktoren = (self.bilanz.aktuell or {}).get("zonen", {})
        erg: dict[str, dict[str, Any]] = {}
        for ctl in iu_controller(self.daten):
            for seq in iu_sequenzen(ctl):
                plan = self._plan(seq)
                plan_pct = plan["laufzeit"] if plan else 100
                zonen = {}
                for nr, sz in enumerate(seq["zonen"], start=1):
                    zone = zone_nach_id(ctl, sz["zone"])
                    f = 1.0
                    if wetter["aktiv"] and seq["wetter"] and zone and sz["zone"] in faktoren:
                        f = faktoren[sz["zone"]]["faktor"]
                    pct = f * plan_pct * wetter["grundfaktor"] * (zone["faktor"] if zone else 100) / 1e4
                    pct = int(round(pct / 5) * 5)
                    zonen[sz["zone"]] = {"nr": nr, "prozent": pct,
                                         "aktiv": seq_zone_aktiv(ctl, sz) and pct > 0,
                                         "minuten": round(seq_zone_dauer(ctl, sz) * pct / 100, 1)}
                erg[seq["id"]] = {"plan": plan["name"] if plan else None, "plan_prozent": plan_pct, "zonen": zonen}
        return erg

    async def async_berechnen(self, erzwingen: bool = False) -> None:
        if self._berechnen_lock.locked():
            return
        async with self._berechnen_lock:
            try:
                await self.bilanz.nachholen(self.daten)
                await self.bilanz.aktualisieren(self.daten)
            except Exception:  # noqa: BLE001 – Wetter darf die Steuerung nicht stoppen
                _LOGGER.exception("Wasserbilanz nicht berechenbar")
            soll = self.soll_prozente()
            self.zustand["sequenzen"] = soll
            if self.status.get("iu") == "ok" or self._durchgesetzt:
                await self._prozente_anwenden(soll, erzwingen)
            self._melden()

    async def _prozente_anwenden(self, soll: dict[str, dict[str, Any]], erzwingen: bool) -> None:
        zu = zuordnung(self.daten)
        jetzt = time.monotonic()
        for seq_id, s in soll.items():
            entity = zu["sequenzen"].get(seq_id)
            if not entity or self.hass.states.get(entity) is None or _an(self.hass, entity):
                continue
            neu = {z["nr"]: (z["aktiv"], z["prozent"]) for z in s["zonen"].values()}
            alt = self._angewendet.get(seq_id)
            if alt is not None and not erzwingen:
                if jetzt - self._angewendet_zeit.get(seq_id, 0) < MIN_ABSTAND_ANWENDEN:
                    continue
                if all(nr in alt and alt[nr][0] == a and abs(alt[nr][1] - p) < MIN_AENDERUNG_PROZENT
                       for nr, (a, p) in neu.items()):
                    continue
            an = [nr for nr, (a, _p) in neu.items() if a]
            aus = [nr for nr, (a, _p) in neu.items() if not a]
            if an:
                await self._iu("enable", {"entity_id": entity, "zones": an})
            if aus:
                await self._iu("disable", {"entity_id": entity, "zones": aus})
            gruppen: dict[int, list[int]] = {}
            for nr, (a, p) in neu.items():
                if a:
                    gruppen.setdefault(p, []).append(nr)
            for pct, zonen in gruppen.items():
                if pct == 100:
                    await self._iu("adjust_time", {"entity_id": entity, "zones": zonen, "reset": None})
                else:
                    await self._iu("adjust_time", {"entity_id": entity, "zones": zonen, "percentage": pct})
            self._angewendet[seq_id] = neu
            self._angewendet_zeit[seq_id] = jetzt

    # ── Beobachter: Pumpen, Zonen, Sequenzen ──────────────────────────
    @callback
    def _beobachten(self) -> None:
        for abmelden in self._beobachter:
            abmelden()
        self._beobachter.clear()
        zu = zuordnung(self.daten)
        pumpen = {pumpe_id(c): c for c in self.daten["controller"] if pumpe_id(c)}
        ctl_entity = {e: cid for cid, e in zu["controller"].items()}
        zonen_entity = {e: zid for zid, e in zu["zonen"].items()}
        seq_entity = {e: sid for sid, e in zu["sequenzen"].items()}
        zaehler = {wasser_zaehler(c) for c in self.daten["controller"]} - {None}
        self._wasser_segmente = {z: self._wasser_segmente.get(z, []) for z in zaehler}
        alle = [*pumpen, *ctl_entity, *zonen_entity, *seq_entity, *zaehler]
        if not alle:
            return

        @callback
        def _geaendert(event: Event) -> None:
            eid = event.data["entity_id"]
            alt, neu = event.data.get("old_state"), event.data.get("new_state")
            if neu is None:
                return
            if eid in pumpen:
                self.hass.async_create_task(self._pumpe_geaendert(pumpen[eid], neu.state))
            if eid in ctl_entity and alt is not None and alt.state == "on" and neu.state == "off":
                self._planen(f"pumpe_aus_{ctl_entity[eid]}", PUMPE_AUS_NACH_LAUF,
                             lambda cid=ctl_entity[eid]: self._pumpe_nach_lauf(cid))
            if eid in zonen_entity:
                self._zone_geaendert(zonen_entity[eid], alt, neu)
            if eid in seq_entity:
                self._sequenz_geaendert(seq_entity[eid], alt, neu)
            if eid in zaehler:
                self._zaehler_geaendert(eid, alt, neu)

        self._beobachter.append(async_track_state_change_event(self.hass, alle, _geaendert))

    def _ctl_der_zone(self, zone_id: str) -> tuple[dict[str, Any], dict[str, Any]] | tuple[None, None]:
        for ctl in self.daten["controller"]:
            zone = zone_nach_id(ctl, zone_id)
            if zone:
                return ctl, zone
        return None, None

    def _zone_geaendert(self, zone_id: str, alt: Any, neu: Any) -> None:
        ctl, zone = self._ctl_der_zone(zone_id)
        segmente = self._wasser_segmente.get(wasser_zaehler(ctl)) if ctl else None
        if neu.state == "on" and (alt is None or alt.state != "on"):
            self._zonen_start[zone_id] = dt_util.utcnow()
            if segmente is not None:
                segmente.append([zone_id, dt_util.utcnow(), None])
        elif alt is not None and alt.state == "on" and neu.state != "on":
            start = self._zonen_start.pop(zone_id, alt.last_changed)
            minuten = (dt_util.utcnow() - start).total_seconds() / 60
            for seg in segmente or []:
                if seg[0] == zone_id and seg[2] is None:
                    seg[2] = dt_util.utcnow()
            if zone and 0 < minuten < 24 * 60:
                self.bilanz.lauf_gutschreiben(zone, minuten, self.daten)
                self._melden()
            if ctl and zone and zone["wasserhahn"]:
                # IU hat das Ventil nach dem Lauf geschlossen → Hahn ggf. wieder auf
                self._planen(f"hahn_{ctl['id']}", 5, lambda c=ctl: self._hahn_abgleichen(c))

    def _zaehler_geaendert(self, zaehler: str, alt: Any, neu: Any) -> None:
        """Neuer Zählerstand → Menge seit der letzten Meldung auf die Zonen
        verteilen, die in diesem Zeitraum liefen."""
        segmente = self._wasser_segmente.get(zaehler)
        if alt is None or segmente is None:
            return
        vorher = wasser.liter(alt.state, alt.attributes.get("unit_of_measurement"))
        jetzt = wasser.liter(neu.state, neu.attributes.get("unit_of_measurement"))
        if vorher is None or jetzt is None:
            return
        von = getattr(alt, "last_reported", None) or alt.last_updated
        bis = neu.last_updated
        menge = jetzt - vorher
        if 0 < menge <= wasser.MAX_SPRUNG_L:
            verteilt = wasser.verteilen(segmente, von, bis, menge)
            for zone_id, liter in verteilt.items():
                summe = self.bilanz.daten["wasser_l"]
                summe[zone_id] = round(summe.get(zone_id, 0.0) + liter, 2)
            if verteilt:
                self.bilanz.speichern()
                self._melden()
        self._wasser_segmente[zaehler] = wasser.aufraeumen(segmente, bis)

    def _sequenz_geaendert(self, seq_id: str, alt: Any, neu: Any) -> None:
        if neu.state == "on" and (alt is None or alt.state != "on"):
            self._seq_start[seq_id] = (dt_util.utcnow(), neu.attributes.get("current_name"))
        elif alt is not None and alt.state == "on" and neu.state != "on":
            start, plan = self._seq_start.pop(seq_id, (alt.last_changed, alt.attributes.get("current_name")))
            ende = dt_util.utcnow()
            self.bilanz.daten["laeufe"][seq_id] = {
                "start": dt_util.as_local(start).isoformat(), "ende": dt_util.as_local(ende).isoformat(),
                "dauer_min": round((ende - start).total_seconds() / 60, 1), "plan": plan, "art": "automatik",
            }
            self.bilanz.daten["anzahl"]["automatik"] = self.bilanz.daten["anzahl"].get("automatik", 0) + 1
            self.bilanz.speichern()
            self._melden()
            # Laufzeiten für den nächsten Lauf neu setzen
            self._planen("berechnen", 10, lambda: self.async_berechnen(erzwingen=True))

    # ── Pumpe: Wasserhahn, Tagbetrieb, aus nach dem Lauf ─────────────
    def _ctl_nach_id(self, ctl_id: str) -> dict[str, Any] | None:
        return next((c for c in self.daten["controller"] if c["id"] == ctl_id), None)

    def _ist_tag(self) -> bool:
        return self.hass.states.get("sun.sun") is not None and self.hass.states.get("sun.sun").state == "above_horizon"

    async def _pumpe_geaendert(self, ctl: dict[str, Any], zustand: str) -> None:
        if zustand == "on":
            if f"hahn_aus_{ctl['id']}" in self._timer:
                self._timer.pop(f"hahn_aus_{ctl['id']}")()
            await self._hahn_abgleichen(ctl)
        elif zustand == "off":
            self._planen(f"hahn_aus_{ctl['id']}", WASSERHAHN_AUS_VERZOEGERUNG, lambda c=ctl: self._hahn_abgleichen(c))
            if ctl["pumpe"]["tagbetrieb"] and self._ist_tag():
                self._planen(f"tag_ein_{ctl['id']}", TAGBETRIEB_WIEDER_EIN, lambda c=ctl: self._tagbetrieb(c))

    async def _tagbetrieb(self, ctl: dict[str, Any]) -> None:
        """Pumpe tagsüber an (Tagbetrieb), abends aus – außer es läuft etwas."""
        ctl = self._ctl_nach_id(ctl["id"]) or ctl
        pumpe = pumpe_id(ctl)
        if not pumpe or not ctl["pumpe"]["tagbetrieb"]:
            return
        if self._ist_tag():
            if not _an(self.hass, pumpe):
                await self._schalten(pumpe, True)
        elif not self._ctl_laeuft(ctl["id"]) and _an(self.hass, pumpe):
            await self._schalten(pumpe, False)

    async def _sonne(self, _event: Event) -> None:
        for ctl in self.daten["controller"]:
            await self._tagbetrieb(ctl)

    def _ctl_laeuft(self, ctl_id: str) -> bool:
        entity = zuordnung(self.daten)["controller"].get(ctl_id)
        return _an(self.hass, entity) or ctl_id in self._manuell

    async def _pumpe_nach_lauf(self, ctl_id: str) -> None:
        """IU schaltet die Pumpe nur ein. Nach dem Lauf aus – außer Tagbetrieb."""
        ctl = self._ctl_nach_id(ctl_id)
        if not ctl or self._ctl_laeuft(ctl_id):
            return
        if ctl["pumpe"]["tagbetrieb"] and self._ist_tag():
            return
        if _an(self.hass, pumpe_id(ctl)):
            await self._schalten(pumpe_id(ctl), False)

    async def _hahn_abgleichen(self, ctl: dict[str, Any], wechsel: str | None = None) -> None:
        """Ventile im Wasserhahn-Betrieb auf den Pumpenzustand bringen; beim
        Wechsel auf Beregnung den Hahn schließen (außer die Zone läuft)."""
        ctl = self._ctl_nach_id(ctl["id"]) or ctl
        pumpe_an = _an(self.hass, pumpe_id(ctl))
        zu = zuordnung(self.daten)
        for zone in ctl["zonen"]:
            if not zone["wasserhahn"]:
                continue
            if zone["betrieb"] == BETRIEB_WASSERHAHN:
                soll = pumpe_an
            elif zone["betrieb"] == BETRIEB_BEREGNUNG and wechsel == zone["id"] and not _an(self.hass, zu["zonen"].get(zone["id"])):
                soll = False
            else:
                continue
            for ventil in zone["ventile"]:
                if _an(self.hass, ventil) != soll:
                    await self._schalten(ventil, soll)

    async def _schalten(self, entity_id: str, an: bool) -> None:
        domain = entity_id.split(".", 1)[0]
        if domain == "valve":
            dienst = ("valve", "open_valve" if an else "close_valve")
        elif domain == "cover":
            dienst = ("cover", "open_cover" if an else "close_cover")
        else:
            dienst = ("homeassistant", "turn_on" if an else "turn_off")
        try:
            await self.hass.services.async_call(*dienst, {"entity_id": entity_id}, blocking=False)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("%s nicht schaltbar: %s", entity_id, err)

    # ── Manueller Ablauf ──────────────────────────────────────────────
    async def async_manuell(self, ctl_id: str, zonen: list[str] | None, prozent: int, seq_id: str | None) -> None:
        """Zonen (oder die Zonen einer Sequenz) nacheinander laufen lassen:
        Standardlaufzeit bzw. Dauer der Sequenz × prozent."""
        ctl = self._ctl_nach_id(ctl_id)
        if ctl is None:
            raise vol.Invalid("Unbekannter Controller")
        if ctl_id in self._manuell:
            raise vol.Invalid(f"In „{ctl['name']}“ läuft bereits ein manueller Ablauf")
        if self._ctl_laeuft(ctl_id):
            raise vol.Invalid(f"„{ctl['name']}“ läuft gerade")
        if seq_id:
            seq = next((s for s in ctl["sequenzen"] if s["id"] == seq_id), None)
            if seq is None:
                raise vol.Invalid("Unbekannte Sequenz")
            eintraege = [(zone_nach_id(ctl, sz["zone"]), seq_zone_dauer(ctl, sz))
                         for sz in seq["zonen"] if sz["aktiv"]]
            pause = seq["pause_s"]
        else:
            eintraege = [(zone_nach_id(ctl, zid), zone_nach_id(ctl, zid)["standard_min"])
                         for zid in (zonen or []) if zone_nach_id(ctl, zid)]
            pause = 1
        eintraege = [(z, max(1, round(m * 60 * prozent / 100))) for z, m in eintraege if z]
        if not eintraege or prozent <= 0:
            raise vol.Invalid("Keine Zone mit Laufzeit gewählt")
        self._manuell[ctl_id] = self.hass.async_create_task(self._ablauf(ctl, eintraege, pause))

    async def async_stopp(self, ctl_id: str | None) -> None:
        zu = zuordnung(self.daten)
        for cid in [ctl_id] if ctl_id else [c["id"] for c in self.daten["controller"]]:
            task = self._manuell.get(cid)
            if task:
                task.cancel()
            entity = zu["controller"].get(cid)
            if entity:
                await self._iu("cancel", {"entity_id": entity})

    async def _warten(self, entity_id: str, soll: Callable[[str], bool], timeout: float) -> bool:
        if soll(self.hass.states.get(entity_id).state if self.hass.states.get(entity_id) else ""):
            return True
        fertig = asyncio.get_running_loop().create_future()

        @callback
        def _pruefen(event: Event) -> None:
            neu = event.data.get("new_state")
            if neu is not None and soll(neu.state) and not fertig.done():
                fertig.set_result(True)

        abmelden = async_track_state_change_event(self.hass, [entity_id], _pruefen)
        try:
            return await asyncio.wait_for(fertig, timeout)
        except asyncio.TimeoutError:
            return False
        finally:
            abmelden()

    async def _ablauf(self, ctl: dict[str, Any], eintraege: list[tuple[dict[str, Any], int]], pause: int) -> None:
        zu = zuordnung(self.daten)
        ctl_entity = zu["controller"].get(ctl["id"])
        state = self.hass.states.get(ctl_entity) if ctl_entity else None
        freigegeben = bool(state and state.attributes.get("enabled") is False)
        start = dt_util.now()
        if freigegeben:
            await self._iu("enable", {"entity_id": ctl_entity})
        try:
            for zone, sekunden in eintraege:
                entity = zu["zonen"].get(zone["id"])
                if not entity:
                    continue
                self._manuell_info[ctl["id"]] = {"zone": zone["id"], "start": dt_util.now().isoformat(),
                                                 "sekunden": sekunden, "start_ablauf": start.isoformat(),
                                                 "zonen": [z["id"] for z, _s in eintraege]}
                self._melden()
                await self._iu("manual_run", {"entity_id": entity, "time": _hhmmss(sekunden)})
                if not await self._warten(entity, lambda s: s == "on", 60 + ctl["pumpe"]["vorlauf_s"]):
                    _LOGGER.warning("Zone %s ist nicht gestartet – weiter mit der nächsten", zone["name"])
                    continue
                await self._warten(entity, lambda s: s != "on", sekunden + 300)
                if pause:
                    await asyncio.sleep(pause)
        finally:
            self._manuell.pop(ctl["id"], None)
            self._manuell_info.pop(ctl["id"], None)
            if freigegeben:
                await self._iu("disable", {"entity_id": ctl_entity})
            ende = dt_util.now()
            self.bilanz.daten["laeufe"][f"manuell_{ctl['id']}"] = {
                "start": start.isoformat(), "ende": ende.isoformat(),
                "dauer_min": round((ende - start).total_seconds() / 60, 1), "plan": None, "art": "manuell",
            }
            self.bilanz.daten["anzahl"]["manuell"] = self.bilanz.daten["anzahl"].get("manuell", 0) + 1
            self.bilanz.speichern()
            self._melden()
            self._planen(f"pumpe_aus_{ctl['id']}", PUMPE_AUS_NACH_LAUF, lambda c=ctl["id"]: self._pumpe_nach_lauf(c))


def wasser_zaehler(ctl: dict[str, Any] | None) -> str | None:
    """Wasserzähler eines Controllers am Wasseranschluss, sonst None."""
    if not ctl or ctl["anschluss"] != ANSCHLUSS_LEITUNG:
        return None
    return ctl["wasser"]["zaehler"]


def _sekunden(s: int):
    from datetime import timedelta  # pylint: disable=import-outside-toplevel

    return timedelta(seconds=s)
