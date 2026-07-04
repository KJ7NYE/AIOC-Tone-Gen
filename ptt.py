import serial
import serial.tools.list_ports

try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False


PTT_CM108 = "CM108 HID"
PTT_RTS = "Serial RTS"
PTT_DTR = "Serial DTR"
PTT_RTS_DTR = "Serial RTS+DTR"
PTT_METHODS = [PTT_CM108, PTT_DTR, PTT_RTS, PTT_RTS_DTR]

AIOC_DEFAULT_VID = 0x1209
AIOC_DEFAULT_PID = 0x7388
AIOC_ALLSTAR_VID = 0x0D8C
AIOC_ALLSTAR_PID = 0x000C

GPIO1 = 0x01
GPIO2 = 0x02
GPIO3 = 0x04
GPIO4 = 0x08


class SerialPTT:
    def __init__(self, port, use_rts=False, use_dtr=False):
        self._port_name = port
        self._use_rts = use_rts
        self._use_dtr = use_dtr
        self._serial = None

    def open(self):
        s = serial.Serial()
        s.port = self._port_name
        s.baudrate = 9600
        s.rtscts = False
        s.dsrdtr = False
        s.open()
        s.rts = False
        s.dtr = False
        self._serial = s

    def key(self):
        if self._serial is None:
            return
        if self._use_rts:
            self._serial.rts = True
        if self._use_dtr:
            self._serial.dtr = True

    def unkey(self):
        if self._serial is None:
            return
        if self._use_rts:
            self._serial.rts = False
        if self._use_dtr:
            self._serial.dtr = False

    def close(self):
        if self._serial is None:
            return
        try:
            self.unkey()
        except Exception:
            pass
        try:
            self._serial.close()
        finally:
            self._serial = None


class Cm108HidPTT:
    def __init__(self, hid_path, pin_mask):
        self._path = hid_path
        self._mask = pin_mask & 0x0F
        self._device = None

    def open(self):
        if not HID_AVAILABLE:
            raise RuntimeError("hidapi is not installed (pip install hidapi)")
        if not self._mask:
            raise RuntimeError("No CM108 GPIO pin selected")
        self._device = hid.device()
        self._device.open_path(self._path)

    def key(self):
        if self._device is not None:
            self._write(True)

    def unkey(self):
        if self._device is not None:
            self._write(False)

    def _write(self, on):
        data = self._mask if on else 0x00
        report = bytes([0, 0, 0, data, self._mask])
        self._device.write(report)

    def close(self):
        if self._device is None:
            return
        try:
            self._write(False)
        except Exception:
            pass
        try:
            self._device.close()
        finally:
            self._device = None


def make_ptt(method, com_port=None, hid_path=None, pin_mask=0):
    if method == PTT_CM108:
        if hid_path is None:
            raise ValueError("CM108 HID PTT requires a HID device")
        return Cm108HidPTT(hid_path, pin_mask)
    if not com_port:
        raise ValueError("Serial PTT requires a COM port")
    if method == PTT_RTS:
        return SerialPTT(com_port, use_rts=True)
    if method == PTT_DTR:
        return SerialPTT(com_port, use_dtr=True)
    if method == PTT_RTS_DTR:
        return SerialPTT(com_port, use_rts=True, use_dtr=True)
    raise ValueError(f"Unknown PTT method: {method}")


def list_serial_ports():
    return [(p.device, p.description) for p in serial.tools.list_ports.comports()]


def list_hid_devices():
    if not HID_AVAILABLE:
        return []
    seen = set()
    result = []
    for d in hid.enumerate():
        path = d.get("path")
        if path in seen:
            continue
        seen.add(path)
        vid = int(d.get("vendor_id") or 0)
        pid = int(d.get("product_id") or 0)
        product = (d.get("product_string") or "").strip()
        manuf = (d.get("manufacturer_string") or "").strip()
        parts = [p for p in (manuf, product) if p]
        if not parts:
            parts.append("HID device")
        label = f"{' '.join(parts)} [{vid:04x}:{pid:04x}]"
        result.append({"label": label, "path": path, "vid": vid, "pid": pid})
    return result


def is_aioc_hid(entry):
    vid, pid = entry["vid"], entry["pid"]
    return (vid, pid) in (
        (AIOC_DEFAULT_VID, AIOC_DEFAULT_PID),
        (AIOC_ALLSTAR_VID, AIOC_ALLSTAR_PID),
    )


def default_pin_for_hid(entry):
    if entry is None:
        return GPIO3
    vid, pid = entry["vid"], entry["pid"]
    if (vid, pid) == (AIOC_ALLSTAR_VID, AIOC_ALLSTAR_PID):
        return GPIO1
    return GPIO3
