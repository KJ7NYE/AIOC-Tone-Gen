import sys


class VolumeManager:
    def __init__(self, name_substring):
        self._name_substring = name_substring
        self._interface = None
        self._original_scalar = None
        self._friendly_name = None
        if sys.platform == "win32":
            self._init_windows()

    def _init_windows(self):
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        except ImportError:
            return

        needle = self._name_substring.lower()
        for dev in AudioUtilities.GetAllDevices():
            name = getattr(dev, "FriendlyName", None) or ""
            if needle in name.lower():
                try:
                    raw = dev._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self._interface = cast(raw, POINTER(IAudioEndpointVolume))
                    self._original_scalar = self._interface.GetMasterVolumeLevelScalar()
                    self._friendly_name = name
                except Exception:
                    self._interface = None
                    self._original_scalar = None
                return

    def found(self):
        return self._interface is not None

    def friendly_name(self):
        return self._friendly_name

    def get_level_percent(self):
        if self._interface is None:
            return None
        return self._interface.GetMasterVolumeLevelScalar() * 100.0

    def set_level_percent(self, percent):
        if self._interface is None:
            return
        scalar = max(0.0, min(1.0, float(percent) / 100.0))
        self._interface.SetMasterVolumeLevelScalar(scalar, None)

    def restore(self):
        if self._interface is None or self._original_scalar is None:
            return
        try:
            self._interface.SetMasterVolumeLevelScalar(self._original_scalar, None)
        except Exception:
            pass
