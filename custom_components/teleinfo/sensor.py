"""
Support for reading Teleinfo data from a serial port.

Teleinfo is a French specific protocol used in electricity smart meters.
It provides real time information on power consumption, rates and current on
a user accessible serial port.

Sample configuration.yaml

    sensor:
    - platform: teleinfo
        name: "EDF teleinfo"
        serial_port: "/dev/ttyAMA0"
    - platform: template
        sensors:
        teleinfo_base:
            value_template: '{{ (states.sensor.edf_teleinfo.
                attributes["BASE"] | float / 1000) | round(0) }}'
            unit_of_measurement: 'kWh'
            icon_template: mdi:flash
    - platform: template
        sensors:
        teleinfo_iinst1:
            value_template: '{{ states.sensor.edf_teleinfo.
                attributes["IINST1"] | int }}'
            unit_of_measurement: 'A'
            icon_template: mdi:flash

"""
from __future__ import annotations

import logging
import datetime
import asyncio

from serial import SerialException
import serial_asyncio_fast as serial_asyncio
import voluptuous as vol

from datetime import timedelta
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as TELEINFO_PLATFORM_SCHEMA,
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import (
    CONF_NAME,
    ATTR_ATTRIBUTION,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfApparentPower
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    TIC_MODE_HISTORICAL,
    TIC_MODE_STANDARD,
    TELEINFO_ENTITIES
)

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = "serial_port"
CONF_TIC_MODE = "tic_mode"
CONF_REFRESH = "refresh"

CONF_ATTRIBUTION = "Provided by EDF Teleinfo."

DEFAULT_NAME = "Teleinfo Sensor"
DEFAULT_TIC_MODE = TIC_MODE_HISTORICAL

FRAME_START = '\x02'
FRAME_END = '\x03'

DEFAULT_NAME = "Serial Teleinfo Sensor"
DEFAULT_REFRESH = 30

PLATFORM_SCHEMA = TELEINFO_PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Required(CONF_TIC_MODE, default=DEFAULT_TIC_MODE): vol.In(
        [
            TIC_MODE_HISTORICAL,
            TIC_MODE_STANDARD
        ]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_REFRESH, default=DEFAULT_REFRESH): vol.In([10,30,60,120,300]),
})

TELEINFO_TOTAL_ENERGY_KEY = 'EAST'

async def async_setup_platform(
    hass: HomeAssitant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None :
    """Set up the Teleinfo (serial) sensor platform."""
    name = DOMAIN + " Energie active soutirée totale"
    port = config.get(CONF_SERIAL_PORT)
    ticmode = config.get(CONF_TIC_MODE)
    refresh = timedelta(seconds=int(config.get(CONF_REFRESH)))
    
    teleinfo_total_energy_serial_sensor_entity = TeleinfoTotalEnergySerialSensorEntity(name, port, ticmode, refresh)
    
    entities = [teleinfo_total_energy_serial_sensor_entity];
    for eparam in TELEINFO_ENTITIES[ticmode]["string"]:
        e = TeleinfoStringSensorEntity(eparam['name'], eparam['key'],
            eparam['state_class'], eparam['device_class'], eparam['unit'], eparam['icon'])
        entities.append(e)

    for eparam in TELEINFO_ENTITIES[ticmode]["integer"]:
        e = TeleinfoIntegerSensorEntity(eparam['name'], eparam['key'],
            eparam['state_class'], eparam['device_class'], eparam['unit'], eparam['icon'])
        entities.append(e)

    async_add_entities(entities, True)

class TeleinfoTotalEnergySerialSensorEntity(SensorEntity):
    """Representation of a Teleinfo sensor."""

    def __init__(
        self,
        name,
        port,
        ticmode,
        refresh,
    ):
        """Initialize the Teleinfo Serial sensor."""
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id =f"teleinfo-{self._attr_name.lower()}"
        self._port = port
        self._ticmode = ticmode
        self._refresh = refresh
        self._attr_native_value = None
        
        self._attributes = {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
        }

    @callback
    async def async_added_to_hass(self) -> None:
        """Handle when an entity is about to be added to Home Assistant."""
        
        # Timer arm
        self._timer_cancel = async_track_time_interval(
            self.hass,
            self.read_frame,
            interval=self._refresh,
        )
        # Timer cancel
        self.async_on_remove(self._timer_cancel)

    @callback
    async def read_frame(self,_):
        """Read the data from the port."""
        try:
            if self._ticmode == TIC_MODE_HISTORICAL:
                baudrate = 1200
            else:
                baudrate = 9600
            
            reader, writer = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=baudrate,
                bytesize=serial_asyncio.serial.SEVENBITS,
                parity=serial_asyncio.serial.PARITY_EVEN,
                stopbits=serial_asyncio.serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=True,
                dsrdtr=False,
            )
        except SerialException:
            _LOGGER.exception("Unable to connect to the serial device %s", self._port)
            await self._timer_cancel()
        else:
            _LOGGER.debug("Serial device %s connected", self._port)
            
            try:
                # First read need to clear the grimlins.
                line = await reader.readline()
                line = line.decode('ascii').replace('\r', '').replace('\n', '')
        
                while FRAME_START not in line:
                    line = await reader.readline()
                    line = line.decode('ascii').replace('\r', '').replace('\n', '')
        
                _LOGGER.debug(" Start Frame")
                
                line=''
                while FRAME_END not in line:
                    line = await reader.readline()
                    line = line.decode('ascii').replace('\r', '').replace('\n', '')
                    
                    s = line.split('\t')
                    if len(s) == 3:
                        key = s[0]
                        value = s[1]
                        checksum = s[2]
                        ts = None
                    elif len(s) == 4:
                        key = s[0]
                        value = s[2]
                        checksum = s[3]
                        raw_ts = s[1][1:1+2*5]
                        ts = datetime.datetime.strptime(raw_ts, "%y%m%d%H%S")
                        
                    _LOGGER.debug(" Got : [%s] =  (%s)", key, value)
                    self.hass.bus.fire(
                        "teleinfo_"+ key + "_read_event",
                        {"value": value, "timestamp": ts},
                    )
                    
                    if key == TELEINFO_TOTAL_ENERGY_KEY:
                        self._attr_native_value = int(value)
                        self.async_write_ha_state()
                
                writer.close()
                await writer.wait_closed()
                
                _LOGGER.debug(" End Frame")
                
            except SerialException:
                _LOGGER.exception("Error while reading serial device %s", self._port)
                await self._timer_cancel()

    def _validate_checksum(self,frame,checksum):
        """Check if a frame is valid."""
        # Checksum validation method B
        datas = frame[:-1]
        if self._validate_checksum_internal(datas, checksum):
            return True

        # Checksum validation method A
        datas = frame[:-2]
        if self._validate_checksum_internal(datas, checksum):
            return True

        _LOGGER.warning(
            "Invalid checksum for %s : %s",
            frame,
            ord(checksum),
        )
        return False
    
    def _validate_checksum_internal(self, datas, checksum):
        """Check if a frame is valid."""
        computed_checksum = (sum(datas) & 0x3F) + 0x20
        if computed_checksum == ord(checksum):
            return True

        _LOGGER.debug(
            "Invalid checksum for %s : %s != %s",
            datas,
            computed_checksum,
            ord(checksum),
        )

        return False

    def detect():
        """Return a list of candidate paths for USB Teleinfo dongles.

        This method is currently a bit simplistic, it may need to be
        improved to support more configurations and OS.
        """
        globs_to_test = [
            "/dev/tty*",
            "/dev/serial/by-id/*",
            "/workspaces/integration_teleinfo/reader",
        ]
        found_paths = []
        for current_glob in globs_to_test:
            found_paths.extend(glob.glob(current_glob))

        return found_paths

    def validate_path(path: str):
        """Return True if the provided path points to a valid serial port, False otherwise."""
        try:
            # Creating the serial communicator will raise an exception
            # if it cannot connect
            with serial.serial_for_url(url=path):
                return True

        except serial.SerialException as exception:
            _LOGGER.warning("Serial path %s is invalid: %s", path, str(exception))
            return False

    @property
    def should_poll(self) -> bool:
        """Do not poll for those entities"""
        return False

    @property
    def state_class(self):
        return SensorStateClass.TOTAL_INCREASING

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfEnergy.WATT_HOUR

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, TELEINFO_TOTAL_ENERGY_KEY)},
            name=self._attr_name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )
        
class TeleinfoStringSensorEntity(SensorEntity):
    """Representation of a Teleinfo Integer sensor."""

    def __init__(
        self,
        name,
        key,
        state_class,
        device_class,
        unit,
        icon
    ) -> None:
        """Initialize"""
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_native_value = None
        self._key = key
        self._state_class = state_class
        self._device_class = device_class
        self._unit = unit
        self._icon = icon

        self._attributes = {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
        }

    @callback
    async def async_added_to_hass(self) -> None:
        """Handle when an entity is about to be added to Home Assistant."""
       
        listener_cancel = self.hass.bus.async_listen(
            "teleinfo_"+ self._key +"_read_event",
            self._on_event,
        )
        
        self.async_on_remove(listener_cancel)

    @callback
    async def _on_event(self, event: Event):
        self._attr_native_value = event.data['value']
        self.async_write_ha_state()

    @property
    def should_poll(self) -> bool:
        """Do not poll for those entities"""
        return False

    @property
    def state_class(self):
        return self._state_class

    @property
    def device_class(self):
        return self._device_class

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._unit

    @property
    def icon(self):
        return self._icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._key)},
            name=self._attr_name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )
        
class TeleinfoIntegerSensorEntity(TeleinfoStringSensorEntity):
    """Representation of a Teleinfo Integer sensor."""

    @callback
    async def _on_event(self, event: Event):
        self._attr_native_value = int(event.data['value'])
        self.async_write_ha_state()