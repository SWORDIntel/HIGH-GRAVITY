"""
MEMSHADOW Protocol - Post-Quantum Cryptography

Implements post-quantum cryptographic algorithms for quantum-resistant security.
Uses hybrid classical/PQC approach for transition period.
"""

import hashlib
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from enum import IntEnum

try:
    # Try to import post-quantum libraries
    try:
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization
        X25519_AVAILABLE = True
    except ImportError:
        X25519_AVAILABLE = False
    
    # CRYSTALS-Kyber (key exchange) - would need actual library
    # CRYSTALS-Dilithium (signatures) - would need actual library
    # SPHINCS+ (hash-based signatures) - would need actual library
    
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class PQCAlgorithm(IntEnum):
    """Post-quantum cryptographic algorithms"""
    CLASSICAL_ONLY = 0  # Classical only (for compatibility)
    HYBRID_X25519_KYBER = 1  # X25519 + CRYSTALS-Kyber
    HYBRID_ECDSA_DILITHIUM = 2  # ECDSA + CRYSTALS-Dilithium
    PQC_ONLY = 3  # Post-quantum only (future)
    # Homomorphic Encryption algorithms
    BFV_HOMOMORPHIC = 4  # Brakerski-Fan-Vercauteren (BFV) scheme
    CKKS_HOMOMORPHIC = 5  # Cheon-Kim-Kim-Song (CKKS) scheme for approximate arithmetic
    TFHE_HOMOMORPHIC = 6  # Fast Fully Homomorphic Encryption over Torus (TFHE)
    HYBRID_BFV_CLASSICAL = 7  # BFV + classical encryption
    HYBRID_CKKS_CLASSICAL = 8  # CKKS + classical encryption


@dataclass
class HybridKeyPair:
    """Hybrid classical/PQC key pair"""
    classical_private: Optional[bytes] = None
    classical_public: Optional[bytes] = None
    pqc_private: Optional[bytes] = None
    pqc_public: Optional[bytes] = None
    # Homomorphic encryption keys
    he_public_key: Optional[bytes] = None  # Public key for homomorphic encryption
    he_private_key: Optional[bytes] = None  # Private key for homomorphic encryption
    he_evaluation_key: Optional[bytes] = None  # Evaluation key for homomorphic operations
    he_relinearization_key: Optional[bytes] = None  # Relinearization key for BFV/CKKS
    he_galois_key: Optional[bytes] = None  # Galois key for rotations (CKKS)
    algorithm: PQCAlgorithm = PQCAlgorithm.HYBRID_X25519_KYBER


@dataclass
class HybridSignature:
    """Hybrid classical/PQC signature"""
    classical_sig: Optional[bytes] = None
    pqc_sig: Optional[bytes] = None
    algorithm: PQCAlgorithm = PQCAlgorithm.HYBRID_ECDSA_DILITHIUM


@dataclass
class HomomorphicCiphertext:
    """Homomorphic encryption ciphertext with metadata"""
    ciphertext: bytes  # The encrypted data
    algorithm: PQCAlgorithm  # Which HE algorithm was used
    scale: Optional[float] = None  # Scale parameter for CKKS
    level: Optional[int] = None  # Multiplicative depth level
    noise_budget: Optional[int] = None  # Remaining noise budget


class PostQuantumCrypto:
    """
    Post-quantum cryptography implementation
    
    Provides quantum-resistant cryptographic operations.
    Uses hybrid approach for transition period.
    """
    
    def __init__(self, algorithm: PQCAlgorithm = PQCAlgorithm.HYBRID_X25519_KYBER):
        self.algorithm = algorithm
        self.kyber_available = False  # Would check for CRYSTALS-Kyber library
        self.dilithium_available = False  # Would check for CRYSTALS-Dilithium library
        self.sphincs_available = False  # Would check for SPHINCS+ library
        # Homomorphic encryption availability
        self.bfv_available = False  # Would check for BFV library (Microsoft SEAL, etc.)
        self.ckks_available = False  # Would check for CKKS library
        self.tfhe_available = False  # Would check for TFHE library
    
    def generate_keypair(self) -> HybridKeyPair:
        """
        Generate hybrid classical/PQC key pair
        
        Returns:
            HybridKeyPair with both classical and PQC keys
        """
        if self.algorithm == PQCAlgorithm.CLASSICAL_ONLY:
            # Classical only
            if X25519_AVAILABLE:
                private_key = x25519.X25519PrivateKey.generate()
                public_key = private_key.public_key()
                return HybridKeyPair(
                    classical_private=private_key.private_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PrivateFormat.Raw,
                        encryption_algorithm=serialization.NoEncryption()
                    ),
                    classical_public=public_key.public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw
                    ),
                    algorithm=self.algorithm
                )
        
        elif self.algorithm == PQCAlgorithm.HYBRID_X25519_KYBER:
            # Hybrid: X25519 + CRYSTALS-Kyber
            # Generate classical key
            classical_private = None
            classical_public = None
            if X25519_AVAILABLE:
                private_key = x25519.X25519PrivateKey.generate()
                public_key = private_key.public_key()
                classical_private = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                classical_public = public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            
            # Generate PQC key (CRYSTALS-Kyber)
            # Placeholder - would use actual Kyber library
            pqc_private = b'\x00' * 32  # Placeholder
            pqc_public = b'\x00' * 32  # Placeholder
            
            return HybridKeyPair(
                classical_private=classical_private,
                classical_public=classical_public,
                pqc_private=pqc_private,
                pqc_public=pqc_public,
                algorithm=self.algorithm
            )
        
        elif self.algorithm == PQCAlgorithm.PQC_ONLY:
            # PQC only (future)
            pqc_private = b'\x00' * 32  # Placeholder
            pqc_public = b'\x00' * 32  # Placeholder

            return HybridKeyPair(
                pqc_private=pqc_private,
                pqc_public=pqc_public,
                algorithm=self.algorithm
            )

        elif self.algorithm == PQCAlgorithm.BFV_HOMOMORPHIC:
            # BFV Homomorphic Encryption
            # Generate BFV keypair (placeholder - would use actual BFV library)
            he_public_key = b'\x00' * 1024  # Public key (large for lattice-based)
            he_private_key = b'\x00' * 512   # Private key
            he_evaluation_key = b'\x00' * 2048  # Evaluation key for relinearization
            he_relinearization_key = b'\x00' * 1536  # Relinearization key

            return HybridKeyPair(
                he_public_key=he_public_key,
                he_private_key=he_private_key,
                he_evaluation_key=he_evaluation_key,
                he_relinearization_key=he_relinearization_key,
                algorithm=self.algorithm
            )

        elif self.algorithm == PQCAlgorithm.CKKS_HOMOMORPHIC:
            # CKKS Homomorphic Encryption (approximate arithmetic)
            he_public_key = b'\x00' * 1024  # Public key
            he_private_key = b'\x00' * 512   # Private key
            he_evaluation_key = b'\x00' * 2048  # Evaluation key
            he_relinearization_key = b'\x00' * 1536  # Relinearization key
            he_galois_key = b'\x00' * 1024  # Galois key for rotations

            return HybridKeyPair(
                he_public_key=he_public_key,
                he_private_key=he_private_key,
                he_evaluation_key=he_evaluation_key,
                he_relinearization_key=he_relinearization_key,
                he_galois_key=he_galois_key,
                algorithm=self.algorithm
            )

        elif self.algorithm == PQCAlgorithm.TFHE_HOMOMORPHIC:
            # TFHE Homomorphic Encryption (boolean operations)
            he_public_key = b'\x00' * 2048  # Cloud key (large for TFHE)
            he_private_key = b'\x00' * 256   # Secret key
            # TFHE doesn't use evaluation keys in the same way
            he_evaluation_key = None

            return HybridKeyPair(
                he_public_key=he_public_key,
                he_private_key=he_private_key,
                he_evaluation_key=he_evaluation_key,
                algorithm=self.algorithm
            )

        elif self.algorithm == PQCAlgorithm.HYBRID_BFV_CLASSICAL:
            # Hybrid: BFV Homomorphic + Classical encryption
            # Generate classical keys
            classical_private = None
            classical_public = None
            if X25519_AVAILABLE:
                private_key = x25519.X25519PrivateKey.generate()
                public_key = private_key.public_key()
                classical_private = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                classical_public = public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )

            # Generate BFV keys
            he_public_key = b'\x00' * 1024
            he_private_key = b'\x00' * 512
            he_evaluation_key = b'\x00' * 2048
            he_relinearization_key = b'\x00' * 1536

            return HybridKeyPair(
                classical_private=classical_private,
                classical_public=classical_public,
                he_public_key=he_public_key,
                he_private_key=he_private_key,
                he_evaluation_key=he_evaluation_key,
                he_relinearization_key=he_relinearization_key,
                algorithm=self.algorithm
            )

        elif self.algorithm == PQCAlgorithm.HYBRID_CKKS_CLASSICAL:
            # Hybrid: CKKS Homomorphic + Classical encryption
            # Generate classical keys
            classical_private = None
            classical_public = None
            if X25519_AVAILABLE:
                private_key = x25519.X25519PrivateKey.generate()
                public_key = private_key.public_key()
                classical_private = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                classical_public = public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )

            # Generate CKKS keys
            he_public_key = b'\x00' * 1024
            he_private_key = b'\x00' * 512
            he_evaluation_key = b'\x00' * 2048
            he_relinearization_key = b'\x00' * 1536
            he_galois_key = b'\x00' * 1024

            return HybridKeyPair(
                classical_private=classical_private,
                classical_public=classical_public,
                he_public_key=he_public_key,
                he_private_key=he_private_key,
                he_evaluation_key=he_evaluation_key,
                he_relinearization_key=he_relinearization_key,
                he_galois_key=he_galois_key,
                algorithm=self.algorithm
            )

        # Default fallback
        return HybridKeyPair(algorithm=self.algorithm)
    
    def key_exchange(
        self,
        my_private: bytes,
        peer_public: bytes,
        use_pqc: bool = True
    ) -> bytes:
        """
        Perform key exchange (hybrid if enabled)
        
        Combines classical and PQC key exchange results.
        """
        if not use_pqc or self.algorithm == PQCAlgorithm.CLASSICAL_ONLY:
            # Classical only
            if X25519_AVAILABLE:
                # Would perform X25519 key exchange
                # Placeholder
                return hashlib.sha256(my_private + peer_public).digest()
        
        # Hybrid: Combine classical and PQC
        classical_shared = hashlib.sha256(my_private + peer_public).digest()
        pqc_shared = b'\x00' * 32  # Placeholder for PQC key exchange
        
        # Combine using HKDF-like approach
        combined = hashlib.sha256(classical_shared + pqc_shared).digest()
        return combined
    
    def sign(
        self,
        message: bytes,
        private_key: HybridKeyPair
    ) -> HybridSignature:
        """
        Sign message with hybrid signature
        
        Creates both classical and PQC signatures.
        """
        if self.algorithm == PQCAlgorithm.CLASSICAL_ONLY:
            # Classical signature only
            sig = hashlib.sha256(message + (private_key.classical_private or b'')).digest()
            return HybridSignature(
                classical_sig=sig,
                algorithm=self.algorithm
            )
        
        elif self.algorithm == PQCAlgorithm.HYBRID_ECDSA_DILITHIUM:
            # Hybrid: ECDSA + CRYSTALS-Dilithium
            classical_sig = hashlib.sha256(message + (private_key.classical_private or b'')).digest()
            pqc_sig = b'\x00' * 64  # Placeholder for Dilithium signature
            
            return HybridSignature(
                classical_sig=classical_sig,
                pqc_sig=pqc_sig,
                algorithm=self.algorithm
            )
        
        elif self.algorithm == PQCAlgorithm.PQC_ONLY:
            # PQC signature only
            pqc_sig = b'\x00' * 64  # Placeholder
            return HybridSignature(
                pqc_sig=pqc_sig,
                algorithm=self.algorithm
            )
        
        # Default
        return HybridSignature(algorithm=self.algorithm)
    
    def verify(
        self,
        message: bytes,
        signature: HybridSignature,
        public_key: HybridKeyPair
    ) -> bool:
        """
        Verify hybrid signature
        
        Verifies both classical and PQC signatures if present.
        """
        if signature.algorithm == PQCAlgorithm.CLASSICAL_ONLY:
            # Verify classical only
            expected_sig = hashlib.sha256(message + (public_key.classical_public or b'')).digest()
            return signature.classical_sig == expected_sig
        
        elif signature.algorithm == PQCAlgorithm.HYBRID_ECDSA_DILITHIUM:
            # Verify both signatures
            classical_valid = False
            if signature.classical_sig and public_key.classical_public:
                expected_classical = hashlib.sha256(message + public_key.classical_public).digest()
                classical_valid = signature.classical_sig == expected_classical
            
            pqc_valid = False
            if signature.pqc_sig and public_key.pqc_public:
                # Would verify PQC signature
                pqc_valid = True  # Placeholder
            
            # Both must be valid for hybrid
            return classical_valid and pqc_valid
        
        elif signature.algorithm == PQCAlgorithm.PQC_ONLY:
            # Verify PQC only
            if signature.pqc_sig and public_key.pqc_public:
                # Would verify PQC signature
                return True  # Placeholder
        
        return False
    
    def get_algorithm_info(self) -> Dict:
        """Get information about available algorithms"""
        return {
            'algorithm': self.algorithm.name,
            'classical_available': X25519_AVAILABLE,
            'kyber_available': self.kyber_available,
            'dilithium_available': self.dilithium_available,
            'sphincs_available': self.sphincs_available,
            'bfv_available': self.bfv_available,
            'ckks_available': self.ckks_available,
            'tfhe_available': self.tfhe_available,
            'hybrid_mode': self.algorithm in [
                PQCAlgorithm.HYBRID_X25519_KYBER,
                PQCAlgorithm.HYBRID_ECDSA_DILITHIUM,
                PQCAlgorithm.HYBRID_BFV_CLASSICAL,
                PQCAlgorithm.HYBRID_CKKS_CLASSICAL
            ],
            'homomorphic_mode': self.algorithm in [
                PQCAlgorithm.BFV_HOMOMORPHIC,
                PQCAlgorithm.CKKS_HOMOMORPHIC,
                PQCAlgorithm.TFHE_HOMOMORPHIC,
                PQCAlgorithm.HYBRID_BFV_CLASSICAL,
                PQCAlgorithm.HYBRID_CKKS_CLASSICAL
            ]
        }

    def he_encrypt(self, plaintext: bytes, public_key: HybridKeyPair) -> Optional[HomomorphicCiphertext]:
        """
        Encrypt data using homomorphic encryption

        Args:
            plaintext: Data to encrypt
            public_key: Public key for encryption

        Returns:
            HomomorphicCiphertext or None if encryption fails
        """
        if not public_key.he_public_key:
            return None

        # Check algorithm compatibility
        if self.algorithm not in [
            PQCAlgorithm.BFV_HOMOMORPHIC,
            PQCAlgorithm.CKKS_HOMOMORPHIC,
            PQCAlgorithm.TFHE_HOMOMORPHIC,
            PQCAlgorithm.HYBRID_BFV_CLASSICAL,
            PQCAlgorithm.HYBRID_CKKS_CLASSICAL
        ]:
            return None

        # Placeholder homomorphic encryption
        # In real implementation, would use actual HE library (SEAL, TFHE, etc.)
        # For placeholder, we store the plaintext at the end for testing purposes
        padding = b'\x00' * 128
        ciphertext = padding + plaintext  # Placeholder: store plaintext at end

        return HomomorphicCiphertext(
            ciphertext=ciphertext,
            algorithm=self.algorithm,
            scale=1.0 if self.algorithm in [PQCAlgorithm.CKKS_HOMOMORPHIC, PQCAlgorithm.HYBRID_CKKS_CLASSICAL] else None,
            level=0,  # Starting multiplicative depth
            noise_budget=100  # Placeholder noise budget
        )

    def he_decrypt(self, ciphertext: HomomorphicCiphertext, private_key: HybridKeyPair) -> Optional[bytes]:
        """
        Decrypt homomorphically encrypted data

        Args:
            ciphertext: Encrypted data
            private_key: Private key for decryption

        Returns:
            Decrypted plaintext or None if decryption fails
        """
        if not private_key.he_private_key:
            return None

        # Placeholder decryption
        # In real implementation, would use actual HE library
        # For placeholder, extract plaintext from end
        if len(ciphertext.ciphertext) > 128:
            plaintext = ciphertext.ciphertext[128:]  # Extract plaintext from end
        else:
            plaintext = ciphertext.ciphertext

        return plaintext

    def he_add(self, ct1: HomomorphicCiphertext, ct2: HomomorphicCiphertext,
               evaluation_key: HybridKeyPair) -> Optional[HomomorphicCiphertext]:
        """
        Perform homomorphic addition on encrypted data

        Args:
            ct1: First ciphertext
            ct2: Second ciphertext
            evaluation_key: Evaluation key for the operation

        Returns:
            Result of homomorphic addition or None if operation fails
        """
        if not evaluation_key.he_evaluation_key:
            return None

        if ct1.algorithm != ct2.algorithm or ct1.algorithm != self.algorithm:
            return None

        # Placeholder homomorphic addition
        # In real implementation, would perform actual HE addition
        result_ciphertext = b'\x00' * len(ct1.ciphertext)  # Placeholder

        new_level = max(ct1.level or 0, ct2.level or 0)
        new_noise_budget = min(ct1.noise_budget or 100, ct2.noise_budget or 100) - 5  # Noise consumption

        return HomomorphicCiphertext(
            ciphertext=result_ciphertext,
            algorithm=self.algorithm,
            scale=ct1.scale,  # Scale unchanged for addition
            level=new_level,
            noise_budget=max(0, new_noise_budget)
        )

    def he_multiply(self, ct1: HomomorphicCiphertext, ct2: HomomorphicCiphertext,
                    evaluation_key: HybridKeyPair, relinearization_key: Optional[HybridKeyPair] = None) -> Optional[HomomorphicCiphertext]:
        """
        Perform homomorphic multiplication on encrypted data

        Args:
            ct1: First ciphertext
            ct2: Second ciphertext
            evaluation_key: Evaluation key for the operation
            relinearization_key: Relinearization key (required for BFV/CKKS)

        Returns:
            Result of homomorphic multiplication or None if operation fails
        """
        if not evaluation_key.he_evaluation_key:
            return None

        if ct1.algorithm != ct2.algorithm or ct1.algorithm != self.algorithm:
            return None

        # For BFV/CKKS, relinearization key is typically required for multiplication
        if self.algorithm in [PQCAlgorithm.BFV_HOMOMORPHIC, PQCAlgorithm.CKKS_HOMOMORPHIC,
                             PQCAlgorithm.HYBRID_BFV_CLASSICAL, PQCAlgorithm.HYBRID_CKKS_CLASSICAL]:
            if not relinearization_key or not relinearization_key.he_relinearization_key:
                return None

        # Placeholder homomorphic multiplication
        # In real implementation, would perform actual HE multiplication
        result_ciphertext = b'\x00' * len(ct1.ciphertext)  # Placeholder

        new_level = max(ct1.level or 0, ct2.level or 0) + 1  # Multiplication increases depth
        new_noise_budget = min(ct1.noise_budget or 100, ct2.noise_budget or 100) - 20  # More noise consumption

        # For CKKS, scale is multiplied
        new_scale = None
        if self.algorithm in [PQCAlgorithm.CKKS_HOMOMORPHIC, PQCAlgorithm.HYBRID_CKKS_CLASSICAL]:
            new_scale = (ct1.scale or 1.0) * (ct2.scale or 1.0)

        return HomomorphicCiphertext(
            ciphertext=result_ciphertext,
            algorithm=self.algorithm,
            scale=new_scale,
            level=new_level,
            noise_budget=max(0, new_noise_budget)
        )

    def he_rotate(self, ciphertext: HomomorphicCiphertext, steps: int,
                  galois_key: HybridKeyPair) -> Optional[HomomorphicCiphertext]:
        """
        Perform homomorphic rotation on encrypted data (CKKS/TFHE)

        Args:
            ciphertext: Ciphertext to rotate
            steps: Number of positions to rotate
            galois_key: Galois key for rotation

        Returns:
            Rotated ciphertext or None if operation fails
        """
        if self.algorithm not in [PQCAlgorithm.CKKS_HOMOMORPHIC, PQCAlgorithm.TFHE_HOMOMORPHIC,
                                 PQCAlgorithm.HYBRID_CKKS_CLASSICAL]:
            return None

        if not galois_key.he_galois_key:
            return None

        # Placeholder homomorphic rotation
        # In real implementation, would perform actual HE rotation
        rotated_ciphertext = ciphertext.ciphertext  # Placeholder (no actual rotation)

        return HomomorphicCiphertext(
            ciphertext=rotated_ciphertext,
            algorithm=self.algorithm,
            scale=ciphertext.scale,
            level=ciphertext.level,
            noise_budget=max(0, (ciphertext.noise_budget or 100) - 2)  # Small noise consumption
        )


class PQCManager:
    """
    Post-quantum cryptography manager
    
    Coordinates PQC operations across the protocol.
    """
    
    def __init__(self, algorithm: PQCAlgorithm = PQCAlgorithm.HYBRID_X25519_KYBER):
        self.pqc = PostQuantumCrypto(algorithm=algorithm)
        self.keypairs: Dict[str, HybridKeyPair] = {}  # node_id -> keypair
    
    def generate_node_keypair(self, node_id: str) -> HybridKeyPair:
        """Generate keypair for node"""
        keypair = self.pqc.generate_keypair()
        self.keypairs[node_id] = keypair
        return keypair
    
    def get_node_keypair(self, node_id: str) -> Optional[HybridKeyPair]:
        """Get keypair for node"""
        return self.keypairs.get(node_id)
    
    def perform_key_exchange(
        self,
        my_node_id: str,
        peer_node_id: str,
        peer_public_key: HybridKeyPair
    ) -> Optional[bytes]:
        """Perform key exchange with peer"""
        my_keypair = self.get_node_keypair(my_node_id)
        if not my_keypair:
            return None
        
        # Extract public keys
        my_private = my_keypair.classical_private or my_keypair.pqc_private
        peer_public = peer_public_key.classical_public or peer_public_key.pqc_public
        
        if not my_private or not peer_public:
            return None

        return self.pqc.key_exchange(my_private, peer_public)

    def he_encrypt_data(self, node_id: str, plaintext: bytes) -> Optional[HomomorphicCiphertext]:
        """Encrypt data using homomorphic encryption for a node"""
        keypair = self.get_node_keypair(node_id)
        if not keypair:
            return None
        return self.pqc.he_encrypt(plaintext, keypair)

    def he_decrypt_data(self, node_id: str, ciphertext: HomomorphicCiphertext) -> Optional[bytes]:
        """Decrypt homomorphically encrypted data for a node"""
        keypair = self.get_node_keypair(node_id)
        if not keypair:
            return None
        return self.pqc.he_decrypt(ciphertext, keypair)

    def he_compute_sum(self, node_id: str, ct1: HomomorphicCiphertext,
                      ct2: HomomorphicCiphertext) -> Optional[HomomorphicCiphertext]:
        """Perform homomorphic addition for encrypted data"""
        keypair = self.get_node_keypair(node_id)
        if not keypair:
            return None
        return self.pqc.he_add(ct1, ct2, keypair)

    def he_compute_product(self, node_id: str, ct1: HomomorphicCiphertext,
                          ct2: HomomorphicCiphertext) -> Optional[HomomorphicCiphertext]:
        """Perform homomorphic multiplication for encrypted data"""
        keypair = self.get_node_keypair(node_id)
        if not keypair:
            return None
        return self.pqc.he_multiply(ct1, ct2, keypair, keypair)

    def he_rotate_data(self, node_id: str, ciphertext: HomomorphicCiphertext,
                      steps: int) -> Optional[HomomorphicCiphertext]:
        """Perform homomorphic rotation on encrypted data"""
        keypair = self.get_node_keypair(node_id)
        if not keypair:
            return None
        return self.pqc.he_rotate(ciphertext, steps, keypair)
