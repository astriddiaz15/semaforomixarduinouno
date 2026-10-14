"""
Servidor del semáforo (Arduino UNO o ESP32).
- Sirve la página web (index.html) en http://localhost:8000
- API:
    GET  /api/status -> {"light","pin","duration","remaining","connected","mode","port","timestamp"}
    POST /api/update  (JSON de la placa por WiFi, solo ESP32) -> actualiza el estado
- Lee la placa por Serial USB (115200 baud). Requiere: pip install pyserial
- La página muestra el estado SOLO con datos reales de la placa.
  Si no hay datos recientes (mas de 3 s), reporta connected=false
  y la página muestra "ESPERANDO ARDUINO".
Solo usa la librería estándar (+ pyserial). Sin frameworks.
Uso:  python server.py [--port 8000] [--serial COM3] [--baud 115200]
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
INDEX = BASE / "index.html"

# Si no llegan datos en este tiempo, se considera que no hay placa.
STALE_S = 3.0

# Secuencia oficial (debe coincidir con el .ino)
SECUENCIA = [
    {"light": "ROJO", "pin": 2, "duration": 20},
    {"light": "VERDE", "pin": 5, "duration": 15},
    {"light": "AMARILLO", "pin": 4, "duration": 5},
]

estado = {
    "light": None,
    "pin": None,
    "duration": None,
    "remaining": 0.0,
    "connected": False,   # True solo con datos frescos de la placa
    "mode": "serial",
    "port": None,
    "timestamp": 0.0,     # 0 = aún no llega ningún dato
}
lock = threading.Lock()


def set_estado(light, pin, duration, remaining, connected, mode, port):
    with lock:
        estado.update({
            "light": light, "pin": int(pin),
            "duration": int(duration),
            "remaining": max(0.0, float(remaining)),
            "connected": bool(connected),
            "mode": mode, "port": port,
            "timestamp": time.time(),
        })


def marcar_desconectado():
    with lock:
        estado.update({
            "light": None, "pin": None, "duration": None,
            "remaining": 0.0, "connected": False,
            "mode": "serial", "port": None,
            "timestamp": 0.0,
        })


def parse_linea(linea: str):
    """Acepta JSON {"light":..,"pin":..,"duration":..,"remaining":..}
    o texto simple con la palabra ROJO/VERDE/AMARILLO."""
    linea = linea.strip()
    if not linea:
        return None
    if linea.startswith("{"):
        try:
            d = json.loads(linea)
            light = str(d.get("light", "")).upper()
            if light not in ("ROJO", "VERDE", "AMARILLO"):
                return None
            dur = int(d.get("duration", 0)) or next(
                f["duration"] for f in SECUENCIA if f["light"] == light)
            pin = int(d.get("pin", 0)) or next(
                f["pin"] for f in SECUENCIA if f["light"] == light)
            rem = float(d.get("remaining", dur))
            return light, pin, dur, rem
        except (ValueError, KeyError, TypeError):
            return None
    up = linea.upper()
    for f in SECUENCIA:
        if f["light"] in up:
            return f["light"], f["pin"], f["duration"], f["duration"]
    return None


def hilo_serial(puerto, baud):
    """Lee el Serial del Arduino en el puerto dado. Reintenta hasta detectarlo."""
    try:
        import serial
    except ImportError:
        print("[serial] Falta pyserial, instálalo con: pip install pyserial")
        return
    ultimo_luz = None
    while True:
        try:
            print(f"[serial] Abriendo {puerto} @ {baud} ...")
            with serial.Serial(puerto, baud, timeout=1) as ser:
                time.sleep(2)  # la placa se reinicia al abrir el puerto
                print(f"[serial] Arduino detectado en {puerto}. Recibiendo datos...")
                while True:
                    raw = ser.readline().decode("utf-8", "ignore")
                    p = parse_linea(raw)
                    if p:
                        light, pin, dur, rem = p
                        set_estado(light, pin, dur, rem, True, "serial", puerto)
                        if light != ultimo_luz:
                            ultimo_luz = light
                            print(f"[serial] {puerto}: luz {light} (pin {pin}, {dur} s)")
        except Exception as e:  # noqa: BLE001 - debe reintentar siempre
            print(f"[serial] {puerto}: {e} -> reintentando en 2 s")
            ultimo_luz = None
            marcar_desconectado()
            time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                data = INDEX.read_bytes()
            except FileNotFoundError:
                self.send_error(404, "index.html no encontrado junto a server.py")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/api/status":
            with lock:
                snap = dict(estado)
            ahora = time.time()
            # Sin datos recientes = sin placa: no mostrar estado viejo.
            if not snap["connected"] or (ahora - snap["timestamp"]) > STALE_S:
                snap = {"light": None, "pin": None, "duration": None,
                        "remaining": 0.0, "connected": False,
                        "mode": "serial", "port": None, "timestamp": ahora}
            else:
                # Descuenta el tiempo desde el último mensaje (cuenta regresiva).
                snap["remaining"] = max(0.0, snap["remaining"] - (ahora - snap["timestamp"]))
                snap["timestamp"] = ahora
            self._json(snap)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/update":
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json({"ok": False, "error": "JSON inválido"}, 400)
            light = str(d.get("light", "")).upper()
            if light not in ("ROJO", "VERDE", "AMARILLO"):
                return self._json({"ok": False, "error": "light debe ser ROJO/VERDE/AMARILLO"}, 400)
            dur = int(d.get("duration", 0)) or next(
                f["duration"] for f in SECUENCIA if f["light"] == light)
            pin = int(d.get("pin", 0)) or next(
                f["pin"] for f in SECUENCIA if f["light"] == light)
            rem = float(d.get("remaining", dur))
            set_estado(light, pin, dur, rem, True, "wifi", self.client_address[0])
            return self._json({"ok": True})
        self.send_error(404)


def main():
    ap = argparse.ArgumentParser(description="Servidor monitor del semáforo (Arduino/ESP32)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--serial", default="COM7", help="Puerto serial del Arduino (por defecto COM7)")
    ap.add_argument("--baud", type=int, default=115200)
    args = ap.parse_args()

    threading.Thread(target=hilo_serial, args=(args.serial, args.baud), daemon=True).start()

    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"Abre en tu navegador: http://localhost:{args.port}")
    print(f"Detectando Arduino en {args.serial} @ {args.baud} baud (o POST WiFi a /api/update) ...")
    print("La página mostrará ESPERANDO ARDUINO hasta detectar datos reales.")
    print("Ctrl+C para detener.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
