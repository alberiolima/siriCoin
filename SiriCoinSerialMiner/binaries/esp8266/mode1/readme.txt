>> using flash-download-tools
address file
0x0     minerSiriSerial.ino.bin 

>> Using upload.py 
(path for python3: /home/user/.arduino15/packages/esp8266/tools/python3/3.7.2-post1/ )
(path for upload.py: /home/user/.arduino15/packages/esp8266/hardware/esp8266/3.0.2/tools/
python3 -I upload.py --chip esp8266 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash 0x0 minerSiriSerial.ino.bin 

>> job example
send (beaconRoot,target): 
0xdc4aa6691eab411279d87e30192f37656bfa30184adb8538b47e8a6dd92a980a,0x000000342845c05cd30200000000000000000000000000000000000000000000

receive(nonce,elapsed time, prof):
117596,13663912,0x000000326a773eee191da945f718e32acd56fbf59ecc8d13765650b464c32303
