import random
import os
from pathlib import Path

class NetworkRotator:
    def __init__(self, config_dir: Path):
        self.configs = list(config_dir.glob("*.conf"))
        
    def get_random_config(self) -> str:
        return str(random.choice(self.configs))
