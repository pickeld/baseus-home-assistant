"""Sensor platform for Baseus Security.

The cloud device list carries per-camera telemetry under a nested ``extra``
mapping whose exact keys vary by model/firmware. Rather than hard-code one
layout, every scalar leaf is flattened and each sensor tries a list of
candidate field names. A sensor entity is only created for a camera when a
value is actually present, so no empty/unknown entities are spawned.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS,
    UnitOfInformation,
    UnitOfTemperature,
)
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


def _leaf(cam, keys: tuple[str, ...]):
    """Return the first present candidate field value for a camera."""
    flat = _flatten(getattr(cam, "extra", {}) or {}, {})
    for key in keys:
        if key in flat and flat[key] not in (None, ""):
            return flat[key]
    return None


def _nested(cam, *path):
    """Read an exact nested path from ``cam.extra`` (avoids flatten collisions)."""
    node = getattr(cam, "extra", {}) or {}
    for part in path:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _nested_int(cam, *path, lo=None, hi=None):
    val = _nested(cam, *path)
    try:
        num = int(float(val))
    except (TypeError, ValueError):
        return None
    if lo is not None:
        num = max(lo, num)
    if hi is not None:
        num = min(hi, num)
    return num


def _as_int(cam, keys, lo=None, hi=None):
    val = _leaf(cam, keys)
    try:
        num = int(float(val))
    except (TypeError, ValueError):
        return None
    if lo is not None:
        num = max(lo, num)
    if hi is not None:
        num = min(hi, num)
    return num


def _as_str(cam, keys):
    val = _leaf(cam, keys)
    return None if val in (None, "") else str(val)


def _storage_mb(cam, keys):
    """Storage fields may be MB ints or strings like '32GB'/'1024'."""
    val = _leaf(cam, keys)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().lower()
    try:
        if s.endswith("gb"):
            return int(float(s[:-2]) * 1024)
        if s.endswith("mb"):
            return int(float(s[:-2]))
        return int(float(s))
    except ValueError:
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
        value_fn=lambda c: _as_int(
            c, ("electricity", "battery", "battery_percent", "power", "elec", "quantity"), 0, 100
        ),
    ),
    BaseusSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _as_int(c, ("wifi_signal", "signal", "rssi", "wifi_rssi")),
    ),
    BaseusSensorDescription(
        key="wifi_strength",
        translation_key="wifi_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _as_int(
            c, ("wifi_strength", "wifi_quality", "signal_level", "wifi_level"), 0, 100
        ),
    ),
    BaseusSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _as_int(c, ("temperature", "temp", "battery_temp")),
    ),
    BaseusSensorDescription(
        key="speaker_volume",
        translation_key="speaker_volume",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _as_int(c, ("speaker_vol", "speaker_volume", "volume"), 0, 100),
    ),
    BaseusSensorDescription(
        key="pir_sensitivity",
        translation_key="pir_sensitivity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        # Nested under PIR to avoid colliding with SmartMode.pir_sen.
        value_fn=lambda c: _nested_int(c, "child_info", "PIR", "pir_sen", lo=0, hi=100),
    ),
    BaseusSensorDescription(
        key="storage_total",
        translation_key="storage_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _nested_int(c, "base", "storage", "total")
        or _storage_mb(c, ("sd_total", "sdcard_total", "storage_total", "total_size", "tf_total")),
    ),
    BaseusSensorDescription(
        key="storage_free",
        translation_key="storage_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _nested_int(c, "base", "storage", "free")
        or _storage_mb(c, ("sd_free", "sdcard_free", "storage_free", "free_size", "tf_free")),
    ),
    BaseusSensorDescription(
        key="storage_used",
        translation_key="storage_used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _nested_int(c, "base", "storage", "used"),
    ),
    BaseusSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: _as_str(
            c, ("sw_version", "firmware", "fw_version", "version", "soft_version")
        ),
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
        for slug, cam in (coordinator.data or {}).items():
            for desc in SENSORS:
                marker = (slug, desc.key)
                if marker in known:
                    continue
                # Only create the sensor if the camera actually reports it.
                if desc.value_fn(cam) is None:
                    continue
                known.add(marker)
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
