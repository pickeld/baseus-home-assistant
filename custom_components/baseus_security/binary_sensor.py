"""Binary sensor platform: online/connectivity per camera."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BaseusCoordinator
from .entity import BaseusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BaseusCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _sync() -> None:
        new = []
        for slug in coordinator.data or {}:
            if slug in known:
                continue
            known.add(slug)
            new.append(BaseusConnectivity(coordinator, slug))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusConnectivity(BaseusEntity, BinarySensorEntity):
    """Reports whether the camera is currently online."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: BaseusCoordinator, slug: str) -> None:
        super().__init__(coordinator, slug)
        self._attr_unique_id = f"{slug}_connectivity"

    @property
    def is_on(self) -> bool | None:
        cam = self._camera
        if cam is None:
            return None
        return bool(getattr(cam, "online", False))
