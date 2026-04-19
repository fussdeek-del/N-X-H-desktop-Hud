// hUD Firmware for RP2040 + ST7789
// reads serial data from PC and displays on TFT

#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <SPI.h>

// PIN CONFIG (matched to your PCB schematic) 
#define TFT_CS    17   // GPIO17 - pin 22 on Pico
#define TFT_DC    20   // GPIO20 - pin 26 on Pico
#define TFT_RST   21   // GPIO21 - pin 27 on Pico
#define TFT_BL    22   // GPIO22 - pin 29 on Pico (backlight)

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

//  DATA VARIABLES 
String fps     = "--";
String cpu     = "--";
String ram     = "--";
String disk    = "--";
String timeStr = "--:--:--";

// Keep previous values to avoid redrawing unchanged fields
String prev_fps     = "";
String prev_cpu     = "";
String prev_ram     = "";
String prev_disk    = "";
String prev_time    = "";

// COLORS 
#define COLOR_BG     0x0000   // Black background
#define COLOR_LABEL  0x4A49   // Muted grey for labels
#define COLOR_VALUE  0xFFFF   // White for values
#define COLOR_BOX    0x2124   // Dark box behind each row

//  DRAW ONE ROW (no-flicker: only redraws value if changed) 
void drawRow(int y, const char* label, String value, String& prev, const char* unit = "") {
  if (value == prev) return;  // skip if nothing changed

  // Erase old value area only (not the whole screen)
  tft.fillRect(100, y, 140, 24, COLOR_BG);

  // Draw value
  tft.setTextColor(COLOR_VALUE);
  tft.setTextSize(2);
  tft.setCursor(100, y);
  tft.print(value);
  if (strlen(unit) > 0) tft.print(unit);

  prev = value;
}

//  DRAW STATIC LABELS (called once at startup)
void drawLabels() {
  tft.setTextColor(COLOR_LABEL);
  tft.setTextSize(2);

  tft.setCursor(10, 20);  tft.print("FPS :");
  tft.setCursor(10, 60);  tft.print("CPU :");
  tft.setCursor(10, 100); tft.print("RAM :");
  tft.setCursor(10, 140); tft.print("DSK :");
  tft.setCursor(10, 190); tft.print("TIME:");
}

//  PARSE INCOMING SERIAL LINE 
void parseData(String data) {
  int start;

  start = data.indexOf("FPS:");
  if (start != -1) fps = data.substring(start + 4, data.indexOf(';', start));

  start = data.indexOf("CPU:");
  if (start != -1) cpu = data.substring(start + 4, data.indexOf(';', start));

  start = data.indexOf("RAM:");
  if (start != -1) ram = data.substring(start + 4, data.indexOf(';', start));

  start = data.indexOf("DISK:");
  if (start != -1) disk = data.substring(start + 5, data.indexOf(';', start));

  start = data.indexOf("TIME:");
  if (start != -1) timeStr = data.substring(start + 5, data.indexOf(';', start));
}

//  SETUP 
void setup() {
  Serial.begin(115200);

  // Turn on backlight
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);

  // Init display
  tft.init(240, 240);
  tft.setRotation(0);
  tft.fillScreen(COLOR_BG);

  // Draw static labels once
  drawLabels();
}

//  LOOP 
void loop() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    parseData(data);

    // only redraws rows where value actually changed — no flicke
    drawRow(20,  "FPS :", fps,     prev_fps);
    drawRow(60,  "CPU :", cpu,     prev_cpu,  "%");
    drawRow(100, "RAM :", ram,     prev_ram,  "%");
    drawRow(140, "DSK :", disk,    prev_disk, "%");
    drawRow(190, "TIME:", timeStr, prev_time);
  }
}