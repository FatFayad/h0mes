# h0mes

Small scripts and notes from my Debian home server (`h0mes`). It runs Docker/CasaOS, a Glance dashboard, a virtualized pfSense dual-WAN router under KVM, and an old Android tablet taped up as a wall monitor.

## What is in here

- `glance-netgraph/netgraph.py` - tiny zero-dependency Python server that reads `/sys/class/net/<iface>/statistics/{rx,tx}_bytes` every 2 seconds and returns live SVG traffic sparklines (`WAN`, `RoomAP`, `LAN`) for Glance.
- `npm-alerts/watch.py` - tails Nginx Proxy Manager access logs, drops static assets, scanner paths (`/.env`, `/wp-`), and bots, and pings Discord when a real browser hits one of my domains.
- `tablet-kiosk/tablet-kiosk.sh` - runs from cron to keep `adb reverse tcp:4000 tcp:4000` alive to a WallPanel Android tablet, waking it when my PC is online and putting it to sleep when my PC is off (with a 20-minute manual wake override).
- `pfsense.md` - notes on how the dual-WAN pfSense KVM VM is bridged across a 4-port NIC, the `halt_poll_ns=0` CPU fix, and three network faults I had to trace from logs.
