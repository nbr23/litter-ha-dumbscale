"""Number platform for Cat Weight Tracker."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import get_device_info
from .const import CONF_CAT_NAME, CONF_CAT_WEIGHT, CONF_CATS, DOMAIN, SIGNAL_CAT_UPDATE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cat Weight Tracker number entities."""
    entities = []

    for cat in entry.data[CONF_CATS]:
        entities.append(
            CatWeightNumber(
                entry=entry,
                cat_name=cat[CONF_CAT_NAME],
                initial_weight=cat[CONF_CAT_WEIGHT],
            )
        )

    async_add_entities(entities)


class CatWeightNumber(RestoreEntity, NumberEntity):
    """Number entity for cat weight."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 30
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfMass.POUNDS
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:scale"

    def __init__(
        self,
        entry: ConfigEntry,
        cat_name: str,
        initial_weight: float,
    ) -> None:
        """Initialize the number entity."""
        self._entry = entry
        self._cat_name = cat_name
        self._initial_weight = initial_weight
        self._attr_native_value = initial_weight

        from homeassistant.util import slugify
        cat_slug = slugify(cat_name)

        self._attr_unique_id = f"{entry.entry_id}_{cat_slug}_weight"
        self._attr_name = f"{cat_name} weight"
        self.entity_id = f"number.litter_ha_dumbscale_{cat_slug}_weight"

    @property
    def device_info(self):
        """Return device info."""
        return get_device_info(self._entry)

    async def async_added_to_hass(self) -> None:
        """Restore state and set up dispatcher."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
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
        """Handle weight update from dispatcher."""
        if data["cat"] == self._cat_name:
            self._attr_native_value = data["weight"]
            self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
