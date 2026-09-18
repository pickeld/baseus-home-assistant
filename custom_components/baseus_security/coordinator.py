"""Data coordinator: refresh the camera list/status from the Baseus cloud.

All cloud communication is delegated to the ``baseus_bridge.cloud`` client
(shipped by the baseus-cam-bridge project) so this integration keeps no
protocol logic of its own. The blocking cloud call runs in the executor.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ACCOUNT,
    CONF_COUNTRY_CODE,
    CONF_ENABLE_CONTROLS,
    CONF_INCLUDE_OFFLINE,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SET_ACTION,
    CONF_SET_ACTION_BASE,
    CONF_SET_SHAPE,
    CONF_SET_SHAPE_BASE,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_ENABLE_CONTROLS,
    DEFAULT_INCLUDE_OFFLINE,
    DEFAULT_REGION,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class BaseusCoordinator(DataUpdateCoordinator):
    """Poll the account's camera list and keep it keyed by slug."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name="baseus_security",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    def _fetch(self) -> dict:
        """Blocking cloud fetch, executed in a worker thread."""
        # Imported lazily so HA only needs the dependency at runtime.
        from baseus_bridge.cloud import BaseusCloud, CloudError

        data = self.entry.data
        client = BaseusCloud(
            account=data[CONF_ACCOUNT],
            password=data[CONF_PASSWORD],
            region=data.get(CONF_REGION, DEFAULT_REGION),
            country_code=data.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
        )
        try:
            cameras = client.discover_cameras()
        except CloudError as err:
            raise UpdateFailed(str(err)) from err

        include_offline = data.get(CONF_INCLUDE_OFFLINE, DEFAULT_INCLUDE_OFFLINE)
        result: dict[str, object] = {}
        for cam in cameras:
            if not include_offline and not cam.online:
                continue
            result[cam.slug] = cam
        return result

    async def _async_update_data(self) -> dict:
        return await self.hass.async_add_executor_job(self._fetch)

    # --- writable controls ---
    @property
    def controls_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_ENABLE_CONTROLS, DEFAULT_ENABLE_CONTROLS))

    def _set_param_blocking(self, cam, key, value, level: str):
        from baseus_bridge.cloud import BaseusCloud, CloudError

        data = self.entry.data
        opts = self.entry.options
        if level == "base":
            action = opts.get(CONF_SET_ACTION_BASE) or opts.get(CONF_SET_ACTION) or None
            shape = opts.get(CONF_SET_SHAPE_BASE) or opts.get(CONF_SET_SHAPE) or None
        else:
            action = opts.get(CONF_SET_ACTION) or None
            shape = opts.get(CONF_SET_SHAPE) or None
        client = BaseusCloud(
            account=data[CONF_ACCOUNT],
            password=data[CONF_PASSWORD],
            region=data.get(CONF_REGION, DEFAULT_REGION),
            country_code=data.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
        )
        try:
            client.login()
            if level == "base":
                return client.set_device_param(
                    cam.device_sn, key, value, action=action, shape=shape)
            return client.set_device_param(
                cam.device_sn, key, value, action=action, shape=shape,
                channel=cam.channel, child_sn=cam.camera_sn)
        except CloudError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_set_param(self, slug: str, key: str, value, *, level: str = "child") -> None:
        """Set a device/camera parameter via the cloud, then refresh state."""
        cam = (self.data or {}).get(slug)
        if cam is None:
            raise HomeAssistantError(f"unknown camera {slug!r}")
        accepted, resp = await self.hass.async_add_executor_job(
            self._set_param_blocking, cam, key, value, level
        )
        if not accepted:
            raise HomeAssistantError(
                f"device rejected {key}={value} (code={resp.get('code')}). "
                "Confirm the set-action via `probe-controls` and the integration options."
            )
        await self.async_request_refresh()
