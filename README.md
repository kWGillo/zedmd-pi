# zedmd-pi

**A ZeDMD-compatible DMD for LED panels that ZeDMD cannot drive.**

`zedmd-pi` turns a Raspberry Pi into a network DMD display. It speaks the
ZeDMD-WiFi protocol, so Batocera, `dmdserver`, dmd-extensions and Visual
Pinball talk to it believing it is a real ZeDMD device — but the panel is
driven by the Pi itself, which means **S-PWM panels work**.

When the DMD is idle it becomes a clock and a media player.

---

## Why this exists

ZeDMD runs on an ESP32 and uses
[ESP32-HUB75-MatrixPanel-DMA](https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA),
which supports "dumb" HUB75 panels: shift registers plus a handful of address
lines. It explicitly does **not** support S-PWM driver chips — panels with an
internal framebuffer that generate their own PWM, such as FM6373, FM6353,
SM16380, ICN2053, MBI5153.

Those chips are increasingly what you actually receive when you order a P2.5
panel, and sellers rarely declare the driver IC. A panel that looks identical
on the listing can be either perfectly supported or completely dead on arrival,
and you only find out after wiring it up.

There is exactly one piece of software that drives S-PWM panels today:
[kingdo9/rpi-rgb-led-matrix_pwm_experiment](https://github.com/kingdo9/rpi-rgb-led-matrix_pwm_experiment),
a Raspberry Pi fork of hzeller's library. `zedmd-pi` puts that fork behind the
ZeDMD network protocol, so an S-PWM panel can finally be used as a virtual
pinball DMD.

Developed and tested with two 128×64 P2.5 panels (FM6373 driver, DP32020B row
driver, A/B/C address lines only) chained to 256×64.

---

## Features

- **ZeDMD-WiFi receiver** — full protocol implementation: HTTP handshake,
  TCP and UDP frame streams, zone streaming, deflate compression, RGB565 and
  RGB888, brightness and clear-screen commands.
- **Clock** — independent colours for time and date, 12/24-hour format,
  weekday names in Italian, French or English.
- **Media player** — random photos and videos from a library folder, shown at
  random intervals. Works with Pixelcade artwork, with or without Batocera.
  Files arrive over SMB or through the web interface; ffmpeg does the
  conversion, so most formats work without preparation.
- **Air radar** — aircraft passing within a radius of a GPS position, from the
  community ADS-B APIs (adsb.fi, adsb.one, adsb.lol — free, no key). Selectable
  flight fields, origin/destination lookup, and a downloadable CSV log of every
  pass.
- **Night mode / Sleep mode** — scheduled dimming and scheduled blackout.
- **Over-the-air updates** — checks this repository, verifies the archive
  before installing, and rolls back automatically if the service does not come
  back up.
- **Web interface** — brightness, NTP, timezone, DST, S-PWM fine tuning,
  services, media upload, radar configuration, updates. Available in **English
  and Italian**: the language is picked from the browser's `Accept-Language` on
  first visit and can be switched from any page. The weekday names shown on the
  panel are a separate setting, since whoever looks at the cabinet is not
  necessarily whoever configures it.
- **Single owner of the panel** — one process, several content sources, one
  arbiter with pre-emption and a grace period.

No GPS coordinates ship with this repository: the radar starts at 0/0 and does
nothing until a position is entered locally. Your location stays in
`/etc/dmd/config.json` on your own machine.

---

## Hardware

| Component | Notes |
|---|---|
| Raspberry Pi | Zero W, Zero 2 W, 3 or 4. **Raspberry Pi only** — the matrix library writes directly to Broadcom/RP1 registers, so Orange Pi and similar boards cannot work. |
| HUB75 panels | Any resolution the fork can drive. S-PWM panels need a matching register profile. |
| Power | Separate 5 V supply for the panels. **Grounds must be common** with the Pi. |

### Wiring (hzeller "regular" mapping)

| Panel | GPIO (BCM) | Physical pin |
|---|---|---|
| R1 | 11 | 23 |
| G1 | 27 | 13 |
| B1 | 7 | 26 |
| R2 | 8 | 24 |
| G2 | 9 | 21 |
| B2 | 10 | 19 |
| A | 22 | 15 |
| B | 23 | 16 |
| C | 24 | 18 |
| CLK | 17 | 11 |
| LAT | 4 | 7 |
| OE | 18 | 12 |
| GND | — | 6 and 14 |

D and E are left unconnected on panels that mark them NC.

---

## Installation

Prepare the Pi first: disable onboard audio (it shares the PWM peripheral the
panel needs), isolate a CPU core on quad-core models, then build the matrix
library.

```bash
sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' /boot/firmware/config.txt
echo "blacklist snd_bcm2835" | sudo tee /etc/modprobe.d/blacklist-audio.conf
sudo sed -i '1s/$/ isolcpus=3/' /boot/firmware/cmdline.txt   # skip on Pi Zero W
sudo reboot
```

```bash
sudo apt install -y git build-essential
git clone https://github.com/kingdo9/rpi-rgb-led-matrix_pwm_experiment.git
cd rpi-rgb-led-matrix_pwm_experiment && make && cd examples-api-use && make
```

Then install `zedmd-pi`:

```bash
git clone https://github.com/kWGillo/zedmd-pi.git ~/dmd
cd ~/dmd
chmod +x install.sh update.sh setup_share.sh
sudo ./install.sh
```

Review `/etc/dmd/config.json` — at minimum `panel.slowdown` (1 for Pi Zero W,
3 for Zero 2 W and Pi 3, 5 for Pi 4) and `panel.chain` — then:

```bash
sudo systemctl start dmd
journalctl -u dmd -f
```

The web interface is on port **8080**. Port 80 redirects to it.

### Updating

From the web interface: the *Settings* page compares the installed version
with the one published here and offers a button when a newer one exists. The
update downloads the branch archive, checks that every expected file is present
and that all Python compiles, backs up the current installation, swaps the
files, restarts the service, and then polls `/api/status`. If the service does
not answer, the backup is restored automatically. The installer runs detached
so it survives the restart of the service that launched it.

From the command line:

```bash
cd ~/dmd && git pull && sudo ./update.sh
```

Either way, restart Batocera afterwards.

### Finding the right panel profile

S-PWM panels need a register profile that matches the specific panel. The fork
ships a catalogue and an interactive browser:

```bash
sudo SPWM_PROFILE_DIR=<repo>/lib/spwm/registertest/data \
  <repo>/examples-api-use/demo -D15 --led-no-drop-privs \
  --led-rows=64 --led-cols=128 --led-chain=1 --led-panel-type=fm6373 \
  --led-spwm-row-addr-type=1 --led-spwm-scan=64 --led-slowdown-gpio=3
```

Arrow keys cycle profiles. Put the working number in `panel.spwm_register_config`.
Power-cycle the panel between attempts: S-PWM chips keep configuration in
internal registers and a bad profile can leave them stuck.

---

## Connecting Batocera

Batocera drives real DMDs through `dmdserver` (libdmdutil). There is no field
in the UI for a network address — it lives in a config file:

```bash
cat > /userdata/system/configs/dmdserver/config.ini << 'EOF'
[DMDServer]
AltColor = 1

[ZeDMD]
Enabled = 0

[ZeDMD-WiFi]
Enabled = 1
WiFiAddr = 192.168.0.XXX
EOF
```

Then enable the **DMD reale** service. Restart Batocera after any update of
`zedmd-pi`: the client caches connection state and per-zone bookkeeping.

---

## The ZeDMD-WiFi protocol

Reconstructed from the [libzedmd](https://github.com/PPUC/libzedmd) source.
Documented here because it does not appear to be written down anywhere else.

**Discovery — HTTP, port 80 (hardcoded in the client)**

`GET /handshake` returns 22 pipe-separated fields:

```
width|height|firmware|s3|protocol|port|udpDelay|writeAtOnce|brightness|rgbMode|
clkphase|driver|i2sspeed|latchBlanking|minRefresh|yOffset|ssid|half|id|power|
deviceType|lineDecoder
```

Single-value endpoints exist as a fallback: `/get_width`, `/get_height`,
`/get_version`, `/get_s3`, `/get_protocol`, `/get_port`, `/get_udp_delay`.

> **Implementation note.** The client reads the HTTP response with a single
> `recv()` and stops as soon as it gets fewer than 1024 bytes. A server that
> writes headers and body separately — as most WSGI servers do — will be read
> as headers only: the client sees an empty body, parses every field as zero,
> fails to detect the TCP transport and silently falls back to UDP. This is why
> the handshake here is served by a dedicated socket server that emits the whole
> response in one `sendall()`, while the web UI lives on another port.

**Frames — TCP or UDP, port 3333**

```
b"FRAME" + [ b"ZeDMD" + cmd(1) + size_hi(1) + size_lo(1) + compressed(1) + data ]*
```

Compressed payloads are deflate. Commands:

| Code | Meaning |
|---|---|
| `0x04` / `0x05` | RGB888 / RGB565 zone stream |
| `0x06` | render frame |
| `0x07` / `0x08` | RGB888 / RGB565 full frame |
| `0x0a` | clear screen |
| `0x0b` | keep-alive |
| `0x16` | brightness (0–15) |

Zone streams use a fixed 16×8 grid of 128 zones; zone width is `width/16` and
zone height is `height/8`. Each zone is preceded by its index; an index ≥ 128
means "zone index−128 is entirely black" with no pixel data following. Only
changed zones are transmitted.

Advertising `TCP` in the handshake avoids UDP fragmentation entirely — the
client's own comments note that rapid UDP bursts crash real ESP32 hardware.

---

## Architecture

Only one process can drive the GPIO, so every content source lives in one
service and an arbiter decides who owns the display.

| Priority | Source |
|---|---|
| 100 | ZeDMD |
| 60 | Air radar |
| 50 | Media player |
| 10 | Clock |

ZeDMD pre-empts immediately on connection or incoming frame and holds the
display for `grace_seconds` after the last signal — without that hysteresis the
clock would flash in during Batocera's menu pauses. An abrupt power-off leaves
the TCP connection open, so an application-level timeout treats prolonged
silence as a dead client.

Sleep mode overrides everything; night mode only changes brightness.

```
dmdd.py        main service, arbiter, render loop
display.py     exclusive owner of the panel
zedmd_http.py  ZeDMD handshake server (port 80)
webui.py       Flask web interface (port 8080)
ota.py         over-the-air update from this repository
i18n.py        English/Italian strings for the web interface
sources/       zedmd.py, airradar.py, media.py, clock.py
```

Adding a language means adding a column to the tuples in `i18n.py` and a code
to `LANGUAGES` — there are no `.po` files to compile and no build step.

Adding a service means writing a new source in `sources/`, registering it in
`Runtime`, and adding an entry to the services page.

---

## Timing, or: why white lines appear

The matrix library generates the panel signal in software, timing GPIO
transitions to the microsecond. Anything that preempts the process — another
program, disk I/O, network traffic — stretches one row's on-time, and that row
shows up brighter. **Horizontal white lines are a load indicator, not a panel
fault.**

This has practical consequences for the rest of the system:

- Keep `isolcpus=3` and `dtparam=audio=off`. They are not optional.
- Lower `panel.pwm_bits` before lowering anything else: 8 bits instead of 11
  cuts the work substantially and the difference is hard to see on a DMD.
- Avoid repeated filesystem walks. A full Pixelcade collection is tens of
  thousands of files; since 1.6 the library listing is cached rather than
  re-read on every content change and every status request, because that scan
  alone was enough to produce visible lines.
- Prefer a USB stick over the SD card for the media library, and stop the
  service before bulk-copying into it.

If instead you see `Bus error` or `Input/output error` on system binaries, that
is not a timing problem — the machine has lost the ability to read its own
executables. Check `vcgencmd get_throttled` for undervoltage (panels and Pi on
one supply is the usual cause) and `dmesg` for `mmc`/`ext4` errors before
blaming the CPU.

---

## Credits

- [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) — the LED matrix library
- [kingdo9/rpi-rgb-led-matrix_pwm_experiment](https://github.com/kingdo9/rpi-rgb-led-matrix_pwm_experiment) — S-PWM panel support, without which none of this would be possible
- [PPUC/ZeDMD](https://github.com/PPUC/ZeDMD) and [PPUC/libzedmd](https://github.com/PPUC/libzedmd) — the protocol
- [vpinball/libdmdutil](https://github.com/vpinball/libdmdutil) — `dmdserver`, the Batocera side

## Documentation in Italian

- [`docs/README.it.md`](docs/README.it.md) — service documentation
- [`docs/installazione.it.md`](docs/installazione.it.md) — installation manual
- [`docs/hardware-setup.it.md`](docs/hardware-setup.it.md) — panel wiring and tuning

## License

GPLv3 — see [LICENSE](LICENSE).
