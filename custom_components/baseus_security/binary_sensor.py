"""Binary sensor platform: connectivity and charging per camera."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BaseusCoordinator
from .entity import BaseusEntity


def _flatten(obj, out: dict) -> dict:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                _flatten(v, out)
            else:
                out[str(k).lower()] = v
    elif isinstance(obj, list):
        for v in obj:
            _flatten(v, out)
    return out


def _charging(cam) -> bool | None:
    flat = _flatten(getattr(cam, "extra", {}) or {}, {})
    for key in ("charging", "is_charging", "charge_status", "charge_state", "charge"):
        if key in flat and flat[key] not in (None, ""):
            val = flat[key]
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "charging", "on")
            return bool(val)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BaseusCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[tuple[str, str]] = set()

    @callback
    def _sync() -> None:
        new = []
        for slug, cam in (coordinator.data or {}).items():
            if (slug, "connectivity") not in known:
                known.add((slug, "connectivity"))
                new.append(BaseusConnectivity(coordinator, slug))
            if (slug, "charging") not in known and _charging(cam) is not None:
                known.add((slug, "charging"))
                new.append(BaseusCharging(coordinator, slug))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusConnectivity(BaseusEntity, BinarySensorEntity):
    """Reports whether the camera is currently online."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BaseusCoordinator, slug: str) -> None:
        super().__init__(coordinator, slug)
        self._attr_unique_id = f"{slug}_connectivity"

    @property
    def is_on(self) -> bool | None:
        cam = self._camera
        if cam is None:
            return None
        return bool(getattr(cam, "online", False))


class BaseusCharging(BaseusEntity, BinarySensorEntity):
    """Reports whether the camera battery is charging."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = "charging"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BaseusCoordinator, slug: str) -> None:
        super().__init__(coordinator, slug)
        self._attr_unique_id = f"{slug}_charging"

    @property
    def is_on(self) -> bool | None:
        cam = self._camera
        if cam is None:
            return None
        return _charging(cam)
