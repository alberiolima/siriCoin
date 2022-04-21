import socket
import sys

PORT = 9999
HOST = "192.168.1.36"
    
# Create a socket (SOCK_STREAM means a TCP socket)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    # Connect to gateway and send request job
    sock.connect((HOST, PORT))
    sock.sendall(bytes("$REQJOB,0x0E9b419F7Cd861bf86230b124229F9a1b6FF9674\n", "utf-8"))

    # Receive data from the server and shut down
    received = str(sock.recv(300), "utf-8")
    print(f"jobrecv: {received}")
