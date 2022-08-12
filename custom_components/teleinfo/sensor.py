"""
Support for reading Teleinfo data from a serial port.

Teleinfo is a French specific protocol used in electricity smart meters.
It provides real time information on power consumption, rates and current on
a user accessible serial port.

For more details about this platform, please refer to the documentation at
https://www.enedis.fr/sites/default/files/Enedis-NOI-CPT_02E.pdf

Work based on https://github.com/nlamirault

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
import logging
import datetime
import serial

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, STATE_CLASS_TOTAL_INCREASING
from homeassistant.const import (
    CONF_NAME, EVENT_HOMEASSISTANT_STOP, ATTR_ATTRIBUTION, DEVICE_CLASS_ENERGY)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

FRAME_START = '\x02'
FRAME_END = '\x03'

CONF_SERIAL_PORT = 'serial_port'

CONF_ATTRIBUTION = "Provided by EDF Teleinfo."

DEFAULT_NAME = "Serial Teleinfo Sensor"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

TELEINFO_SELF_VALUE = 'EAST'

TIMEOUT = 30

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Serial sensor platform."""
    name = config.get(CONF_NAME)
    port = config.get(CONF_SERIAL_PORT)
    sensor = SerialTeleinfoSensor(name, port)

    add_entities([sensor], True)

class SerialTeleinfoSensor(Entity):
    """Representation of a Serial sensor."""

    def __init__(self, name, port):
        """Initialize the Serial sensor."""
        self._name = name
        self._port = port
        self._state = None
        self._attributes = {
            ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
        }

    def update(self):
        """Process the data."""
        _LOGGER.debug("Start update")
        is_over = False

        self._reader = serial.Serial(self._port, baudrate=9600, bytesize=7,
            parity='E', stopbits=1, rtscts=1, timeout=TIMEOUT)

        # First read need to clear the grimlins.
        line = self._reader.readline()
        line = line.decode('ascii').replace('\r', '').replace('\n', '')

        while FRAME_START not in line:
            line = self._reader.readline()
            line = line.decode('ascii').replace('\r', '').replace('\n', '')

        _LOGGER.debug(" Start Frame")
        line=''
        while FRAME_END not in line:
            line = self._reader.readline()
            line = line.decode('ascii').replace('\r', '').replace('\n', '')

            s = line.split('\t')
            if len(s) == 3:
                name = s[0]
                value = s[1]
                checksum = s[2]
                ts = None
            elif len(s) == 4:
                name = s[0]
                value = s[2]
                checksum = s[3]
                raw_ts = s[1][1:1+2*5]
                ts = datetime.datetime.strptime(raw_ts, "%y%m%d%H%S")

            _LOGGER.debug(" Got : [%s] =  (%s)", name, value)
            self._attributes[name] = value
            if name == TELEINFO_SELF_VALUE:
                self._state = int(self._attributes[TELEINFO_SELF_VALUE])

        self._reader.close()
        _LOGGER.debug(" End Frame")

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def state_class(self):
        return STATE_CLASS_TOTAL_INCREASING # so far no const available in homeassistant core

    @property
    def device_class(self):
        return DEVICE_CLASS_ENERGY

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"teleinfo-{self._name.lower()}"

    @property
    def unit_of_measurement(self):
        return "Wh"

    @property
    def icon(self):
        return "mdi:counter"
