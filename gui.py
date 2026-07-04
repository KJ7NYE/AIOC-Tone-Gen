import threading
import tkinter as tk
from tkinter import ttk, messagebox

from audio import ToneGenerator, list_output_devices
from ptt import (
    make_ptt,
    list_serial_ports,
    list_hid_devices,
    is_aioc_hid,
    default_pin_for_hid,
    PTT_METHODS,
    PTT_CM108,
    PTT_DTR,
    GPIO1,
    GPIO2,
    GPIO3,
    GPIO4,
)
from volume import VolumeManager

AIOC_AUDIO_NAME = "AIOC Audio"


class ToneGenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AIOC Tone Generator")
        self.root.resizable(False, False)

        self.tone = ToneGenerator()
        self.ptt = None
        self.volume = VolumeManager(AIOC_AUDIO_NAME)

        self._transmitting = False
        self._audio_map = {}
        self._com_map = {}
        self._hid_map = {}

        self._build_ui()
        self._populate_devices()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(200, self._check_windows_volume)

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        row = 0
        ref = ttk.LabelFrame(frm, text="Bessel Null Peak Deviation", padding=(8, 4))
        ref.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        mono = ("Consolas", 9)
        ttk.Label(ref, text="1st null (β=2.4048):", font=mono).grid(row=0, column=0, sticky="w")
        ttk.Label(ref, text="1000 Hz → 2.405 kHz", font=mono).grid(row=0, column=1, sticky="w", padx=(12, 12))
        ttk.Label(ref, text="1200 Hz → 2.886 kHz", font=mono).grid(row=0, column=2, sticky="w")
        ttk.Label(ref, text="2nd null (β=5.5201):", font=mono).grid(row=1, column=0, sticky="w")
        ttk.Label(ref, text="1000 Hz → 5.520 kHz", font=mono).grid(row=1, column=1, sticky="w", padx=(12, 12))
        ttk.Label(ref, text="1200 Hz → 6.624 kHz", font=mono).grid(row=1, column=2, sticky="w")

        row += 1
        ttk.Label(frm, text="Audio Device:").grid(row=row, column=0, sticky="w", pady=4)
        self.audio_var = tk.StringVar()
        self.audio_combo = ttk.Combobox(
            frm, textvariable=self.audio_var, state="readonly", width=46
        )
        self.audio_combo.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)

        row += 1
        ttk.Label(frm, text="PTT Method:").grid(row=row, column=0, sticky="w", pady=4)
        self.method_var = tk.StringVar(value=PTT_DTR)
        self.method_combo = ttk.Combobox(
            frm, textvariable=self.method_var, state="readonly",
            values=PTT_METHODS, width=20,
        )
        self.method_combo.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=4)
        self.method_combo.bind("<<ComboboxSelected>>", self._on_method_change)

        row += 1
        ttk.Label(frm, text="HID Device:").grid(row=row, column=0, sticky="w", pady=4)
        self.hid_var = tk.StringVar()
        self.hid_combo = ttk.Combobox(
            frm, textvariable=self.hid_var, state="readonly", width=46
        )
        self.hid_combo.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)
        self.hid_combo.bind("<<ComboboxSelected>>", self._on_hid_change)

        row += 1
        ttk.Label(frm, text="CM108 Pins:").grid(row=row, column=0, sticky="w", pady=4)
        pinfrm = ttk.Frame(frm)
        pinfrm.grid(row=row, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=4)
        self.pin_vars = {
            GPIO1: tk.BooleanVar(value=False),
            GPIO2: tk.BooleanVar(value=False),
            GPIO3: tk.BooleanVar(value=False),
            GPIO4: tk.BooleanVar(value=False),
        }
        self.pin_checks = {}
        for i, (mask, label) in enumerate([
            (GPIO1, "GPIO1"), (GPIO2, "GPIO2"),
            (GPIO3, "GPIO3"), (GPIO4, "GPIO4"),
        ]):
            cb = ttk.Checkbutton(pinfrm, text=label, variable=self.pin_vars[mask])
            cb.grid(row=0, column=i, padx=(0, 10))
            self.pin_checks[mask] = cb

        row += 1
        ttk.Label(frm, text="COM Port:").grid(row=row, column=0, sticky="w", pady=4)
        self.com_var = tk.StringVar()
        self.com_combo = ttk.Combobox(
            frm, textvariable=self.com_var, state="readonly", width=46
        )
        self.com_combo.grid(row=row, column=1, columnspan=3, sticky="ew", padx=(8, 0), pady=4)

        row += 1
        ttk.Label(frm, text="Frequency:").grid(row=row, column=0, sticky="w", pady=(12, 4))
        self.freq_var = tk.IntVar(value=1200)
        self.freq_entry_var = tk.StringVar(value="1200")
        freq_box = ttk.Frame(frm)
        freq_box.grid(row=row, column=3, sticky="e", pady=(12, 4))
        self.freq_entry = ttk.Entry(
            freq_box, textvariable=self.freq_entry_var, width=6, justify="right"
        )
        self.freq_entry.pack(side="left")
        ttk.Label(freq_box, text=" Hz").pack(side="left")
        self.freq_entry.bind("<Return>", self._on_freq_entry_commit)
        self.freq_entry.bind("<FocusOut>", self._on_freq_entry_commit)
        self.freq_scale = ttk.Scale(
            frm, from_=100, to=3000, orient="horizontal",
            command=self._on_freq_change, length=300,
        )
        self.freq_scale.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(12, 4))
        self.freq_scale.set(1200)

        row += 1
        ttk.Label(frm, text="Volume:").grid(row=row, column=0, sticky="w", pady=4)
        self.vol_var = tk.IntVar(value=50)
        self.vol_entry_var = tk.StringVar(value="50")
        vol_box = ttk.Frame(frm)
        vol_box.grid(row=row, column=3, sticky="e", pady=4)
        self.vol_entry = ttk.Entry(
            vol_box, textvariable=self.vol_entry_var, width=6, justify="right"
        )
        self.vol_entry.pack(side="left")
        ttk.Label(vol_box, text=" %").pack(side="left")
        self.vol_entry.bind("<Return>", self._on_vol_entry_commit)
        self.vol_entry.bind("<FocusOut>", self._on_vol_entry_commit)
        self.vol_scale = ttk.Scale(
            frm, from_=0, to=100, orient="horizontal",
            command=self._on_vol_change, length=300,
        )
        self.vol_scale.grid(row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        self.vol_scale.set(50)

        row += 1
        self.toggle_btn = ttk.Button(frm, text="Start Tone", command=self._toggle)
        self.toggle_btn.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(16, 6))

        row += 1
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(frm, textvariable=self.status_var, anchor="center", foreground="#555")
        status.grid(row=row, column=0, columnspan=4, sticky="ew")

    def _populate_devices(self):
        outputs = list_output_devices()
        display = [f"[{idx}] {name}" for idx, name in outputs]
        self._audio_map = {label: idx for label, (idx, _) in zip(display, outputs)}
        self.audio_combo["values"] = display
        default = next(
            (label for label in display if AIOC_AUDIO_NAME.lower() in label.lower()),
            None,
        )
        if default:
            self.audio_var.set(default)
        elif display:
            self.audio_var.set(display[0])

        hid_entries = list_hid_devices()
        hid_labels = [e["label"] for e in hid_entries]
        self._hid_map = {e["label"]: e for e in hid_entries}
        self.hid_combo["values"] = hid_labels
        aioc_hid = next((e for e in hid_entries if is_aioc_hid(e)), None)
        if aioc_hid:
            self.hid_var.set(aioc_hid["label"])
        elif hid_labels:
            self.hid_var.set(hid_labels[0])
        self._apply_default_pins()

        ports = list_serial_ports()
        port_display = [f"{dev} - {desc}" for dev, desc in ports]
        self._com_map = {label: dev for label, (dev, _) in zip(port_display, ports)}
        self.com_combo["values"] = port_display
        if port_display:
            self.com_var.set(port_display[0])

        self._update_enabled_state()

    def _apply_default_pins(self):
        for var in self.pin_vars.values():
            var.set(False)
        entry = self._hid_map.get(self.hid_var.get())
        mask = default_pin_for_hid(entry)
        for bit, var in self.pin_vars.items():
            if bit & mask:
                var.set(True)

    def _on_method_change(self, _event=None):
        self._update_enabled_state()

    def _on_hid_change(self, _event=None):
        self._apply_default_pins()

    def _update_enabled_state(self):
        method = self.method_var.get()
        cm108 = method == PTT_CM108
        hid_state = "readonly" if cm108 else "disabled"
        com_state = "disabled" if cm108 else "readonly"
        pin_state = "normal" if cm108 else "disabled"
        self.hid_combo.config(state=hid_state)
        self.com_combo.config(state=com_state)
        for cb in self.pin_checks.values():
            cb.config(state=pin_state)

    def _check_windows_volume(self):
        if not self.volume.found():
            return
        level = self.volume.get_level_percent()
        if level is None or level >= 99.5:
            return
        answer = messagebox.askyesno(
            "AIOC Windows Volume",
            f"AIOC Windows output volume is at {level:.0f}%.\n\n"
            "Set it to 100% for consistent tone level?\n"
            "The original level will be restored on exit.",
        )
        if answer:
            self.volume.set_level_percent(100.0)

    def _on_freq_change(self, val):
        f = int(float(val))
        self.freq_var.set(f)
        if self.freq_entry.focus_get() is not self.freq_entry:
            self.freq_entry_var.set(str(f))
        self.tone.set_frequency(f)

    def _on_vol_change(self, val):
        v = int(float(val))
        self.vol_var.set(v)
        if self.vol_entry.focus_get() is not self.vol_entry:
            self.vol_entry_var.set(str(v))
        self.tone.set_volume(v)

    def _on_freq_entry_commit(self, _event=None):
        try:
            f = int(float(self.freq_entry_var.get()))
        except ValueError:
            self.freq_entry_var.set(str(self.freq_var.get()))
            return
        f = max(100, min(3000, f))
        self.freq_entry_var.set(str(f))
        self.freq_scale.set(f)

    def _on_vol_entry_commit(self, _event=None):
        try:
            v = int(float(self.vol_entry_var.get()))
        except ValueError:
            self.vol_entry_var.set(str(self.vol_var.get()))
            return
        v = max(0, min(100, v))
        self.vol_entry_var.set(str(v))
        self.vol_scale.set(v)

    def _toggle(self):
        if self._transmitting:
            self._stop()
        else:
            self._start()

    def _selected_pin_mask(self):
        mask = 0
        for bit, var in self.pin_vars.items():
            if var.get():
                mask |= bit
        return mask

    def _start(self):
        audio_label = self.audio_var.get()
        if audio_label not in self._audio_map:
            messagebox.showerror("Audio", "Select an audio device.")
            return

        method = self.method_var.get()
        try:
            if method == PTT_CM108:
                hid_label = self.hid_var.get()
                if hid_label not in self._hid_map:
                    messagebox.showerror("PTT", "Select a HID device.")
                    return
                pin_mask = self._selected_pin_mask()
                if not pin_mask:
                    messagebox.showerror("PTT", "Select at least one CM108 GPIO pin.")
                    return
                self.ptt = make_ptt(method, hid_path=self._hid_map[hid_label]["path"], pin_mask=pin_mask)
            else:
                com_label = self.com_var.get()
                if com_label not in self._com_map:
                    messagebox.showerror("PTT", "Select a COM port.")
                    return
                self.ptt = make_ptt(method, com_port=self._com_map[com_label])
            self.ptt.open()
            self.ptt.key()
        except Exception as e:
            messagebox.showerror("PTT Error", f"Could not key PTT:\n{e}")
            self._safe_close_ptt()
            return

        device_index = self._audio_map[audio_label]
        try:
            self.tone.start(device_index, self.freq_var.get(), self.vol_var.get())
        except Exception as e:
            self._safe_close_ptt()
            messagebox.showerror("Audio Error", f"Could not start audio:\n{e}")
            return

        self._transmitting = True
        self.toggle_btn.config(text="Stop Tone")
        self.status_var.set(f"Transmitting ({method})")

    def _stop(self):
        self.toggle_btn.config(state="disabled")
        self.status_var.set("Stopping...")
        self.tone.stop()
        threading.Thread(target=self._finish_stop, daemon=True).start()

    def _finish_stop(self):
        self.tone.wait_stopped()
        self._safe_close_ptt()
        self.root.after(0, self._after_stop)

    def _safe_close_ptt(self):
        if self.ptt is None:
            return
        try:
            self.ptt.unkey()
        except Exception:
            pass
        try:
            self.ptt.close()
        except Exception:
            pass
        self.ptt = None

    def _after_stop(self):
        self._transmitting = False
        self.toggle_btn.config(text="Start Tone", state="normal")
        self.status_var.set("Stopped")

    def _on_close(self):
        try:
            if self._transmitting:
                self.tone.stop()
                self.tone.wait_stopped()
                self._safe_close_ptt()
        finally:
            self.volume.restore()
            self.root.destroy()
