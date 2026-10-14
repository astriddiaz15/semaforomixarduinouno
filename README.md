# Semáforo ESP32 + Página web + Servidor

Monitor web del semáforo físico. La ESP32 prende los LEDs en secuencia y manda
por Serial (USB) el estado; el servidor lo recibe y la página lo muestra con
cuenta regresiva.

## Tiempos y pines (igual en el `.ino` y el servidor)

| Luz      | Pin | Duración |
|----------|----------|----------|
| ROJO     | 2        | 20 s     |
| VERDE    | 5        | 15 s     |
| AMARILLO | 4        | 5 s      |

Orden: ROJO → VERDE → AMARILLO → repetir.

## Archivos

- `semaforo_esp32.ino` — código para la ESP32 (con opción WiFi).
- `semaforo_arduino_uno.ino` — código para Arduino UNO / Nano / Mega (recomendado si tu placa es Arduino, no ESP32).
- `server.py` — servidor (página + API + lectura Serial). Solo librería estándar (+ `pyserial` opcional).
- `index.html` — interfaz web con el diseño Figma (la sirve `server.py`, no la abras directo).
- `requirements.txt` — solo `pyserial`.

## 1. Placa (Arduino IDE)

**Si tu placa es Arduino UNO / Nano / Mega:** abre `semaforo_arduino_uno.ino`
(versión sin WiFi ni `Serial.printf`, 100% compatible con AVR).

**Si tu placa es ESP32:** abre `semaforo_esp32.ino`.

En ambos casos:

1. Conecta la placa por USB (en ESP32 instala el driver CP210x si no la reconoce).
2. Arduino IDE → placa y puerto COM correctos.
3. Conecta LEDs con resistencia 220 Ω a GND:
   ROJO→pin 2, VERDE→pin 5, AMARILLO→pin 4.
4. Sube el código y abre el Monitor Serial a **115200 baud**: verás
   `{"light":"ROJO","pin":2,"duration":20,"remaining":19}` cada segundo.

Opción WiFi (solo ESP32): en el `.ino` pon `#define USE_WIFI 1`, configura
`WIFI_SSID`, `WIFI_PASS` y `SERVER_URL` con la IP de tu PC, y la ESP32 hará
`POST /api/update` en vez de (o además de) Serial.

## 2. Servidor

Necesitas Python 3.10+ (https://www.python.org/downloads/, marca "Add to PATH").

```bat
cd semaforo-esp32
pip install -r requirements.txt
python server.py
```

Opciones: `python server.py --port 8000 --serial COM7 --baud 115200`.
Por defecto escucha al Arduino en **COM7**; si tu placa está en otro puerto,
pásalo con `--serial COMx`. Reintenta solo hasta detectar la placa.

Abre **http://localhost:8000** en el navegador.

## 3. Página web

- Dibuja el semáforo y resalta la luz activa = puerto activo de la placa.
- Número grande = cuenta regresiva (segundos para el cambio de luz).
- Muestra pin activo, duración de la fase y modo (`serial` / `wifi`).
- Consulta `/api/status` cada 500 ms e interpola el conteo para que sea fluido.

Sin datos recientes de la placa (más de 3 s sin mensajes), la página muestra
**DESCONECTADO** con el semáforo apagado, hasta detectar señal real en COM7.

## Protocolo ESP32 → servidor

Línea Serial o `POST /api/update` con JSON:

```json
{"light":"ROJO","pin":2,"duration":20,"remaining":17}
```

`light` ∈ `ROJO | AMARILLO | VERDE`. El servidor calcula `remaining`
descontando el tiempo desde el último mensaje.
