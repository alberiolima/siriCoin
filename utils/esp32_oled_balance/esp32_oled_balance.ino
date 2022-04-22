/*
 * SiriCoin OLED Balance
 * ESP32 OLED display balance
 * By Alberio Lima (Brazil)
 * 04/2022
 * Tested on Heltec WiFi LoRa 32 (v2)
 */
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h" 
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <SSD1306.h> // alias for `#include "SSD1306Wire.h"`

/* Pinos do display OLED I2C */
#define PINO_OLED_SDA    4
#define PINO_OLED_SCL   15
#define PINO_OLED_RST   16 //RST must be set by software
#define PINO_OLED_VXT   21
#define OLED_ADRESS   0x3c

/* User info */
const char *SSID = "your_ssid";
const char *WIFI_PASS = "your_password"; 
const char* minerAddr   = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674"; //SiriCoin address

/* Server info (no need change) */
const char* url_balance = "accounts/accountBalance/";
const char* serverAddr  = "https://siricoin-node-1.dynamic-dns.net:5005/";

SSD1306 display(OLED_ADRESS, PINO_OLED_SDA, PINO_OLED_SCL, PINO_OLED_RST);

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); //disable brownout detector
  Serial.begin(115200);
  
  /* Init OLED LCD */  
  Wire.begin(PINO_OLED_SDA,PINO_OLED_SCL);
  pinMode( PINO_OLED_VXT, OUTPUT );
  digitalWrite( PINO_OLED_VXT, LOW );
  delay(1000);
  display.init();
  //display.flipScreenVertically();  
  //display.setFont(ArialMT_Plain_10);
  //display.setFont(ArialMT_Plain_16);
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.setFont(ArialMT_Plain_24);
  display.drawString(0, 0, "SiriCoin");
  display.drawString(0, 24, "Hello");
  display.display();
  
  /* Init Wifi */
  Serial.print("Connecting ");
  Serial.println(SSID);
  WiFi.mode(WIFI_STA); 
  btStop();
  WiFi.begin(SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(250); 
  }
  Serial.println();
  Serial.println("Connected to WiFi");
  Serial.println("Local IP address: " + WiFi.localIP().toString());
  Serial.println();

}

void loop() {
  
  /* Update display information */
  statusDisplay();
  delay(30000);
  
}

/* function to update display information */
void statusDisplay() {
  String url = String(serverAddr) + String(url_balance) + minerAddr;
  String str_balance = "None";
  String payload = "";
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;
  
  if (http.begin(client, url)) {
    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
      payload = http.getString();
      //Serial.print("payload :");
      //Serial.println(payload );
      DynamicJsonDocument doc(1024);
      deserializeJson(doc, payload);
      str_balance = doc["result"]["balance"].as<String>();
    } else {
      Serial.printf("Get fetch failed - error: %s\n", http.errorToString(httpCode).c_str());
    }
  }
  
  /* Display information */
  display.clear();
  display.drawString(0, 0, "SiriCoin");
  display.drawString(0, 24, str_balance );
  display.display();
}
