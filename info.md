# Baseus Security

Bring your **Baseus Security** cameras into Home Assistant: live video plus
battery, Wi-Fi signal and online status.

Requires the companion **[baseus-cam-bridge](https://github.com/pickeld/baseus-cam-bridge)**
running on your LAN to provide the RTSP streams. This integration signs in with
your own Baseus account to discover your cameras and connects each one to the
bridge.

**Setup:** add the integration, enter your Baseus account + password, and the
RTSP base URL of your bridge (e.g. `rtsp://homeassistant.local:8554`).

Use only with cameras you own or are authorized to manage.
