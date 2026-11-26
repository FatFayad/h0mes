# Dual-WAN pfSense VM on Debian KVM

My router is a pfSense VM running under KVM/libvirt on the same Debian box as the rest of my homelab. A 4-port NIC is split with Linux bridges so the host hands two WAN uplinks (ISP 1 PPPoE fiber + ISP 2 DHCP broadband), the main LAN, and a separate access-point subnet straight into the VM.

Weighted load balancing splits normal traffic across both ISPs, and a tiered failover gateway group handles latency-sensitive traffic so games and calls stay on the primary line unless it drops.

![Home network topology](network-map.svg)

## Host CPU fix

Out of the box, the pfSense VM burned around 115% host CPU even at idle because of KVM halt polling. Setting:

```bash
echo 0 | sudo tee /sys/module/kvm/parameters/halt_poll_ns
```

dropped host CPU usage for the VM from ~115% down to ~16%.

## Three faults I traced while setting this up

1. PPPoE link dropped. Physical link on the host NIC and Linux bridge was still UP, so I skipped reseating cables and checked `/var/log/ppp.log` inside pfSense. It showed an authentication rejection from the ISP side rather than a local bridge or VM drop.
2. Secondary WAN had carrier UP inside pfSense but passed zero traffic. The upstream router had a MAC whitelist active, and the KVM virtual NIC was presenting a generated bridge MAC. Matching the VM interface MAC to the whitelisted address fixed it immediately.
3. Web browsing felt sluggish even though speedtests and gateway pings looked fine. One ISP's DHCP lease was injecting a slow DNS resolver into pfSense. Disabling ISP DHCP DNS override and setting explicit resolvers cleared the lag.
