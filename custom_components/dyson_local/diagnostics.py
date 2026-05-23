from typing import Any, cast
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_DEVICES, DOMAIN
from .libdyson.dyson_device import DysonDevice, DysonFanDevice


async def async_get_config_entry_diagnostics(hass: HomeAssistant, config_entry: ConfigEntry):
    device: DysonDevice = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    values = dict[str, dict]()

    status = cast(dict[str, Any], device._status)
    values["status"] = {x: DysonFanDevice._get_field_value(
        status, x, str) for x in status}

    if isinstance(device, DysonFanDevice):
        environment = device._environmental_data
        values["environment"] = {x: DysonFanDevice._get_field_value(
            environment, x, str) for x in environment}

    return values
