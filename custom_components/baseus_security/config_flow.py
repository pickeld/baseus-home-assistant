"""Config flow for the Baseus Security integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_ACCOUNT,
    CONF_COUNTRY_CODE,
    CONF_INCLUDE_OFFLINE,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_RTSP_BASE,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_INCLUDE_OFFLINE,
    DEFAULT_REGION,
    DEFAULT_RTSP_BASE,
    DOMAIN,
    REGIONS,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_ACCOUNT, default=defaults.get(CONF_ACCOUNT, "")): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(
                CONF_RTSP_BASE, default=defaults.get(CONF_RTSP_BASE, DEFAULT_RTSP_BASE)
            ): str,
            vol.Optional(
                CONF_REGION, default=defaults.get(CONF_REGION, DEFAULT_REGION)
            ): vol.In(REGIONS),
            vol.Optional(
                CONF_COUNTRY_CODE,
                default=defaults.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
            ): str,
            vol.Optional(
                CONF_INCLUDE_OFFLINE,
                default=defaults.get(CONF_INCLUDE_OFFLINE, DEFAULT_INCLUDE_OFFLINE),
            ): bool,
        }
    )


class BaseusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Baseus Security."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            account = user_input[CONF_ACCOUNT].strip()
            await self.async_set_unique_id(account.lower())
            self._abort_if_unique_id_configured()

            valid = await self.hass.async_add_executor_job(
                self._validate_login, user_input
            )
            if valid is True:
                # Normalise the RTSP base (strip a trailing slash).
                user_input[CONF_RTSP_BASE] = user_input[CONF_RTSP_BASE].rstrip("/")
                user_input[CONF_ACCOUNT] = account
                return self.async_create_entry(title=account, data=user_input)
            errors["base"] = valid  # error code string

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    @staticmethod
    def _validate_login(user_input: dict[str, Any]) -> Any:
        """Return True on success, or an error code string on failure."""
        try:
            from baseus_bridge.cloud import BaseusCloud, CloudError
        except Exception:  # pragma: no cover - dependency missing
            return "dependency_missing"

        client = BaseusCloud(
            account=user_input[CONF_ACCOUNT].strip(),
            password=user_input[CONF_PASSWORD],
            region=user_input.get(CONF_REGION, DEFAULT_REGION),
            country_code=user_input.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
        )
        try:
            client.login()
        except CloudError:
            return "invalid_auth"
        except Exception:  # pragma: no cover - network/other
            return "cannot_connect"
        return True
