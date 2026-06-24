# TP-Link Wi-Fi Smart Plug Domoticz Plugin

A Python plugin for **Domoticz** to control and monitor **TP-Link HS100, HS103, and HS110** Wi-Fi Smart Plugs.

---

## Features

- **On/Off Switching:** Directly control the power state of your smart plugs from Domoticz.
- **Realtime Energy Monitoring (HS110):** Retrieve voltage (V), current (A), power (W), and total consumption (Wh) in real time.
- **Support for HS110 v2:** Correctly scales and parses the different measurement outputs of newer hardware versions (mV vs V, mA vs A, mW vs W, Wh vs kWh).
- **Graceful Error Handling:** Robust socket connection timeout handling prevents network drops or offline smart plugs from causing traceback errors in Domoticz logs.

---

## Installation

1. Clone this repository into your Domoticz `plugins` folder:
   ```bash
   cd domoticz/plugins
   git clone https://github.com/J0hnMatrix/domoticz-tplink-smartplug.git tplink-smartplug
   ```

2. Restart your Domoticz service to load the new plugin:
   ```bash
   sudo service domoticz.sh restart
   ```

3. Go to the **Hardware** settings page in the Domoticz Web UI and add the **TP-Link Wi-Fi Smart Plug HS100/HS110** type.

---

## File References

- Main Plugin Script: [plugin.py](file:///d:/dev/domoticz-tplink-smartplug/plugin.py)
- Configuration & Parameters: Defined in the XML docstring at the top of [plugin.py](file:///d:/dev/domoticz-tplink-smartplug/plugin.py#L9-L44)

---

## Changelog

### Version 1.0.0 (June 2026) — *John_Matrix*
- **Robust Exception Handling:** Trapped and gracefully handled connection timeouts (`socket.error`) in the socket communication helper, preventing system log cluttering with traceback logs.
- **Fixed Undefined Error Catch:** Resolved a `NameError` bug where `JSONDecodeError` was referenced without being imported.
- **Modern Python 3 Log Formatting:** Refactored logging and configuration dumps to use Python f-strings instead of string concatenation.
- **Safety Checks:** Added dictionary-existence checks (`if unit in Devices`) before updating device states, preventing runtime failures if devices are missing or deleted.
- **Code Refactoring:** Deduplicated telemetry parsing logic between HS110 v1 and v2.

### July 2019 — *lordzurp*
- Changed sensor types to display Watts (W) and Watt-hours (Wh) correctly.
- Added v2 hardware type support (handles mV to V, mA to A, mW to W, Wh to kWh scaling differences).
- Added automatic refresh of smartplug status.

### Original Creator
- Developed by **Dan Hallgren**, based on reverse engineering of the TP-Link HS110 by Lubomir Stroetmann and Tobias Esser.
