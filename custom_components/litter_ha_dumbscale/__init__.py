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
    CONF_ANOMALY_THRESHOLD,
    CONF_CAT_NAME,
    CONF_CAT_WEIGHT,
    CONF_CATS,
    CONF_LITTER_ROBOT_ENTITY,
    CONF_MAX_WEIGHT,
    CONF_MIN_WEIGHT,
    CONF_WEIGHT_ENTITIES,
    DEFAULT_ANOMALY_THRESHOLD,
    DEFAULT_EMA_ALPHA,
    DOMAIN,
    PLATFORMS,
    SIGNAL_ANOMALY_UPDATE,
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

        anomaly_threshold = config.get(
            CONF_ANOMALY_THRESHOLD, DEFAULT_ANOMALY_THRESHOLD
        )

        closest_cat = None
        closest_diff = float("inf")
        closest_ema = None
        second_closest_cat = None
        second_closest_diff = float("inf")

        cats_data = hass.data[DOMAIN][entry.entry_id]["cats"]

        for cat_name, cat_info in cats_data.items():
            ema_entity_id = (
                f"sensor.litter_ha_dumbscale_{cat_info['slug']}_ema_weight"
            )
            state = hass.states.get(ema_entity_id)

            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                current_ema = cat_info["initial_weight"]
            else:
                try:
                    current_ema = float(state.state)
                except (ValueError, TypeError):
                    current_ema = cat_info["initial_weight"]

            diff = abs(new_weight - current_ema)

            if diff < closest_diff:
                second_closest_cat = closest_cat
                second_closest_diff = closest_diff
                closest_diff = diff
                closest_cat = cat_name
                closest_ema = current_ema
            elif diff < second_closest_diff:
                second_closest_cat = cat_name
                second_closest_diff = diff

        if closest_cat is None:
            _LOGGER.warning("No cats configured, cannot attribute weight reading")
            return

        if closest_diff > anomaly_threshold:
            _LOGGER.warning(
                "Anomaly detected: weight %.2f lb differs from closest cat %s "
                "by %.2f lb (threshold: %.2f lb)",
                new_weight,
                closest_cat,
                closest_diff,
                anomaly_threshold,
            )

            hass.components.persistent_notification.async_create(
                f"Weight reading {new_weight:.2f} lb rejected as anomaly. "
                f"Closest cat: {closest_cat} (diff: {closest_diff:.2f} lb, "
                f"threshold: {anomaly_threshold:.2f} lb).",
                title="Cat Weight Tracker Anomaly",
                notification_id=f"{DOMAIN}_anomaly",
            )

            hass.bus.async_fire(
                f"{DOMAIN}_anomaly",
                {
                    "weight": new_weight,
                    "closest_cat": closest_cat,
                    "diff": round(closest_diff, 2),
                    "threshold": anomaly_threshold,
                    "timestamp": dt_util.utcnow().isoformat(),
                },
            )

            async_dispatcher_send(
                hass,
                f"{SIGNAL_ANOMALY_UPDATE}_{entry.entry_id}",
                {
                    "anomaly": True,
                    "weight": new_weight,
                    "closest_cat": closest_cat,
                    "diff": round(closest_diff, 2),
                },
            )
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

        new_ema = round(
            DEFAULT_EMA_ALPHA * new_weight + (1 - DEFAULT_EMA_ALPHA) * closest_ema, 2
        )

        _LOGGER.info(
            "Attributed weight %.2f lb to %s (diff: %.2f lb, EMA: %.2f -> %.2f)",
            new_weight,
            closest_cat,
            closest_diff,
            closest_ema,
            new_ema,
        )

        async_dispatcher_send(
            hass,
            f"{SIGNAL_ANOMALY_UPDATE}_{entry.entry_id}",
            {"anomaly": False},
        )

        async_dispatcher_send(
            hass,
            f"{SIGNAL_CAT_UPDATE}_{entry.entry_id}",
            {
                "cat": closest_cat,
                "weight": new_weight,
                "ema_weight": new_ema,
                "timestamp": dt_util.utcnow().isoformat(),
            },
        )

    weight_entities = entry.data.get(
        CONF_WEIGHT_ENTITIES, [entry.data[CONF_LITTER_ROBOT_ENTITY]]
    ) if CONF_LITTER_ROBOT_ENTITY in entry.data else entry.data[CONF_WEIGHT_ENTITIES]

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            weight_entities,
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
