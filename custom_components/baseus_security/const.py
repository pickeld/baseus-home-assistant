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

# Defaults
DEFAULT_REGION = "AUTO"
DEFAULT_COUNTRY_CODE = "1"
DEFAULT_RTSP_BASE = "rtsp://homeassistant.local:8554"
DEFAULT_INCLUDE_OFFLINE = True

REGIONS = ["AUTO", "US", "EU", "AU"]

# How often to refresh the camera list / status from the cloud.
UPDATE_INTERVAL_SECONDS = 300

MANUFACTURER = "Baseus"
