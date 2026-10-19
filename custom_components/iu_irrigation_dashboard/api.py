"""WebSocket-API für das Panel.

iu_irrigation_dashboard/daten        Einstellungen + Status lesen (alle Benutzer)
iu_irrigation_dashboard/abonnieren   Änderungen von Einstellungen/Status abonnieren
iu_irrigation_dashboard/speichern    komplette Einstellungen speichern (nur Admin)
iu_irrigation_dashboard/aendern      Bedienwerte ändern (siehe steuerung.ERLAUBT)
iu_irrigation_dashboard/anwenden     IU-Konfiguration neu erzeugen/laden (nur Admin)
iu_irrigation_dashboard/manuell      manueller Ablauf: Zonen oder Sequenz eines Controllers
iu_irrigation_dashboard/stopp        manuellen Ablauf und laufende Beregnung beenden
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_EINSTELLUNGEN
from .einstellungen import neue_id


def _beregnung(hass: HomeAssistant):
    return hass.data.get(DOMAIN)


def _antwort(hass: HomeAssistant) -> dict[str, Any]:
    b = _beregnung(hass)
    return {"einstellungen": b.daten, "status": b.status, "zustand": b.zustand}


@callback
def async_register_api(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_daten)
    websocket_api.async_register_command(hass, ws_abonnieren)
    websocket_api.async_register_command(hass, ws_speichern)
    websocket_api.async_register_command(hass, ws_aendern)
    websocket_api.async_register_command(hass, ws_anwenden)
    websocket_api.async_register_command(hass, ws_neue_id)
    websocket_api.async_register_command(hass, ws_manuell)
    websocket_api.async_register_command(hass, ws_stopp)


def _bereit(hass: HomeAssistant, connection, msg) -> bool:
    if _beregnung(hass) is None:
        connection.send_error(msg["id"], "nicht_bereit", f"{DOMAIN} is not set up")
        return False
    return True


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/daten"})
@callback
def ws_daten(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if _bereit(hass, connection, msg):
        connection.send_result(msg["id"], _antwort(hass))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/abonnieren"})
@callback
def ws_abonnieren(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return

    @callback
    def _senden() -> None:
        if _beregnung(hass) is not None:
            connection.send_message(websocket_api.event_message(msg["id"], _antwort(hass)))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_EINSTELLUNGEN, _senden)
    connection.send_result(msg["id"])
    _senden()


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/speichern", vol.Required("einstellungen"): dict}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_speichern(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return
    try:
        await _beregnung(hass).async_speichern(msg["einstellungen"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "ungueltig", str(err))
        return
    connection.send_result(msg["id"], _antwort(hass))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/aendern", vol.Required("aenderungen"): [dict]}
)
@websocket_api.async_response
async def ws_aendern(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return
    try:
        await _beregnung(hass).async_aendern(msg["aenderungen"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "ungueltig", str(err))
        return
    connection.send_result(msg["id"], _antwort(hass))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/anwenden"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_anwenden(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return
    await _beregnung(hass).async_anwenden()
    connection.send_result(msg["id"], _antwort(hass))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/neue_id", vol.Optional("praefix"): vol.In(["c", "z", "s"])})
@callback
def ws_neue_id(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    connection.send_result(msg["id"], {"id": neue_id(msg.get("praefix", "z"))})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/manuell",
        vol.Required("controller"): str,
        vol.Optional("zonen"): [str],
        vol.Optional("sequenz"): str,
        vol.Optional("prozent", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
    }
)
@websocket_api.async_response
async def ws_manuell(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return
    try:
        await _beregnung(hass).async_manuell(msg["controller"], msg.get("zonen"), msg["prozent"], msg.get("sequenz"))
    except vol.Invalid as err:
        connection.send_error(msg["id"], "ungueltig", str(err))
        return
    connection.send_result(msg["id"], _antwort(hass))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/stopp", vol.Optional("controller"): str})
@websocket_api.async_response
async def ws_stopp(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    if not _bereit(hass, connection, msg):
        return
    await _beregnung(hass).async_stopp(msg.get("controller"))
    connection.send_result(msg["id"], _antwort(hass))
