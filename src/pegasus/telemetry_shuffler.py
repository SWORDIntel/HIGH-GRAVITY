import random
import time

class TelemetryShuffler:
    @staticmethod
    def shuffle(data: dict) -> dict:
        """Injects entropy into telemetry payloads."""
        # Random jitter to prevent timing profile
        time.sleep(random.uniform(0.01, 0.05))
        
        # Injects dummy metadata keys to break pattern matching
        data["hg_entropy"] = random.getrandbits(32)
        data["pegasus_node"] = "isolated-cluster-x9"
        return data
