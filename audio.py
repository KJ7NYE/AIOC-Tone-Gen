import time
import threading
import numpy as np
import sounddevice as sd


class ToneGenerator:
    def __init__(self, blocksize=1024):
        self.blocksize = blocksize
        self.samplerate = 48000
        self._stream = None
        self._phase = 0.0
        self._target_freq = 1200.0
        self._target_gain = 0.5
        self._current_gain = 0.0
        self._stop_requested = False
        self._stopped_event = threading.Event()

    def set_frequency(self, freq_hz):
        self._target_freq = float(freq_hz)

    def set_volume(self, volume_percent):
        self._target_gain = max(0.0, min(1.0, float(volume_percent) / 100.0))

    def is_running(self):
        return self._stream is not None and self._stream.active

    def start(self, device_index, frequency_hz, volume_percent):
        if self.is_running():
            return
        self.set_frequency(frequency_hz)
        self.set_volume(volume_percent)

        info = sd.query_devices(device_index)
        self.samplerate = int(info["default_samplerate"]) or 48000

        self._phase = 0.0
        self._current_gain = 0.0
        self._stop_requested = False
        self._stopped_event.clear()

        self._stream = sd.OutputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            channels=1,
            dtype="float32",
            device=device_index,
            callback=self._callback,
            finished_callback=self._on_finished,
        )
        self._stream.start()

    def stop(self):
        self._stop_requested = True

    def wait_stopped(self, timeout=2.0):
        if self._stream is None:
            return
        self._stopped_event.wait(timeout)
        try:
            self._stream.close(ignore_errors=True)
        finally:
            self._stream = None

    def _on_finished(self):
        self._stopped_event.set()

    def _callback(self, outdata, frames, time_info, status):
        freq = self._target_freq
        target = 0.0 if self._stop_requested else self._target_gain
        sr = self.samplerate

        phase_inc = 2.0 * np.pi * freq / sr
        idx = np.arange(1, frames + 1, dtype=np.float64)
        phases = self._phase + idx * phase_inc
        self._phase = float(phases[-1] % (2.0 * np.pi))
        tone = np.sin(phases).astype(np.float32)

        gain_ramp = np.linspace(self._current_gain, target, frames, dtype=np.float32)
        self._current_gain = target

        outdata[:, 0] = tone * gain_ramp

        if self._stop_requested and self._current_gain == 0.0:
            raise sd.CallbackStop


def list_output_devices():
    devices = sd.query_devices()
    outputs = []
    for i, d in enumerate(devices):
        if d.get("max_output_channels", 0) > 0:
            outputs.append((i, d["name"]))
    return outputs
