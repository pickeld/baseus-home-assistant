"""Number platform: writable camera levels (volumes, sensitivity).

Only created when writable controls are enabled in the integration options.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
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
class BaseusNumberDescription(NumberEntityDescription):
    param: str = ""
    read_fn: Callable = lambda cam: None
    level: str = "child"


NUMBERS: tuple[BaseusNumberDescription, ...] = (
    BaseusNumberDescription(
        key="speaker_volume",
        translation_key="speaker_volume",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        param="speaker_vol",
        read_fn=lambda c: _nested(c, "child_info", "speaker_vol"),
    ),
    BaseusNumberDescription(
        key="prompt_volume",
        translation_key="prompt_volume",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        param="prompt_vol",
        read_fn=lambda c: _nested(c, "child_info", "prompt_vol"),
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
            for desc in NUMBERS:
                marker = (slug, desc.key)
                if marker in known or desc.read_fn(cam) is None:
                    continue
                known.add(marker)
                new.append(BaseusNumber(coordinator, slug, desc))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusNumber(BaseusEntity, NumberEntity):
    entity_description: BaseusNumberDescription

    def __init__(
        self,
        coordinator: BaseusCoordinator,
        slug: str,
        description: BaseusNumberDescription,
    ) -> None:
        super().__init__(coordinator, slug)
        self.entity_description = description
        self._attr_unique_id = f"{slug}_{description.key}_number"

    @property
    def native_value(self) -> float | None:
        cam = self._camera
        if cam is None:
            return None
        val = self.entity_description.read_fn(cam)
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_param(
            self._slug, self.entity_description.param, int(value),
            level=self.entity_description.level,
        )
