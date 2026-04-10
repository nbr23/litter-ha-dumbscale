"""Sensor platform for Cat Weight Tracker."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from . import get_device_info
from .const import CONF_CAT_NAME, CONF_CAT_WEIGHT, CONF_CATS, DOMAIN, SIGNAL_CAT_UPDATE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cat Weight Tracker sensor entities."""
    entities: list[SensorEntity] = []

    for cat in entry.data[CONF_CATS]:
        cat_name = cat[CONF_CAT_NAME]
        entities.append(CatVisitCountSensor(entry, cat_name))
        entities.append(CatLastVisitSensor(entry, cat_name))
        entities.append(CatEmaWeightSensor(entry, cat_name, cat[CONF_CAT_WEIGHT]))

    entities.append(LastCatSensor(entry))

    async_add_entities(entities)


class CatVisitCountSensor(RestoreEntity, SensorEntity):
    """Sensor for cat visit count."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"
    _attr_native_value = 0

    def __init__(self, entry: ConfigEntry, cat_name: str) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._cat_name = cat_name
        cat_slug = slugify(cat_name)

        self._attr_unique_id = f"{entry.entry_id}_{cat_slug}_visit_count"
        self._attr_name = f"{cat_name} visit count"
        self.entity_id = f"sensor.litter_ha_dumbscale_{cat_slug}_visit_count"

    @property
    def device_info(self):
        """Return device info."""
        return get_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        """Restore state and set up dispatcher."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = int(last_state.state)
            except (ValueError, TypeError):
                self._attr_native_value = 0

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_CAT_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, data: dict) -> None:
        """Handle update from dispatcher."""
        if data["cat"] == self._cat_name:
            self._attr_native_value = (self._attr_native_value or 0) + 1
            self.async_write_ha_state()


class CatLastVisitSensor(RestoreEntity, SensorEntity):
    """Sensor for cat last visit timestamp."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"
    _attr_native_value = None

    def __init__(self, entry: ConfigEntry, cat_name: str) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._cat_name = cat_name
        cat_slug = slugify(cat_name)

        self._attr_unique_id = f"{entry.entry_id}_{cat_slug}_last_visit"
        self._attr_name = f"{cat_name} last visit"
        self.entity_id = f"sensor.litter_ha_dumbscale_{cat_slug}_last_visit"

    @property
    def device_info(self):
        """Return device info."""
        return get_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        """Restore state and set up dispatcher."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                try:
                    self._attr_native_value = datetime.fromisoformat(last_state.state)
                except (ValueError, TypeError):
                    self._attr_native_value = None

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_CAT_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, data: dict) -> None:
        """Handle update from dispatcher."""
        if data["cat"] == self._cat_name:
            self._attr_native_value = datetime.fromisoformat(data["timestamp"])
            self.async_write_ha_state()


class LastCatSensor(RestoreEntity, SensorEntity):
    """Sensor for last cat that used the litter box."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:cat"
    _attr_native_value = None

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._last_cat = None
        self._last_weight = None

        self._attr_unique_id = f"{entry.entry_id}_last_cat"
        self._attr_name = "Last cat"
        self.entity_id = "sensor.litter_ha_dumbscale_last_cat"

    @property
    def device_info(self):
        """Return device info."""
        return get_device_info(self._entry)

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if self._last_cat is None:
            return None
        return {
            "cat_name": self._last_cat,
            "weight": self._last_weight,
        }

    async def async_added_to_hass(self) -> None:
        """Restore state and set up dispatcher."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                self._attr_native_value = last_state.state
                attrs = last_state.attributes
                self._last_cat = attrs.get("cat_name")
                self._last_weight = attrs.get("weight")

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_CAT_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, data: dict) -> None:
        """Handle update from dispatcher."""
        self._last_cat = data["cat"]
        self._last_weight = data["weight"]
        self._attr_native_value = f"{data['cat']} ({data['weight']:.1f} lb)"
        self.async_write_ha_state()


class CatEmaWeightSensor(RestoreEntity, SensorEntity):

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "lb"
    _attr_icon = "mdi:scale-balance"
    _attr_native_value = None

    def __init__(
        self,
        entry: ConfigEntry,
        cat_name: str,
        initial_weight: float,
    ) -> None:
        self._entry = entry
        self._cat_name = cat_name
        self._initial_weight = initial_weight
        cat_slug = slugify(cat_name)

        self._attr_unique_id = f"{entry.entry_id}_{cat_slug}_ema_weight"
        self._attr_name = f"{cat_name} EMA weight"
        self.entity_id = f"sensor.litter_ha_dumbscale_{cat_slug}_ema_weight"

    @property
    def device_info(self):
        return get_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                self._attr_native_value = self._initial_weight
        else:
            self._attr_native_value = self._initial_weight

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_CAT_UPDATE}_{self._entry.entry_id}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self, data: dict) -> None:
        if data["cat"] == self._cat_name:
            self._attr_native_value = data["ema_weight"]
            self.async_write_ha_state()
