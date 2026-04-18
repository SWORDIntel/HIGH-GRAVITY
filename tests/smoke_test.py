import socket
import sys

def check_proxy():
    port = 9999
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        print("[+] Proxy is alive on port 9999")
        sys.exit(0)
    else:
        print("[-] Proxy is NOT alive on port 9999")
        sys.exit(1)

if __name__ == "__main__":
    check_proxy()
