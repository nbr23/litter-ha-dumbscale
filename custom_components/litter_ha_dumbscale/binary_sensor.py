from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import get_device_info
from .const import DOMAIN, SIGNAL_ANOMALY_UPDATE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AnomalyBinarySensor(entry)])


class AnomalyBinarySensor(RestoreEntity, BinarySensorEntity):

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert"
    _attr_is_on = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._anomaly_weight = None
        self._anomaly_closest_cat = None
        self._anomaly_diff = None

        self._attr_unique_id = f"{entry.entry_id}_anomaly"
        self._attr_name = "Anomaly detected"
        self.entity_id = "binary_sensor.litter_ha_dumbscale_anomaly"

    @property
    def device_info(self):
        return get_device_info(self._entry)

    @property
    def extra_state_attributes(self):
        if not self._attr_is_on:
            return None
        return {
            "weight": self._anomaly_weight,
            "closest_cat": self._anomaly_closest_cat,
            "diff": self._anomaly_diff,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == "on"
            if self._attr_is_on:
                attrs = last_state.attributes
                self._anomaly_weight = attrs.get("weight")
                self._anomaly_closest_cat = attrs.get("closest_cat")
                self._anomaly_diff = attrs.get("diff")

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_ANOMALY_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, data: dict) -> None:
        if data["anomaly"]:
            self._attr_is_on = True
            self._anomaly_weight = data.get("weight")
            self._anomaly_closest_cat = data.get("closest_cat")
            self._anomaly_diff = data.get("diff")
        else:
            self._attr_is_on = False
            self._anomaly_weight = None
            self._anomaly_closest_cat = None
            self._anomaly_diff = None
        self.async_write_ha_state()
