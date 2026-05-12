#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <LittleFS.h>
#include <esp_task_wdt.h>


#define PIN_SIGNAL 34   
#define PIN_LED 2       


volatile int baseline = 0;       
volatile int thresholdDelta = 150; 
volatile int threshold = 0;      
unsigned long muonCount = 0; 

WebServer server(80);
const char* logFile = "/muon_log.csv";

struct ParticleEvent {
  unsigned long timestamp;
  int peakValue;
};
QueueHandle_t dataQueue;

void adcTask(void *pvParameters) {
  analogSetAttenuation(ADC_0db);
  

  for (;;) {
    int val = analogRead(PIN_SIGNAL);

    if (val > threshold && threshold > 0) {
      int peakValue = val;
      unsigned long timeout = micros();
      
      while (analogRead(PIN_SIGNAL) > (baseline + thresholdDelta / 2)) {
        int currentVal = analogRead(PIN_SIGNAL);
        if (currentVal > peakValue) peakValue = currentVal;
        if (micros() - timeout > 5000) break; // Предохранитель
      }

      ParticleEvent ev = {millis() / 1000, peakValue};
      xQueueSend(dataQueue, &ev, 0);

      digitalWrite(PIN_LED, HIGH);
      delayMicroseconds(2000); 
      digitalWrite(PIN_LED, LOW);
    }
    
  }
}

void handleRoot() {
  String html = "<html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<title>Muon Detector</title><style>";
  html += "body{font-family:sans-serif;text-align:center;background:#f4f4f4;padding:10px;}";
  html += ".card{background:white;margin:10px auto;padding:20px;border-radius:10px;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}";
  html += ".btn{display:inline-block;padding:12px;margin:5px;background:#007bff;color:white;text-decoration:none;border-radius:5px;width:90%; font-weight:bold;}";
  html += "input[type=range] {width: 100%; margin: 20px 0;}";
  html += "</style></head><body>";
  
  html += "<div class='card'><h1> Мюоны</h1>";
  html += "<div style='font-size:48px;font-weight:bold;color:#007bff'>" + String(muonCount) + "</div>";
  html += "<p>Текущий порог: <b>" + String(threshold) + ")</p>";
  
  // ФОРМА С ПОЛЗУНКОМ
  html += "<form action='/set_thr' method='GET'>";
  html += "Настройка чувствительности:<br>";
  html += "<input type='range' name='val' min='50' max='2000' value='" + String(thresholdDelta) + "' oninput='this.nextElementSibling.value = this.value'>";
  html += "<output style='font-weight:bold; font-size:1.2em'>" + String(thresholdDelta) + "</output><br>";
  html += "<input type='submit' value='ПРИМЕНИТЬ ПОРОГ' style='background:#6f42c1; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;'>";
  html += " </form>";

  html += "<hr>";
  html += "<a href='/' class='btn'>ОБНОВИТЬ ЭКРАН</a>";
  html += "<a href='/download' class='btn' style='background:#28a745'>СКАЧАТЬ CSV</a>";
  html += "<a href='/clear' class='btn' style='background:#dc3545' onclick=\"return confirm('Удалить данные?')\">ОЧИСТИТЬ ЛОГ</a>";
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

void handleDownload() {
  if (LittleFS.exists(logFile)) {
    File file = LittleFS.open(logFile, FILE_READ);
    server.streamFile(file, "text/csv");
    file.close();
  } else {
    server.send(404, "text/plain", "No log file yet.");
  }
}

void handleClear() {
  LittleFS.remove(logFile);
  muonCount = 0;
  server.sendHeader("Location", "/");
  server.send(303);
}

void handleSetThreshold() {
  if (server.hasArg("val")) {
    thresholdDelta = server.arg("val").toInt();
    threshold = baseline + thresholdDelta; // Сразу пересчитываем порог
    Serial.printf("Новый порог установлен: %d (Total: %d)\n", thresholdDelta, threshold);
  }
  // После смены значения просто возвращаем пользователя на главную
  server.sendHeader("Location", "/");
  server.send(303);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  
  if (!LittleFS.begin(true)) {
    Serial.println("FS Error");
  }

  delay(1000);
  analogSetAttenuation(ADC_0db);
  long sum = 0;
  for (int i = 0; i < 5000; i++) {
    sum += analogRead(PIN_SIGNAL);
    delayMicroseconds(100);
  }
  baseline = sum / 5000;
  threshold = baseline + thresholdDelta;

  dataQueue = xQueueCreate(100, sizeof(ParticleEvent));

  disableCore0WDT(); 
  // Запуск Ядра 0
  xTaskCreatePinnedToCore(adcTask, "ADC_TASK", 4096, NULL, 2, NULL, 0);


  WiFi.setSleep(false); 
  WiFi.softAP("MuonDetector", "12345678");

  server.on("/", handleRoot);
  server.on("/download", handleDownload);
  server.on("/clear", handleClear);

  server.on("/set_thr", handleSetThreshold); 

  server.begin();

  Serial.println("System Ready. IP: 192.168.4.1");
}

void loop() {
  server.handleClient();

  ParticleEvent ev;
  if (xQueueReceive(dataQueue, &ev, 0) == pdPASS) {
    muonCount++;
    File file = LittleFS.open(logFile, FILE_APPEND);
    if (file) {
      file.printf("%lu,%d\n", ev.timestamp, ev.peakValue);
      file.close();
    }
    Serial.printf("Hit! Time: %lu, Peak: %d\n", ev.timestamp, ev.peakValue);
  }
}