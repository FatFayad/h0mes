import json, os, re, time, urllib.request

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
FILES = {
    "media.example.duckdns.org": "/logs/proxy-host-2_access.log",
    "app.example.duckdns.org": "/logs/proxy-host-4_access.log",
}
COOLDOWN = 600  # 10 min per (domain, ip, ua)
LINE_RE = re.compile(
    r'-\s+(\d{3})\s+\d{3}\s+-\s+\S+\s+\S+\s+\S+\s+"([^"]+)"\s+\[Client\s+([^\]]+)\].*?"([^"]+)"\s+"[^"]*"\s*$'
)
SKIP_EXT = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".map", ".txt", ".xml")
SKIP_PATHS = ("/robots.txt", "/favicon.ico", "/sitemap.xml", "/.env", "/wp-", "/cgi-bin")
BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|scan|fetch|http://|https://|curl|wget|python|go-http|headless|claude|gpt|openai|anthropic|infrawatch|palo alto|censys|shodan|zgrab|masscan|uptime|monitor|check',
    re.I,
)

seen = {}
state = {}

def send_discord(msg):
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps({"content": msg}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "H0MES-Alerts/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception as e:
        print(f"discord err: {e}", flush=True)

def open_end(path):
    if not os.path.exists(path):
        return None, None
    f = open(path, "r", errors="ignore")
    f.seek(0, os.SEEK_END)
    return f, os.fstat(f.fileno()).st_ino

for dom, path in FILES.items():
    state[path] = open_end(path)

print("npm-alerts (bot-filtered) watching:", list(FILES.keys()), flush=True)

while True:
    now = time.time()
    for dom, path in FILES.items():
        fh, ino = state[path]
        try:
            st = os.stat(path)
            if fh is None or st.st_ino != ino or st.st_size < fh.tell():
                if fh: fh.close()
                fh = open(path, "r", errors="ignore")
                ino = st.st_ino
                state[path] = (fh, ino)
        except FileNotFoundError:
            continue

        for line in fh:
            m = LINE_RE.search(line)
            if not m:
                continue
            status, req_path, ip, ua = m.groups()
            clean_path = req_path.split("?", 1)[0].lower()
            if clean_path.endswith(SKIP_EXT) or clean_path.startswith(SKIP_PATHS):
                continue
            if BOT_RE.search(ua):
                continue
            key = (dom, ip, ua[:60])
            if now - seen.get(key, 0) < COOLDOWN:
                continue
            seen[key] = now
            send_discord(
                f"👀 **Visitor on `{dom}`**\n"
                f"• **IP:** `{ip}` | **Path:** `{req_path}` (`{status}`)\n"
                f"• **UA:** `{ua[:120]}`"
            )
    time.sleep(2)
