import sys
import time
from src.pegasus.network.msnet.peer_manager import MemshadowPeerManager
from src.pegasus.network.msnet.memshadow_gossip import GossipProtocol

def join_mshw_network(node_id="HG-NODE"):
    print(f"[*] Initializing MEMSHADOW node: {node_id}")
    try:
        # Corrected arguments for MSNET v3.0
        peer_manager = MemshadowPeerManager(peer_id=node_id)
        gossip = GossipProtocol(node_id=node_id, address="127.0.0.1", port=8901)
        
        print("[+] Pegasus MSHW Node initialized. Starting gossip discovery...")
        return True
    except Exception as e:
        print(f"[-] MSHW Init Error: {e}")
        return False

if __name__ == "__main__":
    join_mshw_network()
