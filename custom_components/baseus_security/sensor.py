"""Sensor platform: battery level and Wi-Fi signal per camera (best effort).

The cloud device list carries per-camera telemetry under a nested ``extra``
mapping whose exact keys vary by model/firmware, so values are looked up
defensively and the entity simply reports ``None`` when unavailable.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BaseusCoordinator
from .entity import BaseusEntity


def _flatten(obj, out: dict) -> dict:
    """Collect all scalar leaf values keyed by lowercased field name."""
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


def _first(cam, keys: tuple[str, ...]):
    flat = _flatten(getattr(cam, "extra", {}) or {}, {})
    for key in keys:
        if key in flat and flat[key] not in (None, ""):
            return flat[key]
    return None


def _battery(cam):
    val = _first(cam, ("electricity", "battery", "battery_percent", "power", "elec"))
    try:
        num = int(val)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, num))


def _signal(cam):
    val = _first(cam, ("wifi_signal", "signal", "rssi", "wifi_rssi"))
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class BaseusSensorDescription(SensorEntityDescription):
    value_fn: Callable = lambda cam: None


SENSORS: tuple[BaseusSensorDescription, ...] = (
    BaseusSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_battery,
    ),
    BaseusSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_signal,
    ),
)


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
        for slug in coordinator.data or {}:
            for desc in SENSORS:
                key = (slug, desc.key)
                if key in known:
                    continue
                known.add(key)
                new.append(BaseusSensor(coordinator, slug, desc))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusSensor(BaseusEntity, SensorEntity):
    entity_description: BaseusSensorDescription

    def __init__(
        self,
        coordinator: BaseusCoordinator,
        slug: str,
        description: BaseusSensorDescription,
    ) -> None:
        super().__init__(coordinator, slug)
        self.entity_description = description
        self._attr_unique_id = f"{slug}_{description.key}"

    @property
    def native_value(self):
        cam = self._camera
        if cam is None:
            return None
        return self.entity_description.value_fn(cam)
