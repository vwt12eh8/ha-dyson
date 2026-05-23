"""Sensor platform for dyson."""

from abc import abstractmethod
from typing import Callable

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
                                 CONF_NAME, PERCENTAGE, EntityCategory,
                                 UnitOfTemperature, UnitOfTime)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (CoordinatorEntity,
                                                      DataUpdateCoordinator)

from . import DysonEntity
from .const import DATA_COORDINATORS, DATA_DEVICES, DOMAIN
from .libdyson import (Dyson360Eye, Dyson360Heurist, DysonDevice,
                       DysonPureCoolLink, DysonPureHumidifyCool,
                       DysonPurifierHumidifyCoolFormaldehyde)
from .libdyson.const import Environmental, MessageType
from .libdyson.dyson_device import DysonFanDevice
from .libdyson.dyson_pure_cool import DysonPureCoolBase
from .libdyson.dyson_vacuum_device import DysonVacuumDevice
from .utils import filter_unavailable, is_available


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable
) -> None:
    """Set up Dyson sensor from a config entry."""
    device = hass.data[DOMAIN][DATA_DEVICES][config_entry.entry_id]
    name = config_entry.data[CONF_NAME]
    if isinstance(device, Dyson360Eye) or isinstance(device, Dyson360Heurist):
        entities = [DysonBatterySensor(device, name)]
    else:
        coordinator = hass.data[DOMAIN][DATA_COORDINATORS][config_entry.entry_id]
        entities = [
            DysonHumiditySensor(coordinator, device, name),
            DysonTemperatureSensor(coordinator, device, name),
            DysonVOCSensor(coordinator, device, name),
        ]
        if isinstance(device, DysonPureCoolLink):
            entities.extend(
                [
                    DysonFilterLifeSensor(device, name),
                    DysonParticulatesSensor(coordinator, device, name),
                ]
            )
        else:  # DysonPureCool or DysonPureHumidifyCool
            entities.extend(
                [
                    DysonPM25Sensor(coordinator, device, name),
                    DysonPM10Sensor(coordinator, device, name),
                    DysonNO2Sensor(coordinator, device, name),
                ]
            )
            if device.carbon_filter_life is None:
                entities.append(DysonCombinedFilterLifeSensor(device, name))
            else:
                entities.extend(
                    [
                        DysonCarbonFilterLifeSensor(device, name),
                        DysonHEPAFilterLifeSensor(device, name),
                    ]
                )
        if isinstance(device, DysonPureHumidifyCool) or isinstance(
            device, DysonPurifierHumidifyCoolFormaldehyde):
            entities.append(DysonNextDeepCleanSensor(device, name))
        if isinstance(device, DysonPurifierHumidifyCoolFormaldehyde):
            entities.append(DysonHCHOSensor(coordinator, device, name))
    async_add_entities(entities)


class DysonSensor(SensorEntity, DysonEntity):
    """Base class for a Dyson sensor."""

    _MESSAGE_TYPE = MessageType.STATE
    _SENSOR_TYPE = None

    def __init__(self, device: DysonDevice, name: str):
        """Initialize the sensor."""
        super().__init__(device, name)

    @property
    def sub_unique_id(self):
        """Return the sensor's unique id."""
        return self._SENSOR_TYPE


class DysonSensorEnvironmental(CoordinatorEntity, DysonSensor):
    """Dyson environmental sensor."""

    _MESSAGE_TYPE = MessageType.ENVIRONMENTAL
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: DataUpdateCoordinator, device: DysonDevice, name: str
    ):
        """Initialize the environmental sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        DysonSensor.__init__(self, device, name)

    @property
    def available(self) -> bool:
        return is_available(self._native_value)

    @property
    def native_value(self):
        return filter_unavailable(self._native_value)

    @property
    @abstractmethod
    def _native_value(self) -> int | float | Environmental:
        ...


class DysonBatterySensor(DysonSensor):
    """Dyson battery sensor."""

    _SENSOR_TYPE = "battery_level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonVacuumDevice

    @property
    def native_value(self):
        return self._device.battery_level


class DysonFilterLifeSensor(DysonSensor):
    """Dyson filter life sensor (in hours) for Pure Cool Link."""

    _SENSOR_TYPE = "filter_life"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_translation_key = "filter_life"
    _device: DysonPureCoolLink

    @property
    def native_value(self):
        return self._device.filter_life


class DysonCarbonFilterLifeSensor(DysonSensor):
    """Dyson carbon filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "carbon_filter_life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_name = "Carbon filter life"
    _attr_native_unit_of_measurement = PERCENTAGE
    _device: DysonPureCoolBase

    @property
    def native_value(self):
        return self._device.carbon_filter_life


class DysonHEPAFilterLifeSensor(DysonSensor):
    """Dyson HEPA filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "hepa_filter_life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_name = "HEPA filter life"
    _attr_native_unit_of_measurement = PERCENTAGE
    _device: DysonPureCoolBase

    @property
    def native_value(self):
        return self._device.hepa_filter_life


class DysonCombinedFilterLifeSensor(DysonSensor):
    """Dyson combined filter life sensor (in percentage) for Pure Cool."""

    _SENSOR_TYPE = "combined_filter_life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "filter_life"
    _device: DysonPureCoolBase

    @property
    def native_value(self):
        return self._device.hepa_filter_life


class DysonNextDeepCleanSensor(DysonSensor):
    """Sensor of time until next deep clean (in hours) for Dyson Pure Humidify+Cool."""

    _SENSOR_TYPE = "next_deep_clean"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_translation_key = "next_deep_clean"
    _device: DysonPureHumidifyCool

    @property
    def native_value(self):
        return self._device.time_until_next_clean


class DysonHumiditySensor(DysonSensorEnvironmental):
    """Dyson humidity sensor."""

    _SENSOR_TYPE = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonFanDevice

    @property
    def _native_value(self):
        return self._device.humidity


class DysonTemperatureSensor(DysonSensorEnvironmental):
    """Dyson temperature sensor."""

    _SENSOR_TYPE = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.KELVIN
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonFanDevice

    @property
    def _native_value(self):
        return self._device.temperature


class DysonPM25Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 2.5 fine particulate matters."""

    _SENSOR_TYPE = "pm25"
    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonPureCoolBase

    @property
    def _native_value(self):
        return self._device.particulate_matter_2_5


class DysonPM10Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 10 particulate matters."""

    _SENSOR_TYPE = "pm10"
    _attr_device_class = SensorDeviceClass.PM10
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonPureCoolBase

    @property
    def _native_value(self):
        return self._device.particulate_matter_10


class DysonParticulatesSensor(DysonSensorEnvironmental):
    """Dyson sensor for particulate matters for "Link" devices."""

    _SENSOR_TYPE = "pm1"
    _attr_device_class = SensorDeviceClass.PM1
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonPureCoolLink

    @property
    def _native_value(self):
        return self._device.particulates


class DysonVOCSensor(DysonSensorEnvironmental):
    """Dyson sensor for volatile organic compounds."""

    _SENSOR_TYPE = "voc"
    _attr_icon = "mdi:molecule"
    _attr_name = "VOC"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonPureCoolBase

    @property
    def native_value(self):
        value = super().native_value
        if value is None:
            return None
        return value / 10

    @property
    def _native_value(self):
        return self._device.volatile_organic_compounds


class DysonNO2Sensor(DysonSensorEnvironmental):
    """Dyson sensor for Nitrogen Dioxide."""

    _SENSOR_TYPE = "no2"
    _attr_icon = "mdi:molecule"
    _attr_name = "NO₂"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _device: DysonPureCoolBase

    @property
    def native_value(self):
        value = super().native_value
        if value is None:
            return None
        return value / 10

    @property
    def _native_value(self):
        return self._device.nitrogen_dioxide


class DysonHCHOSensor(DysonSensorEnvironmental):
    """Dyson sensor for Formaldehyde."""

    _SENSOR_TYPE = "hcho"
    _attr_icon = "mdi:molecule"
    _attr_native_unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "hcho"
    _device: DysonPurifierHumidifyCoolFormaldehyde

    @property
    def _native_value(self):
        return self._device.formaldehyde
