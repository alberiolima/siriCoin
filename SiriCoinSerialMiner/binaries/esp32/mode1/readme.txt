
>> Using esptool.py (example path: /home/user/.arduino15/packages/esp32/tools/esptool_py/3.3.0/)
python3 esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB 0xe000 boot_app0.bin 0x1000 minerSiriSerial.ino.bootloader.bin 0x10000 minerSiriSerial.ino.bin 0x8000 minerSiriSerial.ino.partitions.bin 

>> using flash-download-tools
address file
0xe000  boot_app0.bin 
0x1000  minerSiriSerial.ino.bootloader.bin 
0x10000 minerSiriSerial.ino.bin 
0x8000  minerSiriSerial.ino.partitions.bin
