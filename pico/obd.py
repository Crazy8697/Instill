# obd.py — BLE OBD client for Micro Mechanic (FFF0 service)
#
# MAC      : 00:1D:A5:00:F9:57
# FFF1 h20 : NOTIFY  — responses from adapter
# FFF2 h23 : WRITE   — AT commands to adapter
# CCCD h21 : write 0x0100 to enable FFF1 notifications

import bluetooth

_TARGET  = bytes([0x00, 0x1D, 0xA5, 0x00, 0xF9, 0x57])
_HDL_RX  = 20
_HDL_TX  = 23
_HDL_CFG = 21

_IRQ_SCAN_RESULT           = 5
_IRQ_PERIPHERAL_CONNECT    = 7
_IRQ_PERIPHERAL_DISCONNECT = 8
_IRQ_GATTC_WRITE_DONE      = 17
_IRQ_GATTC_NOTIFY          = 18

_INIT = ['ATZ', 'ATE0', 'ATL0', 'ATSP0']

_PIDS = [
    '010C',  # RPM
    '010D',  # speed km/h
    '0104',  # engine load %
    '0105',  # coolant temp
    '010E',  # timing advance
    '0106',  # short term fuel trim
    '010F',  # intake air temp
    '0114',  # O2 sensor voltage
    '011F',  # engine runtime
    '0110',  # MAF g/s
    'ATRV',  # battery voltage
]


class OBD:
    def __init__(self):
        self._ble      = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._conn     = None
        self._buf      = b''
        self._state    = 'idle'
        self._init_idx = 0
        self._poll_idx = 0
        self._data     = {}

    def start(self):
        print('OBD: scanning...')
        self._state = 'scan'
        self._ble.gap_scan(0, 30000, 30000)

    @property
    def connected(self):
        return self._state == 'poll'

    def get_data(self):
        d = self._data.copy()
        self._data.clear()
        return d

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if bytes(addr) == _TARGET:
                self._ble.gap_scan(None)
                print('OBD: found, connecting...')
                self._state = 'connect'
                self._ble.gap_connect(addr_type, addr)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            self._conn, _, _ = data
            print('OBD: connected, enabling notify...')
            self._state = 'cccd'
            self._ble.gattc_write(self._conn, _HDL_CFG, b'\x01\x00', 1)

        elif event == _IRQ_GATTC_WRITE_DONE:
            if self._state == 'cccd':
                print('OBD: notify enabled, starting AT init...')
                self._state    = 'init'
                self._init_idx = 0
                self._buf      = b''
                self._send(_INIT[0])

        elif event == _IRQ_GATTC_NOTIFY:
            _, handle, payload = data
            if handle == _HDL_RX:
                self._buf += bytes(payload)
                self._process()

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            print('OBD: disconnected')
            self._conn  = None
            self._buf   = b''
            self._state = 'idle'

    def _send(self, cmd):
        self._ble.gattc_write(self._conn, _HDL_TX, (cmd + '\r').encode(), 0)

    def _process(self):
        while b'>' in self._buf:
            resp, _, self._buf = self._buf.partition(b'>')
            resp = resp.strip()
            if not resp:
                continue
            text = resp.decode('utf-8', 'ignore').strip()

            if self._state == 'init':
                print('OBD init rx:', repr(text))
                self._init_idx += 1
                if self._init_idx < len(_INIT):
                    self._send(_INIT[self._init_idx])
                else:
                    print('OBD: ready')
                    self._state    = 'poll'
                    self._poll_idx = 0
                    self._send(_PIDS[0])

            elif self._state == 'poll':
                self._parse(text)
                self._poll_idx = (self._poll_idx + 1) % len(_PIDS)
                self._send(_PIDS[self._poll_idx])

    def _parse(self, text):
        # Standard OBD: "41 0C 1A F8"
        parts = text.split()
        if len(parts) >= 3 and parts[0] == '41':
            pid = parts[1].upper()
            try:
                if   pid == '0C' and len(parts) >= 4:
                    self._data['rpm']     = str((int(parts[2],16)*256 + int(parts[3],16)) // 4)
                elif pid == '0D':
                    self._data['speed_raw'] = int(parts[2], 16)  # km/h, corrected in main
                elif pid == '04':
                    self._data['load']    = str(round(int(parts[2],16) * 100 / 255))
                elif pid == '05':
                    self._data['coolant'] = str(int(parts[2],16) - 40)
                elif pid == '0E':
                    self._data['timing']  = str(round(int(parts[2],16) / 2 - 64, 1))
                elif pid == '06':
                    self._data['fuel_trim'] = round((int(parts[2],16) - 128) * 100 / 128, 1)
                elif pid == '0F':
                    self._data['iat']     = str(int(parts[2],16) - 40)
                elif pid == '14':
                    self._data['o2']      = str(round(int(parts[2],16) * 0.005, 3))
                elif pid == '1F' and len(parts) >= 4:
                    secs = int(parts[2],16)*256 + int(parts[3],16)
                    self._data['runtime'] = str(round(secs / 60, 1))
                elif pid == '10' and len(parts) >= 4:
                    self._data['maf']     = str(round((int(parts[2],16)*256 + int(parts[3],16)) / 100, 1))
            except Exception as e:
                print('OBD parse err:', e, repr(text))
            return

        # ATRV: "12.4V" or "12.4"
        v = text.rstrip('V').strip()
        try:
            float(v)
            self._data['battery'] = v
        except:
            pass
