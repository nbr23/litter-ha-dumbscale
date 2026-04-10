"""Constants for Cat Weight Tracker integration."""

DOMAIN = "litter_ha_dumbscale"

CONF_LITTER_ROBOT_ENTITY = "litter_robot_entity"
CONF_MIN_WEIGHT = "min_weight"
CONF_MAX_WEIGHT = "max_weight"
CONF_CATS = "cats"
CONF_CAT_NAME = "name"
CONF_CAT_WEIGHT = "weight"
CONF_ADD_ANOTHER = "add_another"
CONF_ANOMALY_THRESHOLD = "anomaly_threshold"

DEFAULT_MIN_WEIGHT = 4.0
DEFAULT_MAX_WEIGHT = 25.0
DEFAULT_ANOMALY_THRESHOLD = 1.0
DEFAULT_EMA_ALPHA = 0.3

SIGNAL_CAT_UPDATE = f"{DOMAIN}_cat_update"
SIGNAL_ANOMALY_UPDATE = f"{DOMAIN}_anomaly_update"

PLATFORMS = ["binary_sensor", "number", "sensor"]
