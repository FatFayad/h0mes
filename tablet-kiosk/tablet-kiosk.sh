#!/usr/bin/env bash
set -u
SERIAL="${ADB_SERIAL:?Set ADB_SERIAL}"
APP="com.thanksmister.iot.wallpanel/.ui.activities.BrowserActivityNative"
PC_IPS=("${PC_IP_1:-192.168.1.100}")
ADB="adb -s $SERIAL"
STATE_FILE="/tmp/tablet-pc-state"
WAKE_FILE="/tmp/tablet-wake-until"

[ "$($ADB get-state 2>/dev/null)" = "device" ] || exit 0

is_awake() {
  $ADB shell dumpsys power 2>/dev/null | grep -q "mWakefulness=Awake"
}

wake() {
  $ADB reverse tcp:4000 tcp:4000 >/dev/null
  $ADB shell svc power stayon usb >/dev/null
  $ADB shell input keyevent 224 >/dev/null
  $ADB shell am start -n "$APP" >/dev/null
}

sleep_tablet() {
  $ADB shell svc power stayon false >/dev/null
  $ADB shell input keyevent 223 >/dev/null
}

pc_up() {
  for ip in "${PC_IPS[@]}"; do
    ping -c 1 -W 2 "$ip" >/dev/null 2>&1 && return 0
  done
  return 1
}

case "${1:-ensure}" in
  wake)
    wake
    ;;
  sleep)
    rm -f "$WAKE_FILE"
    sleep_tablet
    ;;
  pc-check)
    if pc_up; then
      echo "on" > "$STATE_FILE"
      rm -f "$WAKE_FILE"
      is_awake || wake
    else
      echo "off" > "$STATE_FILE"
      NOW=$(date +%s)
      UNTIL=$(cat "$WAKE_FILE" 2>/dev/null || echo 0)
      [ "$NOW" -ge "$UNTIL" ] && rm -f "$WAKE_FILE" && sleep_tablet
    fi
    ;;
  ensure)
    TUNNEL_OK=1
    if ! $ADB reverse --list 2>/dev/null | grep -q "tcp:4000"; then
      $ADB reverse tcp:4000 tcp:4000 >/dev/null
      TUNNEL_OK=0
    fi
    STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "on")
    if [ "$STATE" = "on" ]; then
      if [ "$TUNNEL_OK" -eq 0 ] || ! is_awake; then
        wake
      fi
    else
      NOW=$(date +%s)
      UNTIL=$(cat "$WAKE_FILE" 2>/dev/null || echo 0)
      if is_awake; then
        if [ "$UNTIL" -eq 0 ]; then
          echo $((NOW + 1200)) > "$WAKE_FILE"
          wake
        elif [ "$NOW" -ge "$UNTIL" ]; then
          rm -f "$WAKE_FILE"
          sleep_tablet
        fi
      else
        [ "$UNTIL" -gt 0 ] && [ "$NOW" -ge "$UNTIL" ] && rm -f "$WAKE_FILE"
      fi
    fi
    ;;
esac
