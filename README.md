# aioc-tone-gen

A lightweight desktop utility for ham radio operators using the [All-In-One-Cable (AIOC)](https://github.com/skuep/AIOC) interface. Generates a stable, calibrated sine wave tone through the AIOC's USB audio output while automatically keying PTT via the AIOC's virtual COM port.

Intended as a **portable RF audio source** for adjusting receive levels on repeaters, AllStar nodes, EchoLink nodes, and other linked radio systems — without needing a second operator or a dedicated signal generator. Also useful for initial deviation setup using the Bessel null method.

---

## Features

- Stable sine wave tone output through AIOC USB audio — usable as a portable RF signal source
- Adjustable tone frequency from 100 Hz to 3000 Hz
- Calibrated output level control with automatic Windows audio normalization
- One-click PTT key/unkey via AIOC serial port (RTS/DTR)
- Auto-detection of AIOC audio device and COM port
- Clean tone start/stop with no audio pops or artifacts
- Warns if Windows device volume is not at 100% and offers to normalize it
- Defaults to 1200 Hz for Bessel null deviation setup

---

## Requirements

- Windows 10 or 11
- [AIOC hardware](https://github.com/skuep/AIOC) connected via USB
- Python 3.10 or newer

> **Linux/Mac support is planned for a future release.**

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/KJYNY/aioc-tone-gen.git
cd aioc-tone-gen
```

**2. Install dependencies**

```bash
pip install numpy sounddevice pyserial pycaw
```

> `tkinter` is included with standard Python on Windows. No separate install needed.

**3. Run the application**

```bash
python main.py
```

---

## Usage

1. Connect your AIOC to a USB port
2. Launch the application
3. Select your AIOC audio device from the **Audio Device** dropdown
4. Select the AIOC COM port from the **COM Port** dropdown
5. Adjust the **Frequency** slider to your desired tone (Hz)
6. Adjust the **Volume** slider to your desired output level
7. Click **Start Tone** — PTT will key automatically
8. Click **Stop Tone** to end transmission and release PTT

---

## Use Cases

### Adjusting Repeater or Node Audio Levels

Repeaters, AllStar nodes, EchoLink nodes, and similar systems all have receive audio level controls that need to match the network's expected input level. This tool gives you a stable, known-deviation RF source to tune against — without needing a second operator or dedicated signal generator.

The process is two steps, in order:

---

#### Step 1 — Calibrate Your Source Radio (Bessel Null Method)

Before you can use your radio as a reference source, you need to know its deviation is correct. 1200 Hz is the default tone frequency for this reason — it is the standard reference for the Bessel null method.

**What you need:** An SDR receiver (RTL-SDR, etc.) and a spectrum display such as SDR# or GQRX.

1. Launch the app — frequency will default to **1200 Hz**
2. Click **Start Tone** to key the radio
3. Watch the carrier and sidebands on your SDR spectrum display
4. Slowly increase the radio's **mic gain**
5. At approximately **2.886 kHz deviation**, the carrier (center frequency) will null out — it disappears into the noise floor
6. Stop there — your source radio is now transmitting at a known, repeatable deviation of ~2.886 kHz
7. Click **Stop Tone**

> This works because FM modulation theory (Bessel functions) predicts the carrier nulls at a modulation index of 2.4048. At 1200 Hz tone frequency, that null occurs at 2.4048 × 1200 Hz ≈ 2.89 kHz — close enough to 3 kHz deviation for practical use, and widely accepted as the standard fieldcraft method when a service monitor is not available.

---

#### Step 2 — Adjust RX Audio Level on the Device Being Tuned

With your source radio now transmitting at a known deviation, you have a stable reference signal to tune against.

1. Change frequency to **1000 Hz** (standard audio reference tone for level setting)
2. Point your calibrated source radio at the repeater or node's input frequency
3. Click **Start Tone**
4. On the repeater or node side, observe the receive audio level meter (Asterisk/app_rpt, AllStar, DVSwitch, etc.)
5. Adjust the **RX level control on the device being tuned** until the input meter hits the target level
6. Click **Stop Tone** — the device is now calibrated to a known-deviation reference signal

> Because the source deviation is known and the tone frequency is fixed, the level reading on the node is meaningful and repeatable. You can use the same source radio to match levels across multiple nodes or return to a documented baseline in the future.

---

## Audio Level Architecture

Windows has multiple volume layers between this app and your radio:

```
App Volume Slider (this controls)
        ↓
Windows Volume Mixer (per-app)
        ↓
Windows Device Volume (AIOC output level)
        ↓
AIOC Hardware (no software-addressable gain)
        ↓
Radio Mic Input
```

On launch, the app reads the AIOC's Windows device volume. If it is not at 100%, you will be prompted to normalize it. This ensures your in-app slider is the single source of truth for output level. The original device volume is restored when the app exits.

---

## Dependencies

| Package | Purpose |
|---|---|
| `numpy` | Sine wave generation |
| `sounddevice` | Real-time audio streaming to AIOC device |
| `pyserial` | PTT control via RTS/DTR on AIOC COM port |
| `pycaw` | Windows audio device volume normalization |
| `tkinter` | GUI (included with Python on Windows) |

---

## Project Status

This project is in early development. Core functionality is working. Contributions and bug reports are welcome.

**Planned for future releases:**
- CTCSS/DCS subaudible tone generation for repeater access
- Preset save/load for per-repeater level settings
- Linux and macOS support
- Sweep/chirp tone mode
- AllStar/app_rpt audio level reference presets

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

[MIT](LICENSE)

---

## Acknowledgments

- [AIOC Project](https://github.com/skuep/AIOC) by skuep — the hardware that makes this possible
- The ham radio open source community
