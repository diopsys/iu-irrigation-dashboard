"""IU Irrigation Dashboard – Panel, Einstellungen und Steuerung für
Irrigation Unlimited.

Hinzufügen unter Einstellungen → Geräte & Dienste → „IU Irrigation
Dashboard“. Die Integration registriert das Panel selbst (kein panel_custom
in YAML) und erzeugt die IU-Konfiguration in packages/iu_irrigation_dashboard.yaml.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .api import async_register_api
from .const import DOMAIN, PANEL_ELEMENT, PANEL_URL_PATH, STATIC_URL
from .steuerung import Beregnung

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Statische Dateien und WebSocket-API einmalig registrieren."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), cache_headers=False)]
    )
    async_register_api(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Reste eines fehlgeschlagenen Einrichtungsversuchs stoppen
    alt: Beregnung | None = hass.data.pop(DOMAIN, None)
    if alt:
        alt.async_stop()

    # Ein Panel unter derselben Adresse (z. B. früheres panel_custom aus YAML)
    # ersetzen. Lader-Modul; es lädt die eigentliche App immer frisch.
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    version = entry.version
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Beregnung" if (hass.config.language or "").startswith("de") else "Irrigation",
        sidebar_icon="mdi:sprinkler-variant",
        module_url=f"{STATIC_URL}/irrigation-panel.js?v={version}",
        embed_iframe=False,
        require_admin=False,
    )

    beregnung = Beregnung(hass)
    # Fingerabdruck der Panel-App: eine noch offene ältere Seite erkennt daran,
    # dass sie neu geladen werden muss (z. B. nach einem Update mit Neustart)
    beregnung.status["app"] = await hass.async_add_executor_job(_app_fingerabdruck)
    hass.data[DOMAIN] = beregnung
    entry.runtime_data = beregnung
    await beregnung.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _app_fingerabdruck() -> str:
    import hashlib  # pylint: disable=import-outside-toplevel

    return hashlib.sha1((Path(__file__).parent / "www" / "irrigation-app.js").read_bytes()).hexdigest()[:12]


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    beregnung: Beregnung | None = hass.data.pop(DOMAIN, None)
    if beregnung:
        beregnung.async_stop()
    return ok
