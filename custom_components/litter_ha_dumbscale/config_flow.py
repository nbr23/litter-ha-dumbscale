"""Config flow for Cat Weight Tracker integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ADD_ANOTHER,
    CONF_CAT_NAME,
    CONF_CAT_WEIGHT,
    CONF_CATS,
    CONF_LITTER_ROBOT_ENTITY,
    CONF_MAX_WEIGHT,
    CONF_MIN_WEIGHT,
    DEFAULT_MAX_WEIGHT,
    DEFAULT_MIN_WEIGHT,
    DOMAIN,
)


class CatWeightTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cat Weight Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict = {}
        self.cats: list[dict] = []

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step - configure litter robot entity and thresholds."""
        errors = {}

        if user_input is not None:
            entity_id = user_input[CONF_LITTER_ROBOT_ENTITY]

            if self.hass.states.get(entity_id) is None:
                errors["base"] = "invalid_entity"
            else:
                self.data = {
                    CONF_LITTER_ROBOT_ENTITY: entity_id,
                    CONF_MIN_WEIGHT: user_input[CONF_MIN_WEIGHT],
                    CONF_MAX_WEIGHT: user_input[CONF_MAX_WEIGHT],
                }
                return await self.async_step_add_cat()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LITTER_ROBOT_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(
                        CONF_MIN_WEIGHT, default=DEFAULT_MIN_WEIGHT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=50,
                            step=0.1,
                            unit_of_measurement="lb",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_MAX_WEIGHT, default=DEFAULT_MAX_WEIGHT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=50,
                            step=0.1,
                            unit_of_measurement="lb",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_add_cat(self, user_input: dict | None = None):
        """Handle adding a cat."""
        errors = {}

        if user_input is not None:
            cat_name = user_input[CONF_CAT_NAME].strip()

            existing_names = [cat[CONF_CAT_NAME].lower() for cat in self.cats]
            if cat_name.lower() in existing_names:
                errors["base"] = "duplicate_cat"
            else:
                self.cats.append({
                    CONF_CAT_NAME: cat_name,
                    CONF_CAT_WEIGHT: user_input[CONF_CAT_WEIGHT],
                })

                if user_input.get(CONF_ADD_ANOTHER, False):
                    return await self.async_step_add_cat()

                self.data[CONF_CATS] = self.cats
                return self.async_create_entry(
                    title="Cat Weight Tracker",
                    data=self.data,
                )

        description = None
        if self.cats:
            cat_list = ", ".join(cat[CONF_CAT_NAME] for cat in self.cats)
            description = f"Cats added: {cat_list}"

        return self.async_show_form(
            step_id="add_cat",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CAT_NAME): str,
                    vol.Required(CONF_CAT_WEIGHT, default=10.0): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=30,
                            step=0.1,
                            unit_of_measurement="lb",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_ADD_ANOTHER, default=False): bool,
                }
            ),
            description_placeholders={"cats": description} if description else None,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options flow not implemented for v1."""
        return None
