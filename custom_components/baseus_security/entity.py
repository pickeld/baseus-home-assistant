"""Shared base entity for Baseus Security."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import BaseusCoordinator


class BaseusEntity(CoordinatorEntity[BaseusCoordinator]):
    """Base entity tied to one camera slug in the coordinator data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BaseusCoordinator, slug: str) -> None:
        super().__init__(coordinator)
        self._slug = slug

    @property
    def _camera(self):
        return (self.coordinator.data or {}).get(self._slug)

    @property
    def available(self) -> bool:
        return super().available and self._camera is not None

    @property
    def device_info(self) -> DeviceInfo:
        cam = self._camera
        name = cam.name if cam else self._slug
        model = getattr(cam, "model", "") if cam else ""
        return DeviceInfo(
            identifiers={(DOMAIN, self._slug)},
            name=name,
            manufacturer=MANUFACTURER,
            model=model or "Baseus Security Camera",
        )
