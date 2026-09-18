"""Constants for the Baseus Security integration."""
from __future__ import annotations

DOMAIN = "baseus_security"

# Config entry keys
CONF_ACCOUNT = "account"
CONF_PASSWORD = "password"
CONF_REGION = "region"
CONF_COUNTRY_CODE = "country_code"
CONF_RTSP_BASE = "rtsp_base"
CONF_INCLUDE_OFFLINE = "include_offline"

# Writable-control options (see README: run `probe-controls` to discover these).
CONF_ENABLE_CONTROLS = "enable_controls"
CONF_SET_ACTION = "set_action"
CONF_SET_SHAPE = "set_shape"
# Optional separate pair for base/HomeStation-level params (falls back to child).
CONF_SET_ACTION_BASE = "set_action_base"
CONF_SET_SHAPE_BASE = "set_shape_base"

# Defaults
DEFAULT_REGION = "AUTO"
DEFAULT_COUNTRY_CODE = "1"
DEFAULT_RTSP_BASE = "rtsp://homeassistant.local:8554"
DEFAULT_INCLUDE_OFFLINE = True
DEFAULT_ENABLE_CONTROLS = False

REGIONS = ["AUTO", "US", "EU", "AU"]

# How often to refresh the camera list / status from the cloud.
UPDATE_INTERVAL_SECONDS = 300

MANUFACTURER = "Baseus"
