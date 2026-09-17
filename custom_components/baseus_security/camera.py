"""Camera platform: one entity per Baseus camera, streamed via the bridge."""
from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_RTSP_BASE, DOMAIN
from .coordinator import BaseusCoordinator
from .entity import BaseusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BaseusCoordinator = hass.data[DOMAIN][entry.entry_id]
    rtsp_base = entry.data[CONF_RTSP_BASE].rstrip("/")

    known: set[str] = set()

    @callback
    def _sync() -> None:
        new = []
        for slug in coordinator.data or {}:
            if slug in known:
                continue
            known.add(slug)
            new.append(BaseusCamera(coordinator, slug, rtsp_base))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))


class BaseusCamera(BaseusEntity, Camera):
    """A single Baseus camera exposed as an RTSP stream."""

    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_name = None  # use the device name

    def __init__(
        self, coordinator: BaseusCoordinator, slug: str, rtsp_base: str
    ) -> None:
        BaseusEntity.__init__(self, coordinator, slug)
        Camera.__init__(self)
        self._rtsp_base = rtsp_base
        self._attr_unique_id = f"{slug}_camera"

    async def stream_source(self) -> str | None:
        return f"{self._rtsp_base}/{self._slug}"
