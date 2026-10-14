// Semaforo para Arduino UNO (o cualquier placa AVR: Nano, Mega, etc.)
// ROJO     -> pin 2 (20 s)
// VERDE    -> pin 5 (15 s)
// AMARILLO -> pin 4 (5 s)
// Orden: ROJO -> VERDE -> AMARILLO -> repetir
//
// La placa manda por Serial USB (115200 baud) una linea JSON cada segundo:
//   {"light":"ROJO","pin":2,"duration":20,"remaining":19}
// El servidor Python (server.py) lee ese puerto y actualiza la pagina web.
// Protocolo identico al de la version ESP32: server.py e index.html no cambian.

#define PIN_ROJO 2        // 20 segundos
#define PIN_VERDE 5       // configurable
#define PIN_AMARILLO 4    // configurable

#define DUR_ROJO 20       // segundos
#define DUR_VERDE 15      // segundos
#define DUR_AMARILLO 5    // segundos

#define SERIAL_BAUD 115200

void apagaTodo() {
  digitalWrite(PIN_ROJO, LOW);
  digitalWrite(PIN_VERDE, LOW);
  digitalWrite(PIN_AMARILLO, LOW);
}

// Serial.printf no existe en AVR: se arma el JSON con Serial.print.
void reporta(const char* nombre, int pin, int duracion, int restante) {
  Serial.print("{\"light\":\"");
  Serial.print(nombre);
  Serial.print("\",\"pin\":");
  Serial.print(pin);
  Serial.print(",\"duration\":");
  Serial.print(duracion);
  Serial.print(",\"remaining\":");
  Serial.print(restante);
  Serial.println("}");
}

// Enciende solo la luz indicada y reporta cada segundo su cuenta regresiva.
void fase(const char* nombre, int pin, int duracion) {
  apagaTodo();
  digitalWrite(pin, HIGH);
  for (int restante = duracion; restante > 0; restante--) {
    reporta(nombre, pin, duracion, restante);
    delay(1000);
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(PIN_ROJO, OUTPUT);
  pinMode(PIN_VERDE, OUTPUT);
  pinMode(PIN_AMARILLO, OUTPUT);
  apagaTodo();
  delay(500);
}

void loop() {
  fase("ROJO", PIN_ROJO, DUR_ROJO);             // 20 s, pin 2
  fase("VERDE", PIN_VERDE, DUR_VERDE);          // 15 s
  fase("AMARILLO", PIN_AMARILLO, DUR_AMARILLO);  // 5 s
}
