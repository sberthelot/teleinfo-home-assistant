# teleinfo-home-assistant
French TIC/Teleinfo integration for Home Assistant (needs a serial dongle/interface)

>The `teleinfo-home-assistant`component is a Home Assistant custom component for getting info from a **serial** dongle
>connected to a French "TIC/Teleinfo" capable electric meter. It includes mainly old "CBE" style and new Linky appliances

Please note that the current code has been migrated from "historical" to "standard" data encoding mode. This mode
is supported only on **Linky** appliances. The default mode is "historical" and may need a change request to Enedis
or your electricity reseller to change it to "standard".

*This custom component is to be considered a hobby project, developed as I see fit, and updated when I see a need, or am inspired by a feature request.  I am open for suggestions and issues detailing problems, but please don't expect me to fix it right away.*

## Installation
---
### Manual Installation
  1. Copy teleinfo-home-assistant folder into your custom_components folder in your hass configuration directory.
  2. Configure the `teleinfo-home-assistant` sensor (currently by editing configuration.yaml + sensor.yaml)
  3. Restart Home Assistant.

### Installation with HACS (Home Assistant Community Store)
(To be tested later)

## State and attributes
---

All documented configuration items are dynamicalled reported by this integration so the list is identical to the
Enedis-Linky-NOI-CPT_54E.pdf detailed informations. Please refer to this file for explanations and available values and mesurement units.

## Configuration
---

**Please check the protocol mode of your electricity meter : "historical" or "standard", only "standard" supported for now.**

Your **configuration.yaml** file should contain :
```
sensor: !include sensor.yaml

#experimental
homeassistant:
  customize: !include customize.yaml

```

Your **sensor.yaml** file would be like :
```
- platform: teleinfo
  name: "Enedis teleinfo"
  serial_port: '/dev/serial/by-id/usb-FTDI_FT230X_Basic_UART_TINFO-1131-if00-port0'
  # Try to use the more precise device name instead of ttyUSB0 if possible
  
- platform: template
  sensors:
    teleinfo_identifiant_compteur:
      friendly_name: "Identifiant compteur"
      value_template: '{{ states.sensor.enedis_teleinfo.attributes["PRM"] }}'
      icon_template: mdi:eye

    teleinfo_option_tarifaire:
      friendly_name: "Option tarifaire"
      value_template: '{{ states.sensor.enedis_teleinfo.attributes["NGTF"] }}'

    teleinfo_intensite_souscrite:
      friendly_name: "Intensite souscrite"
      value_template: '{{ states.sensor.enedis_teleinfo.attributes["PCOUP"] | int }}'
      unit_of_measurement: "A"
      icon_template: mdi:current-ac
      device_class: current

... add all items you need like this, don't forget to cast to int type if needed ...
```

Your **customize.yaml** file should be either **empty** or contain (__experimental__) :
```
sensor.enedis_teleinfo:
  unique_id: compteur1
  device_class: energy
  state_class: total_increasing
sensor.teleinfo_index_base:
  meter_type: '1'
  meter_type_name: ELECTRIC
  state_class: measurement
```
This is an experimental configuration to allow identifying the electric meter as a global power source for homeassistant
and report the global electricity consumed in the "Energy" tab and items

sensor.enedis_teleinfo:
  unique_id: compteur1
  device_class: energy
  state_class: total_increasing
sensor.teleinfo_index_base:
  meter_type: '1'
  meter_type_name: ELECTRIC
  state_class: measurement

## Implementation notes
---

Currently the code has been changed to synchronous IO access and opens/closes the serial port as needed.
Using asynchronous IO makes coding much more complex and would need a timer to update the status periodically, leaving
the serial port always open...
The next things to do are adding a easier configuration method (UI, ...) and allow selecting historical/standard mode

This working fine for me right now and is producing stable data over long periods, which is much better than my
previous implementation.
Some more functionnalities may be added like overconsumption alerts and so on, I will review it later (PR are welcome too ;) )
Have fun !
