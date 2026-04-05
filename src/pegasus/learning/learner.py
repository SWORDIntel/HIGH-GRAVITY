import time
import json
from pathlib import Path
from tools.integration.pegasus.learning.train import train_step  # Conceptually importing from the clone

class PegasusLearner:
    def __init__(self, gsl):
        self.gsl = gsl
        
    def ingest_proxy_flow(self, request: dict, response: bytes):
        """Processes request/response flow and triggers autonomous training."""
        flow_data = {
            "prompt": json.dumps(request.get("messages", [])),
            "response": response.decode(errors="ignore"),
            "timestamp": time.time()
        }
        # Ingest directly into the training loop
        try:
            train_step(flow_data)
        except Exception as e:
            pass # Non-blocking for production traffic
