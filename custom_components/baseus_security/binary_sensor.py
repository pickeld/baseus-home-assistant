"""Binary sensor platform: connectivity, charging, and camera feature states.

Feature-state sensors are read-only reflections of settings reported by the
cloud (motion detection, night vision, status light, etc.). Writable versions
(switches) require device write-commands and are added separately.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BaseusCoordinator
from .entity import BaseusEntity


def _nested(cam, *path):
    node = getattr(cam, "extra", {}) or {}
    for part in path:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _truthy(val) -> bool | None:
    if val in (None, ""):
        return None
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on", "charging", "enabled")
    return bool(val)


def _charging(cam) -> bool | None:
    return _truthy(_nested(cam, "child_info", "charge_state"))


@dataclass(frozen=True, kw_only=True)
class BaseusBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable = lambda cam: None


# Read-only feature-state sensors sourced from child_info.
FEATURE_SENSORS: tuple[BaseusBinaryDescription, ...] = (
    BaseusBinaryDescription(
        key="camera_enabled",
        translation_key="camera_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "camera_on")),
    ),
    BaseusBinaryDescription(
        key="motion_detection",
        translation_key="motion_detection",
        device_class=BinarySensorDeviceClass.MOTION,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "PIR", "pir_state")),
    ),
    BaseusBinaryDescription(
        key="status_light",
        translation_key="status_light",
        device_class=BinarySensorDeviceClass.LIGHT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "light_status")),
    ),
    BaseusBinaryDescription(
        key="night_vision",
        translation_key="night_vision",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: (
            None
            if _nested(c, "child_info", "NightVisionMode") is None
            else bool(_nested(c, "child_info", "NightVisionMode"))
        ),
    ),
    BaseusBinaryDescription(
        key="human_tracking",
        translation_key="human_tracking",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "HumanTracking")),
    ),
    BaseusBinaryDescription(
        key="low_power_mode",
        translation_key="low_power_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "LowPowerMode")),
    ),
    BaseusBinaryDescription(
        key="microphone",
        translation_key="microphone",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: _truthy(_nested(c, "child_info", "mic_status")),
    ),
    BaseusBinaryDescription(
        key="sd_card",
        translation_key="sd_card",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        # card_state == 1 means present/OK -> invert for PROBLEM semantics.
        value_fn=lambda c: (
            None
            if _nested(c, "base", "storage", "card_state") is None
            else not _truthy(_nested(c, "base", "storage", "card_state"))
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
            if (slug, "connectivity") not in known:
                known.add((slug, "connectivity"))
                new.append(BaseusConnectivity(coordinator, slug))
            if (slug, "charging") not in known and _charging(cam) is not None:
                known.add((slug, "charging"))
                new.append(BaseusCharging(coordinator, slug))
            for desc in FEATURE_SENSORS:
                marker = (slug, desc.key)
                if marker in known:
                    continue
                if desc.value_fn(cam) is None:
                    continue
                known.add(marker)
                new.append(BaseusFeatureBinary(coordinator, slug, desc))
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


class BaseusFeatureBinary(BaseusEntity, BinarySensorEntity):
    """Read-only reflection of a camera feature/setting state."""

    entity_description: BaseusBinaryDescription

    def __init__(
        self,
        coordinator: BaseusCoordinator,
        slug: str,
        description: BaseusBinaryDescription,
    ) -> None:
        super().__init__(coordinator, slug)
        self.entity_description = description
        self._attr_unique_id = f"{slug}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        cam = self._camera
        if cam is None:
            return None
        return self.entity_description.value_fn(cam)
