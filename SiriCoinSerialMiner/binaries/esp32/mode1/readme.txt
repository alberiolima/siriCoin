>> Using esptool.py (example path: /home/user/.arduino15/packages/esp32/tools/esptool_py/3.3.0/)
python3 esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB 0xe000 boot_app0.bin 0x1000 ESP32_minerSiriSerial.bootloader.bin 0x10000 ESP32_minerSiriSerial.bin 0x8000 ESP32_minerSiriSerial.partitions.bin 

>> using flash-download-tools
address file
0xe000  boot_app0.bin 
0x1000  ESP32_minerSiriSerial.bootloader.bin 
0x10000 ESP32_minerSiriSerial.bin 
0x8000  ESP32_minerSiriSerial.partitions.bin

>> job example
send (beaconRoot,target,time): 
0xdc4aa6691eab411279d87e30192f37656bfa30184adb8538b47e8a6dd92a980a,0x000000342845c05cd30200000000000000000000000000000000000000000000,30

receive(nonce,elapsed time, prof):
117596,13663912,0x000000326a773eee191da945f718e32acd56fbf59ecc8d13765650b464c32303
