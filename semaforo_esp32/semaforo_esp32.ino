// Semáforo ESP32 — secuencia de semáforo con reporte a PC por Serial (+ opción WiFi)
// ROJO    -> pin 2 (20 s)  [obligatorio]
// VERDE   -> pin 5 (15 s)
// AMARILLO -> pin 4 (5 s)
// Orden: ROJO -> VERDE -> AMARILLO -> repetir (ciclo real de semáforo)
//
// MODO POR DEFECTO (Serial USB):
//   La ESP32 manda por Serial (115200 baud) una línea JSON cada segundo:
//     {"light":"ROJO","pin":2,"duration":20,"remaining":19}
//   El servidor Python (server.py) lee ese puerto y actualiza la página web.
//
// MODO WiFi (opcional): pon USE_WIFI en 1, configura SSID/PASS/SERVER_IP.
//   La ESP32 hace POST a http://SERVER_IP:8000/api/update con el mismo JSON.

#define PIN_ROJO 2        // obligatorio: 20 segundos
#define PIN_VERDE 5       // configurable
#define PIN_AMARILLO 4    // configurable

#define DUR_ROJO 20       // segundos
#define DUR_VERDE 15      // segundos
#define DUR_AMARILLO 5    // segundos

#define SERIAL_BAUD 115200

// ---------- WiFi opcional ----------
#define USE_WIFI 0
#if USE_WIFI
  #include <WiFi.h>
  #include <HTTPClient.h>
  const char* WIFI_SSID = "TU_WIFI";
  const char* WIFI_PASS = "TU_PASSWORD";
  const char* SERVER_URL = "http://192.168.1.100:8000/api/update"; // IP de tu PC
#endif

void apagaTodo() {
  digitalWrite(PIN_ROJO, LOW);
  digitalWrite(PIN_VERDE, LOW);
  digitalWrite(PIN_AMARILLO, LOW);
}

#if USE_WIFI
void wifiUpdate(const char* nombre, int pin, int duracion, int restante) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  char body[96];
  snprintf(body, sizeof(body),
           "{\"light\":\"%s\",\"pin\":%d,\"duration\":%d,\"remaining\":%d}",
           nombre, pin, duracion, restante);
  http.POST((uint8_t*)body, strlen(body));
  http.end();
}
#endif

// Enciende solo la luz indicada y reporta cada segundo su cuenta regresiva.
void fase(const char* nombre, int pin, int duracion) {
  apagaTodo();
  digitalWrite(pin, HIGH);
  for (int restante = duracion; restante > 0; restante--) {
    // Señal para la página web: JSON por Serial (y POST si USE_WIFI)
    Serial.printf("{\"light\":\"%s\",\"pin\":%d,\"duration\":%d,\"remaining\":%d}\n",
                  nombre, pin, duracion, restante);
    #if USE_WIFI
      wifiUpdate(nombre, pin, duracion, restante);
    #endif
    delay(1000);
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(PIN_ROJO, OUTPUT);
  pinMode(PIN_VERDE, OUTPUT);
  pinMode(PIN_AMARILLO, OUTPUT);
  apagaTodo();
  #if USE_WIFI
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(500);
  #endif
  delay(500);
}

void loop() {
  fase("ROJO", PIN_ROJO, DUR_ROJO);           // 20 s, pin 2
  fase("VERDE", PIN_VERDE, DUR_VERDE);        // 15 s
  fase("AMARILLO", PIN_AMARILLO, DUR_AMARILLO); // 5 s
}
