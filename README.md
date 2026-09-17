# Baseus Security for Home Assistant

A custom [HACS](https://hacs.xyz/) integration that brings your **Baseus
Security** cameras into Home Assistant — live video plus battery, Wi-Fi signal
and online status for each camera.

Baseus cameras don't expose RTSP/ONVIF on their own, so this integration is a
thin layer on top of the companion project
**[baseus-cam-bridge](https://github.com/pickeld/baseus-cam-bridge)**, which runs
on your LAN and republishes each camera as a standard RTSP stream. This
integration signs in with **your own Baseus account** to enumerate your cameras
and then wires each one up to the bridge's stream.

> Use this only with cameras you own or are authorized to manage.

---

## What you get

- A `camera` entity per Baseus camera, using the bridge's RTSP stream (works with
  the HA stream component, Picture Glance cards, recording, etc.)
- A **battery** sensor and **Wi-Fi signal** sensor (best-effort, per model)
- A **connectivity** binary sensor (online / offline)
- Automatic discovery of every camera on your account

---

## Prerequisites

1. A running **[baseus-cam-bridge](https://github.com/pickeld/baseus-cam-bridge)**
   on your network (Docker recommended). Note its RTSP base URL, e.g.
   `rtsp://homeassistant.local:8554`.
2. Home Assistant 2024.4 or newer.

---

## Install via HACS

1. HACS → **Integrations** → three-dot menu → **Custom repositories**.
2. Add `https://github.com/pickeld/baseus-home-assistant` with category
   **Integration**.
3. Install **Baseus Security**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Baseus Security**.
5. Enter your Baseus account, password, and the bridge's RTSP base URL.

### Manual install

Copy `custom_components/baseus_security` into your HA `config/custom_components/`
directory and restart.

---

## Configuration

Everything is entered in the UI config flow:

| Field | Meaning |
|---|---|
| Account | Your Baseus app login (email or phone) |
| Password | Your Baseus app password |
| RTSP base URL | Base URL of your baseus-cam-bridge (no trailing slash) |
| Region | `AUTO`, or force `US` / `EU` / `AU` |
| Phone country code | Used at login (e.g. `1`, `44`, `61`) |
| Also add offline cameras | Create entities for currently-offline cameras too |

Credentials are stored in Home Assistant's config entry store, the same as any
other cloud integration.

---

## How it works

```
Baseus cloud --(login + device list)--> coordinator --> camera/sensor entities
your LAN     --(RTSP from bridge)------> camera stream_source = rtsp://.../<slug>
```

- The coordinator calls `baseus_bridge.cloud` (from baseus-cam-bridge) in the
  executor to list your cameras and their status every few minutes.
- Each camera entity's `stream_source` is `RTSP base + / + <camera slug>`, so the
  slugs must match between the bridge and this integration (they use the same
  `baseus_bridge` slug logic, so they line up automatically).

---

## Troubleshooting

- **No cameras appear** — confirm the account/password are correct and that the
  bridge lists the same cameras (`docker compose run --rm baseus-cam-bridge python -m baseus_bridge discover`).
- **Camera entity but no video** — check the RTSP base URL and that the bridge is
  reachable from Home Assistant. Battery cameras can take ~10–15s to wake.
- **Wrong battery/signal** — those fields vary by model; open an issue with your
  camera model so the field mapping can be extended.

---

## License

MIT — see [LICENSE](LICENSE).
