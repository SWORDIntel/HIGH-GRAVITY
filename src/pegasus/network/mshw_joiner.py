import sys
# Ensure msnet is in the path for imports
sys.path.append("/media/john/NVME_STORAGE4/HIGH-GRAVITY/msnet/python")

from memshadow.memshadow_handshake import MemShadowHandshake
from memshadow.memshadow_gossip import MemShadowGossip

def join_mshw_network(node_id="HG-NODE"):
    print(f"[*] Initializing MEMSHADOW node: {node_id}")
    try:
        handshake = MemShadowHandshake(node_id=node_id)
        gossip = MemShadowGossip(node_id=node_id)
        
        # Perform handshake
        if handshake.perform():
            print("[+] Handshake successful. Joining MSHW DHT track.")
            gossip.start()
            return True
        else:
            print("[-] Handshake failed.")
            return False
    except Exception as e:
        print(f"[-] MSHW Init Error: {e}")
        return False

if __name__ == "__main__":
    join_mshw_network()
