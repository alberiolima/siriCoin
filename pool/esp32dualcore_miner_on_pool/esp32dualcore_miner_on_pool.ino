/*
  !!!TEST VERSION (for testers)!!!
  ESP32 dual core mining on pool for SiriCoin
  Developed by Albério Lima 
  https://github.com/alberiolima
  06-2022 Brazil

  Serial 115200 baud
  LED blink 1x job received
  LED blink 2x error
  
*/

#include <ArduinoJson.h>
#include <esp_task_wdt.h>
#include <WiFi.h>
#include <HTTPClient.h>  
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "sph_keccak.h"

#ifndef LED_BUILTIN
  #define LED_BUILTIN 2
#endif
#define LED_ON HIGH


//#define ddebug2

/* SiriCoin Address */
const String siriAddress = "0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674";

/* wifi settings */
const char* WIFI_SSID = "brisa-448561";
const char* WIFI_PASSWORD = "9xmkuiw1";

/* -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-    Advanced Settings   -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- */

/* pool url */
//const String url_pool = "http://siricoin.cu.ma/";
const String url_pool = "http://168.138.151.204/pool/";

/* -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- Do not modify from here -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- */

/* Public variables */
const char* messages = "null";
String str_difficulty = "";
String str_target = "";
String str_last_block = "";
uint32_t miner_id = 0;
uint64_t ui64_target = 0;
uint64_t nonce = 0;
uint64_t nonceLimit = 0;
uint32_t time_stamp = 0;
uint32_t job_id = 0;
unsigned char beacon_root[32];
unsigned char last_block[32];
size_t size_last_block = 32;
unsigned char target[32];
size_t size_target = 32;
unsigned char b_messagesHash[32];
unsigned char b_rewardsRecipient[20];
uint32_t mined_blocks = 0;
uint32_t recused_blocks = 0;
uint32_t jobCount = 0;
float balance = 0.0f;
boolean working = false;

void TaskMining(void *parameter);

SemaphoreHandle_t xMutex;
TaskHandle_t Task1;
TaskHandle_t Task2;

void setup() {
  /* Desable brownout detector */
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  
  pinMode( LED_BUILTIN, OUTPUT );
  digitalWrite( LED_BUILTIN, LED_ON );

  /* Start serial port for debug */
  Serial.begin(115200);
  delay(1000);
  Serial.flush();
  Serial.println();
  
  /* connect with wifi */
  SetupWifi();

  /* Decode rewardsRecipient to b_rewardsRecipient*/
  memset(b_rewardsRecipient, 0, 20);
  for (uint8_t i = 2, j = 0; j < sizeof(b_rewardsRecipient); i += 2, j++) {
    b_rewardsRecipient[j] = ((((siriAddress[i] & 0x1F) + 9) % 25) << 4) + ((siriAddress[i + 1] & 0x1F) + 9) % 25;
  }

  /* Calculate b_messagesHash */
  sph_keccak256_context ctx;
  sph_keccak256_init(&ctx);
  sph_keccak256(&ctx, messages, sizeof(messages));
  sph_keccak256_close(&ctx, b_messagesHash);

  /* Start WDT */
  esp_task_wdt_init(60, true);  // Init Watchdog timer

  /* Create Semaphore */
  xMutex = xSemaphoreCreateMutex();
  
  /* Create tasks */
  xTaskCreatePinnedToCore(TaskMining, "Task1" , 10000, NULL, 2, &Task1, 0);
  delay(500);
  xTaskCreatePinnedToCore(TaskMining, "Task2" , 10000, NULL, 2, &Task2, 1);

  digitalWrite( LED_BUILTIN, !LED_ON );
  
}

void loop() {
  
  /* login */
  if (!poolLogin(false)){
    blink_led(2);
    return;
  }
  
  /* job request */
  if (!poolGetJob()) {
    blink_led(2);
    return;
  }
  
  /* Create beaconRoot */  
  beaconRoot(beacon_root);
  
  /* blink - job received - start work */  
  blink_led(1);
  jobCount++;
  working = true;
  while (working) {
    yield();
  }
    
}

void TaskMining(void *parameter) {
  
  unsigned char local_uchar_bRoot[32];
  unsigned char uchar_nonce[32];
  uint64_t local_nonce = 0;
  uint64_t local_nonceLimit = 0; 
  uint64_t local_uint64_target = 0;

  Serial.print("Start core ");
  Serial.println(xPortGetCoreID());
  
  /* Reiniciar wdt */
  esp_task_wdt_add(NULL);

  /* Loop */
  for (;;) {
   
    /* while start working */
    while (!working) {
      esp_task_wdt_reset();
      delay(50);
    }

    /*  */
    while ( xSemaphoreTake(xMutex, portMAX_DELAY) != pdTRUE );
    memcpy(local_uchar_bRoot, beacon_root, 32);
    local_uint64_target = ui64_target;
    local_nonce = nonce + (uint64_t)xPortGetCoreID();
    local_nonceLimit = nonceLimit; 
    xSemaphoreGive(xMutex);
    memset(uchar_nonce, 0, 32);    
    
    boolean debugJob = false;
    unsigned long elapsed_time = 0;
    unsigned char proof[32];  
    unsigned long start_time = micros();
    max_micros_elapsed(start_time, 0);
    while ((local_nonce < local_nonceLimit)&&(working)) {
    
      proofOfWork(local_uchar_bRoot, local_nonce, proof);
      if ( hashToUint64(proof) < local_uint64_target ) {
        elapsed_time = micros() - start_time;        
        break;
      }
      local_nonce += 2;

      /* reset do wdt */
      if (max_micros_elapsed(micros(), 1000000)){
        yield();     
      }
    
    }

    if (working) {
      while ( xSemaphoreTake(xMutex, portMAX_DELAY) != pdTRUE );
      working = false;
      xSemaphoreGive(xMutex);
      
      /* Mined block */
      if (elapsed_time) {  
        poolSubmitJob(proof,local_nonce);
      } else {
        elapsed_time = micros() - start_time;
      }
    
      /* debug */
      float elapsed_time_s = (float)elapsed_time / 1000000.0f;
      uint32_t calcs = (uint32_t)(local_nonce - nonce);
      Serial.print("Hashrate: ");
      Serial.print(formatHashrate((float)(calcs) / elapsed_time_s));
      Serial.print(", worked " + String(elapsed_time_s) + " seconds");
      Serial.print(", "  + String(calcs) + " calculations");
      Serial.println();
      Serial.print( "Balance: ");
      Serial.print( balance );
      Serial.print( ", jobCount: ");
      Serial.print( jobCount );
      Serial.print( ", mined_blocks: ");
      Serial.print( mined_blocks );
      Serial.print( ", recused_blocks: ");
      Serial.print( recused_blocks );
      Serial.println();      
    }    
  }
}

/* login - mining.authorize */
boolean poolLogin( boolean force ) {
  static boolean poolConnected = false;
  if (force){
    poolConnected = false;
  }
  if (!poolConnected){
    String str_json_post = "{\"id\":null, \"method\": \"mining.authorize\", \"params\":[\""+siriAddress+"\"]}";
    String payload = http_post( url_pool, str_json_post );
    #ifdef ddebug2
      Serial.print("poolLogin(): ");
      Serial.println(payload);
    #endif  
    
    if ( payload == "" ) {      
      delay(3000);
      return false;
    }    
     
    /* Decodifica dados json */
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    boolean j_result = doc["result"].as<boolean>();
    if (j_result){
      unsigned long j_id = doc["id"].as<unsigned long>();
      if (j_id > 0 ){
        miner_id = (uint32_t)j_id;
        poolConnected = true;
      }
    } else {
      Serial.println("login error");
    }
    
  }
  
  poolUpdateBalance();
  
  return poolConnected;
}

boolean poolGetJob(){
  static uint8_t errorCount = 0;
  
  if (errorCount > 10 ) {
    delay(2000);
    poolLogin( true );
    errorCount = 0;
    return false;
  }
  
  String str_json_post = "{\"id\":" + String(miner_id) + ", \"method\": \"mining.subscribe\", \"params\":[\"ESP32\"]}";
  String payload = http_post( url_pool, str_json_post );
  Serial.println();
  #ifdef ddebug2
    Serial.print("poolGetJob(): ");
    Serial.println(payload);
  #endif
  
  if ( payload == "" ) {
    errorCount++;
    delay(2000);
    return false;
  }    

  DynamicJsonDocument doc(1024);
  deserializeJson(doc, payload);  
  if (!doc.containsKey("params")){
    errorCount++;
    delay(2000);
    return false;
  }
  
  nonceLimit = doc["params"][4].as<unsigned long long>();  
  if (nonceLimit < 1 ) {
    errorCount++;
    delay(2000);
    return false;
  }  
  errorCount = 0;
  
  job_id = doc["params"][0].as<unsigned long>();
  str_difficulty = doc["params"][6].as<String>();
  str_last_block = doc["params"][1].as<String>();
  str_target = doc["params"][2].as<String>();
  time_stamp = doc["params"][7].as<unsigned long>();
  nonce = doc["params"][3].as<unsigned long long>();  
  
  str_last_block = str_last_block.substring(2);
  size_last_block = str_last_block.length() / 2;
  memset(last_block, 0, sizeof(last_block));
  const char *temp_last_block = str_last_block.c_str();
  for (uint8_t i = 0, j = 0; j < size_last_block; i += 2, j++) {
    last_block[j] = ((((temp_last_block[i] & 0x1F) + 9) % 25) << 4) + ((temp_last_block[i + 1] & 0x1F) + 9) % 25;
  }

  str_target = str_target.substring(2);
  while (str_target.length() < str_last_block.length() ) {
    str_target = "0" + str_target;
  }
  memset(target, 0, sizeof(target));
  const char *temp_target = str_target.c_str();
  size_target = str_target.length() / 2;
  for (uint8_t i = 0, j = 0; j < size_target; i += 2, j++) {
    target[j] = ((((temp_target[i] & 0x1F) + 9) % 25) << 4) + ((temp_target[i + 1] & 0x1F) + 9) % 25;
  }

  ui64_target = hashToUint64(target);

  /* debug */  
  Serial.print( "Received job_id: " );
  Serial.print( job_id);
  Serial.print( ", timestamp: ");
  Serial.print( time_stamp );
  Serial.print( ", nonce: ");
  Serial.print( nonce );
  Serial.print( " to ");
  Serial.println( nonceLimit );
  #ifdef ddebug2
    Serial.print( "last_block: ");
    Serial.println( str_last_block );
    Serial.print( "target: ");
    Serial.println( str_target ); 
  #endif
  
  poolUpdateBalance();
  
  return true;
}

/* mining.submit */
void poolSubmitJob(unsigned char* prooff, uint64_t non){
  char buf_non[1 + 8 * sizeof(uint64_t)];
  sprintf(buf_non, "%llu", non);
  String str_nonce = String(buf_non);
  String str_proof = toHEX(prooff, 32);
  String str_json_post = "{\"id\":" + String(miner_id) + ", \"method\": \"mining.submit\", \"params\":[\""+siriAddress+"\","+String(job_id)+",\"0x"+str_proof+"\","+String(time_stamp)+","+str_nonce+"]}";
  #ifdef ddebug2
    Serial.print("str_json_post: ");
    Serial.println(str_json_post);
  #endif
  String payload = http_post( url_pool, str_json_post );

  DynamicJsonDocument doc(1024);
  deserializeJson(doc, payload);  
  boolean block_result = doc["result"].as<boolean>();
  if (block_result) {
    mined_blocks++;    
  } else {
    recused_blocks++;
  }

  #ifdef ddebug2
    Serial.print("poolSubmitJob(): ");
    Serial.println(payload);
  #endif  

  poolUpdateBalance();
}

void poolUpdateBalance(){
  String str_json_post = "{\"id\":" + String(miner_id) + ", \"method\": \"mining.balance\", \"params\":[\""+siriAddress+"\"]}";
  #ifdef ddebug2
    Serial.print("str_json_post: ");
    Serial.println(str_json_post);
  #endif
  String payload = http_post( url_pool, str_json_post );
  DynamicJsonDocument doc(1024);
  deserializeJson(doc, payload);  
  balance = doc["result"].as<float>();
  #ifdef ddebug2
    Serial.print("poolUpdateBalance(): ");
    Serial.println(payload);
  #endif
}

bool max_micros_elapsed(unsigned long current, unsigned long max_elapsed) {
  static unsigned long _start = 0;

  if ((current - _start) > max_elapsed) {
    _start = current;
    return true;
  }
  return false;
}

/* Conecta com wifi */
void SetupWifi() {
  yield();
  Serial.print("Connecting to: " + String(WIFI_SSID));
  WiFi.mode(WIFI_STA); 
  btStop();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(250); 
  }
  Serial.println();
  Serial.println("Successfully connected to WiFi");
  Serial.println("Local IP address: " + WiFi.localIP().toString());
  Serial.println();
}

/* Retorna http/post */
String http_post( String url_post, String data_post ) {
  String ret = "";
  boolean http_begin = false;
  WiFiClient client;
  HTTPClient http;
  http_begin = http.begin(client, url_post);
  if (http_begin){
    http.addHeader("Content-Type", "application/json");
    yield();
    int httpCode = http.POST(data_post);
    if ( httpCode == HTTP_CODE_OK) {
      ret = http.getString();
    } else {
      Serial.println(http.errorToString(httpCode));
    }
    http.end();
  }
  return ret;
}

/* Calculate proof */
void proofOfWork(unsigned char* b, uint64_t n, unsigned char* result) {
  uint8_t temp_uint256[32];
  memset(temp_uint256, 0, 32);
  temp_uint256[24] = (uint8_t)(n >> 56);
  temp_uint256[25] = (uint8_t)(n >> 48);
  temp_uint256[26] = (uint8_t)(n >> 40);
  temp_uint256[27] = (uint8_t)(n >> 32);
  temp_uint256[28] = (uint8_t)(n >> 24);
  temp_uint256[29] = (uint8_t)(n >> 16);
  temp_uint256[30] = (uint8_t)(n >> 8);
  temp_uint256[31] = (uint8_t)(n);
  sph_keccak256_context ctx;
  sph_keccak256_init(&ctx);
  sph_keccak256(&ctx, b, 32);
  sph_keccak256(&ctx, temp_uint256, 32);
  sph_keccak256_close(&ctx, result);
}

/* Calculate bRoot */
void beaconRoot(unsigned char* result) {

  uint8_t temp_uint256[32];
  memset(temp_uint256, 0, 32);
  temp_uint256[28] = (uint8_t)(time_stamp >> 24);
  temp_uint256[29] = (uint8_t)(time_stamp >> 16);
  temp_uint256[30] = (uint8_t)(time_stamp >> 8);
  temp_uint256[31] = (uint8_t)(time_stamp);

  sph_keccak256_context ctx;
  sph_keccak256_init(&ctx);
  sph_keccak256(&ctx, last_block, size_last_block);
  sph_keccak256(&ctx, temp_uint256, 32);
  sph_keccak256(&ctx, b_messagesHash, sizeof(b_messagesHash));
  sph_keccak256(&ctx, b_rewardsRecipient, sizeof(b_rewardsRecipient));
  sph_keccak256_close(&ctx, result);

}

/* Format hashrate */
String formatHashrate(float hashrate) {
  String ret = "";
  if (hashrate < 1000) {
    ret = String(hashrate, 3) + "H/s";
  } else if ( hashrate < 1000000 ) {
    ret = String(hashrate / 1000.0f, 3) + "kH/s";
  } else if ( hashrate < 1000000000 ) {
    ret = String(hashrate / 1000000.0f, 3) + "MH/s";
  } else if ( hashrate < 1000000000000 ) {
    ret = String(hashrate / 1000000000.0f, 3) + "GH/s";
  }
  return ret;
}


/* bytes to uint64_t */
uint64_t hashToUint64( const unsigned char* d ) {
  uint64_t u = (uint64_t)d[0] << 56;
  u += (uint64_t)d[1] << 48;
  u += (uint64_t)d[2] << 40;
  u += (uint64_t)d[3] << 32;
  u += (uint64_t)d[4] << 24;
  u += (uint64_t)d[5] << 16;
  u += (uint64_t)d[6] << 8;
  u += (uint64_t)d[7];
  return u;
}

/* bytes to HexString */
String toHEX( const unsigned char *d, size_t n ) {
  String r = "";
  while (n--) {
    unsigned char c = *d++;
    if ( c < 0x10 ) {
      r += "0";
    }
    r += String(c, HEX);
  }
  return r;
}

void blink_led( uint8_t c) {
  while (c--) {
    digitalWrite( LED_BUILTIN, LED_ON );
    delay(50);
    digitalWrite( LED_BUILTIN, !LED_ON );
    delay(80);
  }
}
