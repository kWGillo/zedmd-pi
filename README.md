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
- **Rolling banner** — up to ten scrolling texts, each with its own colour,
  size, speed and blinking, appearing at random intervals.
- **Now playing** — title, artist, album and progress of whatever you are
  listening to. The Pi runs `shairport-sync` and appears on the network as an
  AirPlay 2 speaker that throws the audio away and keeps only the metadata, so
  any app on an iPhone, iPad or Mac works — Apple Music, Spotify, Amazon
  Music, YouTube alike. Spotify Connect playing elsewhere is covered through
  Spotify's own API, and anything else through a free MQTT topic. See
  [Now playing](#now-playing).
- **Home Assistant** — the DMD announces itself over MQTT Discovery: current
  track, a switch per service and brightness, all controllable. Entirely
  optional; the default broker is a local Mosquitto.
- **Doom** — yes, really. It runs as a program of its own (doomgeneric, output
  cropped to 256×64) talking to the service over a pipe: frames one way, keys
  the other. The hard part was never the CPU — it is 1993 software — but the
  shape of the screen: Doom draws 1.6:1 and the panel is 4:1, so a **band
  around the horizon** is cropped, where the enemies are, and floor and
  ceiling are thrown away. While nobody touches anything it plays its own
  built-in demos and yields the panel to everything else; at the first command
  a game starts and the panel is its own, Batocera included. Controlled from a
  keyboard plugged into the Pi, or from the web page. See
  [Doom on the panel](#doom-on-the-panel).
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

Then enable the **DMD reale** service — `dmd_real`, from the menu or from the
shell:

```bash
batocera-services enable dmd_real
batocera-services start dmd_real
```

Check that it actually started, because the config file on its own starts
nothing:

```bash
ps aux | grep dmdserver | grep -v grep
```

You must see a `dmdserver` process carrying `-c /userdata/system/...`. If it is
missing, nobody is reading the file you just wrote, and the Pi will keep
listening without ever seeing a client. From the Pi side, `journalctl -u dmd`
tells the two failures apart: a `[zedmd-http] <ip> /handshake` line means the
client reached the Pi, no such line means it never did — typically a stale
`WiFiAddr` after swapping SD card or Pi.

Restart Batocera after any update of `zedmd-pi`: the client caches connection
state and per-zone bookkeeping.

Known EmulationStation behaviour, not a fault: holding the scroll button does
not update the panel, and neither does releasing it. ES opens a fresh
connection to `dmdserver` on every selection change, but opens none during key
auto-repeat. One extra press realigns the panel.

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
| 58 | Now playing |
| 55 | Rolling banner |
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
mqttbus.py     shared MQTT client: metadata in, Home Assistant entities out
nowplaying.py  current-track state, independent of where it came from
spotifyapi.py  Spotify Web API, OAuth with PKCE
hass.py        Home Assistant entities over MQTT Discovery
sources/       zedmd.py, airradar.py, media.py, banner.py, nowplaying.py, clock.py
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

## Doom on the panel

### The shape of the screen

Doom on a Pi is not a performance question. It is software from 1993 and the
Pi decodes it without noticing. The problem is geometry: Doom draws 320×200 —
1.6:1 — and the panel is 256×64 — 4:1. Scale the whole frame down to 64 rows
and an imp is eight pixels tall, indistinguishable from a barrel.

So the frame is not squashed, it is **cropped**. A band is taken around the
horizon and the rest is discarded. In Doom the floor and the ceiling are
exactly where nothing happens, while enemies sit on the line of sight; the
status bar, which starts at row 168, does not fit and is not needed. The band
is scaled 5:4 horizontally (320 → 256) and by whatever it takes vertically,
with a box average — at this size antialiasing is what makes a figure legible,
not a luxury. The defaults are row 36 for 96 rows and gamma 0.70 (Doom is a
dark game and an LED panel has none of a CRT's black); both are tunable from
the Doom page, because the only place that question has a real answer is in
front of the panel.

### Two processes, not a library

`doom/doom-dmd` is doomgeneric compiled with our own output function. It talks
to the DMD service over a pipe: raw fixed-size frames on stdout, `[state, key]`
pairs on stdin. It is a separate process for three reasons, in order of
importance:

1. **Licence.** doomgeneric descends from the Doom sources, which are GPL
   version 2. This project is GPLv3, and GPL2-only inside a GPLv3 work does not
   fit. Two processes talking over a pipe are not linked: they stay two
   programs, each under its own licence.
2. **Isolation.** If Doom falls over, Doom falls over; the panel goes back to
   the clock and the service does not notice.
3. **Simplicity.** No bindings, no GIL to contend for. Read a frame, publish it.

The sources are not vendored here — `doom/setup_doom.sh` fetches and builds
them. The compiled binary lands in `/var/lib/dmd/doom`, not in `/opt/dmd`,
because an OTA update wipes and re-copies the program's subdirectories and a
binary in there would vanish on every update.

### Attract mode, and a game

While nobody touches anything, Doom plays its own built-in demos — that is
what it has always done when left alone, so attract mode costs nothing. There
it is an ordinary source with a low priority: an aircraft, a birthday and
above all Batocera all outrank it.

At the first command a **game** starts and the panel becomes its own, Batocera
included, until you leave or let it sit idle (three minutes by default). The
game begins by restarting Doom straight into the level rather than pressing a
key to abort the demo and then navigating the menu with arrow keys on a panel
sixty-four pixels tall.

Holding the panel is the same mechanism the media manager uses, generalised: a
named hold, either with a deadline (the library page, kept alive by a
heartbeat, so a closed tab releases it) or without one (the game, so standing
still in front of a door does not send the panel back to the clock). One page
cannot release another's hold.

### Controls

No GPIO. On the SM16380SC panels D and E are wired and the pins that would
have been used are gone, so both routes are software:

- **A keyboard plugged into the Pi**, read straight from `/dev/input` with no
  extra library — the events are a 24-byte (or 16-byte, on 32-bit) struct and
  `struct` is always there. Arrows or WASD, ctrl fires, space opens, shift
  runs. This is the direct route: it does not go through the network.
- **The web page**, with on-screen buttons that hold down properly, plus the
  keyboard of whatever computer is looking at the page. Same key queue, only a
  different way in.

### Setting it up

```
sudo /opt/dmd/doom/setup_doom.sh
```

It installs the build tools if missing, clones and compiles doomgeneric
(a couple of minutes on a Pi 3B+), and downloads **Freedoom**, which is freely
licensed. Commercial WADs cannot be redistributed: if you own one, put it
where you like and correct the path on the Doom page. Then turn the Doom
service on from the Services page.

---

## Now playing

The panel shows what you are listening to: title, artist, album, playing or
paused, and how far into the track you are. The DMD plays no audio and never
sits between the music and your speakers — it only listens for the metadata.

### Where the metadata comes from

**AirPlay 2.** `shairport-sync` runs on the Pi and advertises itself as an
AirPlay speaker. The audio goes into the kernel's `snd_dummy` card — which
has a real clock, unlike `/dev/null` or ALSA's `null` plugin, and that
difference is what keeps a multi-room group in sync — while the metadata goes
out over MQTT. The AirPlay receiver does not care which app is playing, so
Apple Music, Spotify, Amazon Music and YouTube all work with nothing to
configure per app.

**Spotify.** Covers music that does *not* go through AirPlay: Spotify Connect
to real speakers, a computer, an Echo. OAuth with PKCE, so no application
secret is stored; tokens live in `/var/lib/dmd/spotify.json` with mode `0600`
and never appear in an exported configuration.

**A free MQTT topic.** Anything else can publish a JSON with `title`,
`artist`, `album`, `duration`, `position` and `playing` — Home Assistant's own
names (`media_title`, `media_artist`, …) are accepted too. This is how you
cover a HomePod started by voice or an Echo, which the DMD cannot see on its
own.

When several sources have something to say, AirPlay wins: if an audio stream
is arriving here, that is what is being listened to. Otherwise a playing
source beats a paused one.

### Passive sniffing does not work, and cannot

AirPlay 2 encrypts the stream end to end with keys derived from pairing. A
port mirror shows you device names in mDNS and nothing else. Being a paired
endpoint is the supported way to read the metadata, and that is what this is.

### Without Home Assistant

The default broker is `127.0.0.1` — a Mosquitto on the Pi itself. Home
Assistant is an option, not a requirement.

### With Home Assistant

With `mqtt.discovery` on, the DMD announces itself. A device appears carrying
the current track (title as the state, the rest as attributes), a switch per
service and brightness as a `number`. They are controllable, not just
readable. Everything is tied to the MQTT will, so if the service stops the
entities go *unavailable* instead of freezing on a value that looks live.

Nothing watches Home Assistant, and the DMD never needs to know where it is.
Discovery is published retained, so the broker replays it to whoever
subscribes later; and Home Assistant publishes `online` to
`homeassistant/status` when it starts, which the DMD subscribes to and treats
as the trigger to re-declare — after a random delay, so every MQTT device in
the house does not answer the same announcement in the same instant. The
Music page also has a manual re-declare button and one to remove the
entities.

### Track position

AirPlay sends `prgr` — three RTP timestamps at 44100 Hz — only on track
change and after a seek; Spotify answers only when polled. Between updates the
DMD counts the time itself from the last known-good value, using
`time.monotonic()` rather than the system clock: an NTP correction must not
make the progress bar jump.

### No album artwork, on purpose

At 64 pixels it would be unreadable, but more importantly it is made almost
entirely of mid-tones — the worst possible content for an S-PWM panel at a low
refresh rate. For the same reason the text is drawn **without antialiasing**
(edge shading is mid-tones too) and, with *fully saturated colours only*, in
eight colours: hierarchy between lines comes from changing hue rather than
brightness. See [Timing](#timing-or-why-white-lines-appear).

### Installation

```bash
sudo /opt/dmd/setup_nowplaying.sh
```

It asks for the speaker name and where the broker is, then does the rest:
Mosquitto, build dependencies, `nqptp`, `shairport-sync` built with AirPlay 2
and metadata, the dummy sound card, the configuration file, confinement to
cores 0-2 so core 3 stays with the panel, and the DMD's own MQTT section. It
is re-runnable and skips whatever is already done — including the fifteen
minute build. `--verifica` reports the state without changing anything.

It is installed with everything else but never run automatically: it is
optional, and the build alone takes a quarter of an hour. It depends on no
other file, so it can also be downloaded on its own.

### Dependency

`python3-paho-mqtt`. If it is missing, the Music page says so and Now playing
stays off; the rest of the DMD does not notice.

Full setup guide, including doing it by hand (in Italian):
[`docs/now-playing.it.md`](docs/now-playing.it.md).

---

## Credits

- [hzeller/rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) — the LED matrix library
- [kingdo9/rpi-rgb-led-matrix_pwm_experiment](https://github.com/kingdo9/rpi-rgb-led-matrix_pwm_experiment) — S-PWM panel support, without which none of this would be possible
- [PPUC/ZeDMD](https://github.com/PPUC/ZeDMD) and [PPUC/libzedmd](https://github.com/PPUC/libzedmd) — the protocol
- [vpinball/libdmdutil](https://github.com/vpinball/libdmdutil) — `dmdserver`, the Batocera side

## Documentation in Italian

- [`docs/manuale-completo.it.md`](docs/manuale-completo.it.md) — the full
  manual: first boot, system updates, wiring, panel tuning, installation from
  this repository, Batocera, updates, wear-resistant setup, troubleshooting.
  Also available as [PDF](docs/DMD_manuale_completo.pdf).
- [`docs/zedmd-wifi.it.md`](docs/zedmd-wifi.it.md) — connecting a ZeDMD-WiFi
  client (Batocera, Visual Pinball) to the display, and the Pi's own Wi-Fi.
  Also available as [PDF](docs/DMD_zedmd_wifi.pdf).
- [`docs/now-playing.it.md`](docs/now-playing.it.md) — installing
  shairport-sync, nqptp and Mosquitto, linking Spotify, and wiring the whole
  thing into Home Assistant. Also available as
  [PDF](docs/DMD_now_playing.pdf).
- [`docs/README.it.md`](docs/README.it.md) — service documentation
- [`docs/pubblicazione.it.md`](docs/pubblicazione.it.md) — release procedure

## License

GPLv3 — see [LICENSE](LICENSE).
