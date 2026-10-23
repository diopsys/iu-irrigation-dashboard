"""Reparatur „iu_konflikt“: eigenen Abschnitt irrigation_unlimited: in
configuration.yaml nach Rückfrage auskommentieren (mit Sicherung)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import konfig_yaml
from .const import DOMAIN, IU_DATEI


class KonfliktFlow(RepairsFlow):
    """Zeigt die betroffenen Zeilen und kommentiert sie nach Bestätigung aus."""

    def __init__(self) -> None:
        self._auszug: str | None = None

    def _pfad(self) -> Path:
        return Path(self.hass.config.path("configuration.yaml"))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        hass = self.hass
        if user_input is not None:
            ergebnis = await hass.async_add_executor_job(konfig_yaml.beheben, self._pfad(), self._auszug)
            if ergebnis is None:
                return self.async_abort(reason="geaendert")
            beregnung = hass.data.get(DOMAIN)
            if beregnung:
                # IU mit der erzeugten Datei neu laden (nicht während eines Laufs)
                hass.async_create_task(beregnung.async_anwenden())
            return self.async_create_entry(data={})

        gefunden = await hass.async_add_executor_job(konfig_yaml.finden, self._pfad())
        if not gefunden:
            return self.async_abort(reason="nicht_gefunden")
        text, (von, bis) = gefunden
        self._auszug = konfig_yaml.auszug(text, (von, bis))
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"von": str(von + 1), "bis": str(bis), "auszug": self._auszug, "datei": IU_DATEI},
        )


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None) -> RepairsFlow:
    return KonfliktFlow()
