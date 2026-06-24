# Domoticz TP-Link Wi-Fi Smart Plug plugin
#
# Plugin based on reverse engineering of the TP-Link HS110, courtesy of Lubomir Stroetmann and Tobias Esser.
# https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/
#
# Author: Dan Hallgren
#
"""
<plugin key="tplinksmartplug" name="TP-Link Wi-Fi Smart Plug HS100/HS110" version="1.0.0" author="Dan Hallgren / John_Matrix" wikilink="https://github.com/J0hnMatrix/domoticz-tplink-smartplug">
    <description>
        <h2>TP-Link Wi-Fi Smart Plug</h2>
        <ul style="list-sytel-type:square">
            <li>on/off switching</li>
            <li>emeter realtime power (HS110)</li>
            <li>emeter realtime current (HS110)</li>
            <li>emeter realtime voltage (HS110)</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>switch - On/Off</li>
            <li>power - Realtime power in Watts</li>
            <li>current - Realtime current in ampere</li>
            <li>voltage - Voltage input</li>
        </ul>
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" required="true"/>
        <param field="Mode1" label="Model" width="150px" required="false">
             <options>
                <option label="HS100" value="HS100" default="true"/>
                <option label="HS110" value="HS110"  default="false"/>
                <option label="HS110v2" value="HS110v2"  default="false"/>
            </options>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import json
import socket

import Domoticz

PORT = 9999
STATES = ('off', 'on', 'unknown')


class TpLinkSmartPlugPlugin:
    enabled = False
    connection = None

    def __init__(self):
        self.interval = 6  # 6*10 seconds
        self.heartbeatcounter = 0

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            DumpConfigToLog()

        if len(Devices) == 0:
            Domoticz.Device(Name="switch", Unit=1, TypeName="Switch", Used=1).Create()
            Domoticz.Log("Tp-Link smart plug device created")

        if (Parameters["Mode1"] in ("HS110", "HS110v2")) and len(Devices) <= 1:
            # Create more devices here
            Domoticz.Device(Name="(A)", Unit=2, Type=243, Subtype=23).Create()
            Domoticz.Device(Name="(V)", Unit=3, Type=243, Subtype=8).Create()
            Domoticz.Device(Name="(W)", Unit=4, Type=243, Subtype=29).Create()

        state = self.get_switch_state()
        if 1 in Devices:
            if state == 'off':
                Devices[1].Update(0, '0')
            elif state == 'on':
                Devices[1].Update(1, '100')
            else:
                Devices[1].Update(1, '50')

    def onStop(self):
        # Domoticz.Log("onStop called")
        pass

    def onConnect(self, Connection, Status, Description):
        # Domoticz.Log("onConnect called")
        pass

    def onMessage(self, Connection, Data, Status, Extra):
        # Domoticz.Log("onMessage called")
        pass

    def onCommand(self, unit, command, level, hue):
        Domoticz.Log(f"onCommand called for Unit {unit}: Parameter '{command}', Level: {level}")

        command_lower = command.lower()
        if command_lower == 'on':
            cmd = {
                "system": {
                    "set_relay_state": {"state": 1}
                }
            }
            state = (1, '100')
        elif command_lower == 'off':
            cmd = {
                "system": {
                    "set_relay_state": {"state": 0}
                }
            }
            state = (0, '0')
        else:
            Domoticz.Log(f"Unknown command: {command}")
            return

        result = self._send_json_cmd(json.dumps(cmd))
        Domoticz.Debug(f"got response: {result}")

        err_code = result.get('system', {}).get('set_relay_state', {}).get('err_code', 1)

        if err_code == 0 and 1 in Devices:
            Devices[1].Update(*state)

        # Reset counter so we trigger emeter poll next heartbeat
        self.heartbeatcounter = 0

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log(f"Notification: {Name},{Subject},{Text},{Status},{Priority},{Sound},{ImageFile}")

    def onDisconnect(self, Connection):
        # Domoticz.Log("onDisconnect called")
        pass

    def onHeartbeat(self):
        if self.heartbeatcounter % self.interval == 0:
            self.update_emeter_values()
        state = self.get_switch_state()
        if 1 in Devices:
            if state == 'off':
                Devices[1].Update(0, '0')
            elif state == 'on':
                Devices[1].Update(1, '100')
            else:
                Devices[1].Update(1, '50')
        self.heartbeatcounter += 1

    def _encrypt(self, data):
        key = 171
        result = b"\x00\x00\x00" + chr(len(data)).encode('latin-1')
        for i in data.encode('latin-1'):
            a = key ^ i
            key = a
            result += bytes([a])
        return result

    def _decrypt(self, data):
        key = 171
        result = ""
        for i in data:
            a = key ^ i
            key = i
            result += bytes([a]).decode('latin-1')
        return result

    def _send_json_cmd(self, cmd):
        ret = {}
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            sock.connect((Parameters["Address"], PORT))
            data = self._encrypt(cmd)
            sock.send(data)
            data = sock.recv(1024)
            Domoticz.Debug(f"data len: {len(data)}")
            sock.close()
        except socket.error as e:
            Domoticz.Log(f"send command error: {e}")
            return ret

        try:
            json_resp = self._decrypt(data[4:])
            ret = json.loads(json_resp)
        except (TypeError, ValueError) as e:
            Domoticz.Log(f"decode error: {e}")
            Domoticz.Log(f"data: {data}")
            return ret

        return ret

    def update_emeter_values(self):
        mode = Parameters["Mode1"]
        if mode not in ("HS110", "HS110v2"):
            return

        cmd = {
            "emeter": {
                "get_realtime": {}
            }
        }

        result = self._send_json_cmd(json.dumps(cmd))
        Domoticz.Debug(f"got response: {result}")

        realtime_result = result.get('emeter', {}).get('get_realtime', {})
        err_code = realtime_result.get('err_code', 1)

        if err_code == 0:
            try:
                if mode == "HS110":
                    current = round(realtime_result['current'], 2)
                    voltage = round(realtime_result['voltage'], 2)
                    power = round(realtime_result['power'], 2)
                    total = realtime_result['total'] * 1000
                else:  # HS110v2
                    current = round(realtime_result['current_ma'] / 1000, 2)
                    voltage = round(realtime_result['voltage_mv'] / 1000, 2)
                    power = round(realtime_result['power_mw'] / 1000, 2)
                    total = realtime_result['total_wh']

                if 2 in Devices:
                    Devices[2].Update(nValue=0, sValue=str(current))
                if 3 in Devices:
                    Devices[3].Update(nValue=0, sValue=str(voltage))
                if 4 in Devices:
                    Devices[4].Update(nValue=0, sValue=f"{power};{total}")
            except (KeyError, TypeError) as e:
                Domoticz.Log(f"Error parsing emeter response: {e}")


#power = round(float(json_data['emeter']['get_realtime']['power_mw']) / 1000,2)


    def get_switch_state(self):
        cmd = {
            "system": {
                "get_sysinfo": "null"
            }
        }
        result = self._send_json_cmd(json.dumps(cmd))
        Domoticz.Debug(f"sysinfo response: {result}")

        err_code = result.get('system', {}).get('get_sysinfo', {}).get('err_code', 1)

        state = 2  # 'unknown'
        if err_code == 0:
            try:
                state = result['system']['get_sysinfo']['relay_state']
                if state not in (0, 1):
                    state = 2
            except (KeyError, TypeError):
                state = 2

        return STATES[state]


global _plugin
_plugin = TpLinkSmartPlugPlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Connection, Data, Status, Extra)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug(f"'{x}':'{Parameters[x]}'")
    Domoticz.Debug(f"Device count: {len(Devices)}")
    for x in Devices:
        Domoticz.Debug(f"Device:           {x} - {Devices[x]}")
        Domoticz.Debug(f"Device ID:       '{Devices[x].ID}'")
        Domoticz.Debug(f"Device Name:     '{Devices[x].Name}'")
        Domoticz.Debug(f"Device nValue:    {Devices[x].nValue}")
        Domoticz.Debug(f"Device sValue:   '{Devices[x].sValue}'")
        Domoticz.Debug(f"Device LastLevel: {Devices[x].LastLevel}")
    return
