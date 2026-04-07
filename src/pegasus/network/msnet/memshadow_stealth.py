"""
MEMSHADOW Protocol - Stealth/Anonymity Features

Implements stealth features for anonymous communication:
- Traffic obfuscation
- Ephemeral addresses
- Plausible deniability
- Tor/onion routing support
"""

import time
import random
import secrets
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from enum import IntEnum
import hashlib


class StealthMode(IntEnum):
    """Stealth mode levels"""
    NONE = 0
    BASIC = 1  # Basic padding and delays
    INTERMEDIATE = 2  # Traffic obfuscation
    ADVANCED = 3  # Full anonymity (Tor-like)
    MAXIMUM = 4  # Maximum anonymity + deniability


@dataclass
class OnionLayer:
    """Single layer of onion encryption"""
    encrypted_data: bytes
    next_hop: Optional[str]  # Next hop address (None for final destination)
    routing_info: bytes  # Encrypted routing information


@dataclass
class OnionMessage:
    """Onion-encrypted message"""
    layers: List[OnionLayer]
    padding: bytes  # Padding to normalize size


class TrafficObfuscator:
    """
    Obfuscate traffic patterns to resist analysis
    
    Techniques:
    - Constant-rate padding
    - Random delays
    - Dummy traffic
    - Message size normalization
    """
    
    def __init__(self, target_message_size: int = 1024):
        self.target_message_size = target_message_size
        self.dummy_traffic_rate = 0.1  # 10% dummy traffic
    
    def pad_message(self, message: bytes) -> bytes:
        """
        Pad message to target size
        
        Uses constant-rate padding to prevent size analysis.
        """
        current_size = len(message)
        if current_size >= self.target_message_size:
            return message
        
        padding_size = self.target_message_size - current_size
        padding = secrets.token_bytes(padding_size)
        
        return message + padding
    
    def add_random_delay(self, base_delay: float = 0.1) -> float:
        """
        Add random delay to message sending
        
        Uses exponential distribution to mimic real traffic patterns.
        """
        # Exponential distribution for delays
        delay = random.expovariate(1.0 / base_delay)
        return min(delay, base_delay * 10)  # Cap at 10x base delay
    
    def should_send_dummy(self) -> bool:
        """Decide if should send dummy traffic"""
        return random.random() < self.dummy_traffic_rate
    
    def generate_dummy_message(self) -> bytes:
        """Generate dummy message for traffic obfuscation"""
        size = random.randint(64, self.target_message_size)
        return secrets.token_bytes(size)


class EphemeralAddressManager:
    """
    Manage ephemeral addresses for anonymity
    
    Addresses rotate periodically to prevent tracking.
    """
    
    def __init__(self, rotation_interval: int = 3600):  # 1 hour default
        self.rotation_interval = rotation_interval
        self.current_address: Optional[str] = None
        self.address_expiry: float = 0
        self.address_secret: Optional[bytes] = None
    
    def generate_ephemeral_address(self, base_secret: bytes) -> str:
        """
        Generate ephemeral address from base secret
        
        Addresses are derived deterministically but appear random.
        """
        # Use time-based nonce for rotation
        time_slot = int(time.time() / self.rotation_interval)
        nonce = time_slot.to_bytes(8, 'big')
        
        # Derive address
        address_data = hashlib.sha256(base_secret + nonce).digest()
        address = address_data[:16].hex()  # 32-char hex address
        
        self.current_address = address
        self.address_expiry = time.time() + self.rotation_interval
        self.address_secret = base_secret
        
        return address
    
    def get_current_address(self) -> Optional[str]:
        """Get current ephemeral address, rotating if expired"""
        if not self.current_address or time.time() >= self.address_expiry:
            if self.address_secret:
                self.generate_ephemeral_address(self.address_secret)
        return self.current_address
    
    def rotate_address(self) -> str:
        """Force address rotation"""
        if not self.address_secret:
            raise ValueError("No base secret set")
        return self.generate_ephemeral_address(self.address_secret)


class DeniableEncryption:
    """
    Plausible deniability encryption
    
    Allows multiple decryption keys per ciphertext,
    enabling plausible deniability.
    """
    
    def __init__(self):
        self.hidden_layers: Dict[str, bytes] = {}
    
    def encrypt_with_deniability(
        self,
        real_message: bytes,
        decoy_message: bytes,
        real_key: bytes,
        decoy_key: bytes
    ) -> bytes:
        """
        Encrypt with deniability
        
        Creates ciphertext that can be decrypted to either:
        - Real message (with real_key)
        - Decoy message (with decoy_key)
        
        This provides plausible deniability.
        """
        # Simplified implementation
        # Real implementation would use techniques like:
        # - Multiple encryption layers
        # - Hidden volumes
        # - Steganography
        
        # Encrypt real message
        real_ciphertext = self._encrypt(real_message, real_key)
        
        # Encrypt decoy message
        decoy_ciphertext = self._encrypt(decoy_message, decoy_key)
        
        # Combine (simplified - real implementation more sophisticated)
        combined = real_ciphertext + decoy_ciphertext
        
        return combined
    
    def decrypt_with_key(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt with specific key"""
        # Simplified - would decrypt appropriate layer
        return self._decrypt(ciphertext[:len(ciphertext)//2], key)
    
    def _encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple encryption (placeholder)"""
        # Real implementation would use proper encryption
        return hashlib.sha256(data + key).digest()[:len(data)]
    
    def _decrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple decryption (placeholder)"""
        # Real implementation would use proper decryption
        return data  # Placeholder


class DHTOnionRouter:
    """
    Onion routing specifically for DHT (BitTorrent DHT) operations
    
    Since Veilid handles routing/anonymity for primary discovery,
    this provides onion routing for DHT fallback to protect:
    - DHT query privacy
    - DHT node identity
    - DHT traffic patterns
    
    Uses multi-hop routing with encrypted layers for DHT operations.
    """
    
    def __init__(self, num_hops: int = 3, dht_specific: bool = True):
        self.num_hops = num_hops
        self.dht_specific = dht_specific
        self.circuits: Dict[str, List[str]] = {}  # circuit_id -> [hop1, hop2, ...]
        self.dht_nodes: List[str] = []  # Known DHT nodes for routing
    
    def create_dht_circuit(self, dht_target: str, use_random_hops: bool = True) -> str:
        """
        Create onion routing circuit for DHT operation
        
        Args:
            dht_target: Target DHT node address
            use_random_hops: Use random DHT nodes as hops
        
        Returns:
            Circuit ID
        """
        if use_random_hops and len(self.dht_nodes) >= self.num_hops:
            # Select random DHT nodes as hops
            hops = random.sample(self.dht_nodes, self.num_hops)
        else:
            # Use provided hops or generate from DHT
            hops = []
            for _ in range(self.num_hops):
                # Would query DHT for random nodes
                hops.append(f"dht_node_{secrets.token_hex(8)}")
        
        circuit_id = secrets.token_hex(16)
        self.circuits[circuit_id] = hops + [dht_target]
        return circuit_id
    
    def create_circuit(self, hops: List[str]) -> str:
        """
        Create onion routing circuit (generic, for non-DHT use)
        
        Args:
            hops: List of hop addresses (excluding final destination)
        
        Returns:
            Circuit ID
        """
        circuit_id = secrets.token_hex(16)
        self.circuits[circuit_id] = hops
        return circuit_id
    
    def build_onion(
        self,
        message: bytes,
        destination: str,
        circuit_id: str
    ) -> OnionMessage:
        """
        Build onion-encrypted message
        
        Each layer encrypts the next hop's information.
        """
        if circuit_id not in self.circuits:
            raise ValueError("Circuit not found")
        
        hops = self.circuits[circuit_id]
        layers = []
        
        # Start with final destination
        current_data = message
        current_dest = destination
        
        # Build layers from inside out
        for hop in reversed(hops):
            # Encrypt data + next destination
            layer_data = current_data + current_dest.encode()
            encrypted = self._encrypt_layer(layer_data, hop)
            
            layers.insert(0, OnionLayer(
                encrypted_data=encrypted,
                next_hop=hop,
                routing_info=b''  # Would contain encrypted routing info
            ))
            
            current_data = encrypted
            current_dest = hop
        
        # Add padding to normalize size
        padding = secrets.token_bytes(1024 - len(message) % 1024)
        
        return OnionMessage(layers=layers, padding=padding)
    
    def peel_onion_layer(self, layer: OnionLayer, hop_key: bytes) -> Tuple[bytes, Optional[str]]:
        """
        Peel one layer of onion encryption
        
        Each hop peels one layer to reveal next hop.
        """
        decrypted = self._decrypt_layer(layer.encrypted_data, hop_key)
        
        # Extract next destination (last part)
        # Simplified - real implementation more sophisticated
        next_dest = None
        if len(decrypted) > 64:  # Assuming destination is last 64 bytes
            next_dest = decrypted[-64:].decode('utf-8', errors='ignore')
            data = decrypted[:-64]
        else:
            data = decrypted
        
        return data, next_dest
    
    def _encrypt_layer(self, data: bytes, hop: str) -> bytes:
        """Encrypt layer (placeholder)"""
        # Real implementation would use hop's public key
        key = hashlib.sha256(hop.encode()).digest()
        return hashlib.sha256(data + key).digest()[:len(data)]
    
    def _decrypt_layer(self, data: bytes, key: bytes) -> bytes:
        """Decrypt layer (placeholder)"""
        return data  # Placeholder


class StealthManager:
    """
    Main stealth/anonymity manager
    
    Coordinates all stealth features.
    Note: Veilid handles primary routing/anonymity.
    Onion routing here is specifically for DHT fallback operations.
    """
    
    def __init__(self, stealth_mode: StealthMode = StealthMode.BASIC, use_dht_onion: bool = True):
        self.stealth_mode = stealth_mode
        self.obfuscator = TrafficObfuscator()
        self.address_manager = EphemeralAddressManager()
        self.deniable_enc = DeniableEncryption()
        # DHT-specific onion routing (Veilid handles primary routing)
        self.dht_onion_router = DHTOnionRouter(dht_specific=True) if use_dht_onion else None
        # Generic onion router for other use cases (if needed)
        self.onion_router = None if stealth_mode < StealthMode.ADVANCED else None
    
    def prepare_message(self, message: bytes) -> bytes:
        """
        Prepare message with stealth features
        
        Applies padding, obfuscation, etc. based on stealth mode.
        """
        if self.stealth_mode >= StealthMode.BASIC:
            message = self.obfuscator.pad_message(message)
        
        return message
    
    def get_send_delay(self) -> float:
        """Get delay before sending (for obfuscation)"""
        if self.stealth_mode >= StealthMode.INTERMEDIATE:
            return self.obfuscator.add_random_delay()
        return 0.0
    
    def get_current_address(self) -> Optional[str]:
        """Get current ephemeral address"""
        if self.stealth_mode >= StealthMode.INTERMEDIATE:
            return self.address_manager.get_current_address()
        return None
    
    def should_send_dummy(self) -> bool:
        """Check if should send dummy traffic"""
        if self.stealth_mode >= StealthMode.INTERMEDIATE:
            return self.obfuscator.should_send_dummy()
        return False
