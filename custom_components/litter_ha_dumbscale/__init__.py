"""Cat Weight Tracker integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_CAT_NAME,
    CONF_CAT_WEIGHT,
    CONF_CATS,
    CONF_LITTER_ROBOT_ENTITY,
    CONF_MAX_WEIGHT,
    CONF_MIN_WEIGHT,
    DOMAIN,
    PLATFORMS,
    SIGNAL_CAT_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


def get_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return device info for grouping entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Cat Weight Tracker",
        manufacturer="Custom",
        model="Cat Weight Tracker",
        sw_version="1.0.0",
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cat Weight Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    cats_config = {
        cat[CONF_CAT_NAME]: {
            "initial_weight": cat[CONF_CAT_WEIGHT],
            "slug": slugify(cat[CONF_CAT_NAME]),
        }
        for cat in entry.data[CONF_CATS]
    }

    hass.data[DOMAIN][entry.entry_id] = {
        "cats": cats_config,
        "config": entry.data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_weight_change(event: Event) -> None:
        """Handle litter robot weight sensor state change."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        try:
            new_weight = float(new_state.state)
        except (ValueError, TypeError):
            _LOGGER.debug("Invalid weight value: %s", new_state.state)
            return

        config = entry.data
        min_weight = config[CONF_MIN_WEIGHT]
        max_weight = config[CONF_MAX_WEIGHT]
        if not (min_weight <= new_weight <= max_weight):
            _LOGGER.debug(
                "Weight %s outside range [%s, %s], ignoring",
                new_weight,
                min_weight,
                max_weight,
            )
            return

        closest_cat = None
        closest_diff = float("inf")
        second_closest_cat = None
        second_closest_diff = float("inf")

        cats_data = hass.data[DOMAIN][entry.entry_id]["cats"]

        for cat_name, cat_info in cats_data.items():
            weight_entity_id = f"number.litter_ha_dumbscale_{cat_info['slug']}_weight"
            state = hass.states.get(weight_entity_id)

            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                current_weight = cat_info["initial_weight"]
            else:
                try:
                    current_weight = float(state.state)
                except (ValueError, TypeError):
                    current_weight = cat_info["initial_weight"]

            diff = abs(new_weight - current_weight)

            if diff < closest_diff:
                second_closest_cat = closest_cat
                second_closest_diff = closest_diff
                closest_diff = diff
                closest_cat = cat_name
            elif diff < second_closest_diff:
                second_closest_cat = cat_name
                second_closest_diff = diff

        if closest_cat is None:
            _LOGGER.warning("No cats configured, cannot attribute weight reading")
            return

        if (
            closest_diff < 0.5
            and second_closest_cat is not None
            and abs(closest_diff - second_closest_diff) < 0.2
        ):
            _LOGGER.warning(
                "Ambiguous weight match: %s (diff: %.2f lb) and %s (diff: %.2f lb) "
                "are within 0.2 lb of each other for weight %.2f lb",
                closest_cat,
                closest_diff,
                second_closest_cat,
                second_closest_diff,
                new_weight,
            )

        _LOGGER.info(
            "Attributed weight %.2f lb to %s (diff: %.2f lb)",
            new_weight,
            closest_cat,
            closest_diff,
        )

        async_dispatcher_send(
            hass,
            f"{SIGNAL_CAT_UPDATE}_{entry.entry_id}",
            {
                "cat": closest_cat,
                "weight": new_weight,
                "timestamp": dt_util.utcnow().isoformat(),
            },
        )

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            [entry.data[CONF_LITTER_ROBOT_ENTITY]],
            handle_weight_change,
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
