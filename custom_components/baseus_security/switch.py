"""Switch platform: writable camera feature toggles.

These are only created when writable controls are enabled in the integration
options (and a confirmed set-action is pinned there). Discover the set-action
safely with ``python -m baseus_bridge probe-controls`` (see the bridge README).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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


@dataclass(frozen=True, kw_only=True)
class BaseusSwitchDescription(SwitchEntityDescription):
    # Device parameter to write and how to read its current state.
    param: str = ""
    read_fn: Callable = lambda cam: None
    level: str = "child"  # "child" or "base"


SWITCHES: tuple[BaseusSwitchDescription, ...] = (
    BaseusSwitchDescription(
        key="camera_enabled",
        translation_key="camera_enabled",
        param="camera_on",
        read_fn=lambda c: _nested(c, "child_info", "camera_on"),
    ),
    BaseusSwitchDescription(
        key="status_light",
        translation_key="status_light",
        entity_category=EntityCategory.CONFIG,
        param="light_status",
        read_fn=lambda c: _nested(c, "child_info", "light_status"),
    ),
    BaseusSwitchDescription(
        key="night_vision",
        translation_key="night_vision",
        entity_category=EntityCategory.CONFIG,
        param="NightVisionMode",
        read_fn=lambda c: _nested(c, "child_info", "NightVisionMode"),
    ),
    BaseusSwitchDescription(
        key="human_tracking",
        translation_key="human_tracking",
        entity_category=EntityCategory.CONFIG,
        param="HumanTracking",
        read_fn=lambda c: _nested(c, "child_info", "HumanTracking"),
    ),
    BaseusSwitchDescription(
        key="low_power_mode",
        translation_key="low_power_mode",
        entity_category=EntityCategory.CONFIG,
        param="LowPowerMode",
        read_fn=lambda c: _nested(c, "child_info", "LowPowerMode"),
    ),
    BaseusSwitchDescription(
        key="microphone",
        translation_key="microphone",
        entity_category=EntityCategory.CONFIG,
        param="mic_status",
        read_fn=lambda c: _nested(c, "child_info", "mic_status"),
    ),
    BaseusSwitchDescription(
        key="osd_logo",
        translation_key="osd_logo",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        param="osd_logo",
        read_fn=lambda c: _nested(c, "child_info", "osd_logo"),
    ),
    BaseusSwitchDescription(
        key="alert_voice",
        translation_key="alert_voice",
        entity_category=EntityCategory.CONFIG,
        param="alert_voice",
        read_fn=lambda c: _nested(c, "child_info", "alert_voice"),
    ),
    BaseusSwitchDescription(
        key="base_led",
        translation_key="base_led",
        entity_category=EntityCategory.CONFIG,
        param="led_status",
        level="base",
        read_fn=lambda c: _nested(c, "base", "led_status"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BaseusCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.controls_enabled:
        return
    known: set[tuple[str, str]] = set()

    @callback
    def _sync() -> None:
        new = []
        for slug, cam in (coordinator.data or {}).items():
            for desc in SWITCHES:
                marker = (slug, desc.key)
                if marker in known or desc.read_fn(cam) is None:
                    continue
                known.add(marker)
                new.append(BaseusSwitch(coordinator, slug, desc))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusSwitch(BaseusEntity, SwitchEntity):
    entity_description: BaseusSwitchDescription

    def __init__(
        self,
        coordinator: BaseusCoordinator,
        slug: str,
        description: BaseusSwitchDescription,
    ) -> None:
        super().__init__(coordinator, slug)
        self.entity_description = description
        self._attr_unique_id = f"{slug}_{description.key}_switch"

    @property
    def is_on(self) -> bool | None:
        cam = self._camera
        if cam is None:
            return None
        val = self.entity_description.read_fn(cam)
        return None if val is None else bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_param(
            self._slug, self.entity_description.param, 1,
            level=self.entity_description.level,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_param(
            self._slug, self.entity_description.param, 0,
            level=self.entity_description.level,
        )
