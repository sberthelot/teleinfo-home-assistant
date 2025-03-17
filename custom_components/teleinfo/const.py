"""Constants for teleinformation."""

from homeassistant.components.sensor import (
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    Platform,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfApparentPower,
)


DOMAIN = "teleinfo"
DEVICE_MANUFACTURER = "Enedis"
VERSION = "0.9.9-20250312"

PLATFORMS: list[Platform] = [Platform.SENSOR]

TIC_MODE_HISTORICAL = "historical"
TIC_MODE_STANDARD = "standard"

TELEINFO_ENTITIES = {
    TIC_MODE_HISTORICAL: [
        ],

    TIC_MODE_STANDARD: {
        "string": [
                    {
                        "name": DOMAIN + ' Nom du calendrier tarifaire fournisseur',
                        "key": 'NGTF',
                        "state_class": None,
                        "device_class": SensorDeviceClass.ENUM,
                        "unit": None,
                        "icon": None
                    },
                    {
                        "name": DOMAIN + ' Libellé tarif fournisseur en cours',
                        "key": 'LTARF',
                        "state_class": None,
                        "device_class": SensorDeviceClass.ENUM,
                        "unit": None,
                        "icon": None
                    },
                    {
                        "name": DOMAIN + ' PRM',
                        "key": 'PRM',
                        "state_class": None,
                        "device_class": SensorDeviceClass.ENUM,
                        "unit": None,
                        "icon": 'mdi:eye'
                    },
            ],
        "integer": [
                    {
                        "name": DOMAIN + ' Courant efficace, phase 1',
                        "key": 'IRMS1',
                        "state_class": SensorStateClass.MEASUREMENT,
                        "device_class": SensorDeviceClass.CURRENT,
                        "unit": UnitOfElectricCurrent.AMPERE,
                        "icon": 'mdi:current-ac'
                    },
                    {
                        "name": DOMAIN + ' Puissance app. de coupure',
                        "key": 'PCOUP',
                        "state_class": SensorStateClass.MEASUREMENT,
                        "device_class": SensorDeviceClass.POWER,
                        "unit": UnitOfPower.KILO_WATT,
                        "icon": 'mdi:current-ac'
                    },
                    {
                        "name": DOMAIN + ' Puissance app. instantanée soutirée',
                        "key": 'SINSTS',
                        "state_class": SensorStateClass.MEASUREMENT,
                        "device_class": SensorDeviceClass.APPARENT_POWER,
                        "unit": UnitOfApparentPower.VOLT_AMPERE,
                        "icon": 'mdi:flash'
                    },
                    {
                        "name": DOMAIN + ' Puissance app. max. soutirée n',
                        "key": 'SMAXSN',
                        "state_class": SensorStateClass.MEASUREMENT,
                        "device_class": SensorDeviceClass.APPARENT_POWER,
                        "unit": UnitOfApparentPower.VOLT_AMPERE,
                        "icon": 'mdi:flash'
                    },
            ]
        }
    }