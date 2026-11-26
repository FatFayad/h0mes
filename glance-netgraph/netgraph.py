import json, os, threading, time
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

IFACES = [
    ("wan", "WAN", "enp5s0f0"),
    ("roomap", "RoomAP", "enp6s0f0"),
    ("lan", "LAN", "enp6s0f1"),
]
POINTS = 30
INTERVAL = 2.0
NET_ROOT = "/host/sys/class/net"

history = {k: deque([(0.0, 0.0)] * POINTS, maxlen=POINTS) for k, _, _ in IFACES}
lock = threading.Lock()

def read_bytes(dev):
    try:
        with open(f"{NET_ROOT}/{dev}/statistics/rx_bytes") as f:
            rx = int(f.read().strip())
        with open(f"{NET_ROOT}/{dev}/statistics/tx_bytes") as f:
            tx = int(f.read().strip())
        return rx, tx
    except OSError:
        return 0, 0

def sampler():
    prev = {k: read_bytes(dev) for k, _, dev in IFACES}
    prev_t = time.monotonic()
    while True:
        time.sleep(INTERVAL)
        now_t = time.monotonic()
        dt = max(now_t - prev_t, 0.1)
        prev_t = now_t
        with lock:
            for k, _, dev in IFACES:
                rx, tx = read_bytes(dev)
                prx, ptx = prev[k]
                prev[k] = (rx, tx)
                in_mbs = max(0.0, (rx - prx) / dt / 1048576.0)
                out_mbs = max(0.0, (tx - ptx) / dt / 1048576.0)
                history[k].append((in_mbs, out_mbs))

def fmt_rate(mbs):
    if mbs >= 10.0:
        return f"{mbs:.1f} MB/s"
    if mbs >= 0.1:
        return f"{mbs:.2f} MB/s"
    return f"{mbs * 1024:.0f} KB/s"

def make_svg(pts):
    w, h, mid = 120, 44, 22
    vmax = max(max(max(a, b) for a, b in pts), 0.1)
    n = len(pts) - 1
    in_pts = []
    out_pts = []
    for i, (rx, tx) in enumerate(pts):
        x = round(i * w / n, 1)
        y_in = round(mid - (rx / vmax) * (mid - 2), 1)
        y_out = round(mid + (tx / vmax) * (mid - 2), 1)
        in_pts.append(f"{x},{y_in}")
        out_pts.append(f"{x},{y_out}")
    in_poly = f"0,{mid} " + " ".join(in_pts) + f" {w},{mid}"
    out_poly = f"0,{mid} " + " ".join(out_pts) + f" {w},{mid}"
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="44" preserveAspectRatio="none" '
        f'style="display:block;border-radius:4px;background:rgba(255,255,255,0.03);">'
        f'<line x1="0" y1="{mid}" x2="{w}" y2="{mid}" stroke="rgba(255,255,255,0.12)" stroke-width="0.8"/>'
        f'<polygon points="{in_poly}" fill="rgba(56,161,243,0.35)"/>'
        f'<polyline points="{" ".join(in_pts)}" fill="none" stroke="#38a1f3" stroke-width="1.3"/>'
        f'<polygon points="{out_poly}" fill="rgba(237,137,54,0.35)"/>'
        f'<polyline points="{" ".join(out_pts)}" fill="none" stroke="#ed8936" stroke-width="1.3"/>'
        f'</svg>'
    )

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with lock:
            items = []
            for k, label, _ in IFACES:
                pts = list(history[k])
                cur_in, cur_out = pts[-1]
                items.append({
                    "key": k,
                    "label": label,
                    "in": fmt_rate(cur_in),
                    "out": fmt_rate(cur_out),
                    "svg": make_svg(pts),
                })
        body = json.dumps({"interfaces": items}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

threading.Thread(target=sampler, daemon=True).start()
HTTPServer(("0.0.0.0", 9199), Handler).serve_forever()
