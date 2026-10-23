"""Einrichtung über die Oberfläche (ohne Eingaben – alles Weitere im Panel)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import konfig_yaml
from .const import DOMAIN, NAME


class BeregnungConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            # Eigener IU-Abschnitt in configuration.yaml: vorher darauf hinweisen
            gefunden = await self.hass.async_add_executor_job(
                konfig_yaml.finden, Path(self.hass.config.path("configuration.yaml")))
            if gefunden:
                von, bis = gefunden[1]
                return self.async_show_form(step_id="bestand",
                                            description_placeholders={"von": str(von + 1), "bis": str(bis)})
            return self.async_create_entry(title=NAME, data={})
        return self.async_show_form(step_id="user")

    async def async_step_bestand(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_create_entry(title=NAME, data={})
