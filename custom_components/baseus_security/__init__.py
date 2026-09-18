"""The Baseus Security integration.

Exposes Baseus Security cameras in Home Assistant. Live video is served by a
companion local gateway (baseus-cam-bridge) as standard RTSP; this integration
adds the camera entities plus battery/signal/connectivity for each device,
using your own Baseus account to enumerate the cameras.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BaseusCoordinator

PLATFORMS: list[Platform] = [
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Baseus Security from a config entry."""
    coordinator = BaseusCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change (e.g. controls enabled/set-action pinned)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
