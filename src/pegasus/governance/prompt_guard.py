"""
Prompt Guard - Defense against Prompt Injection and Payload Validation

This module implements:
1. Strict schema validation for UFP (Universal Format Payload) payloads to prevent untrusted strings from being injected into `system_prompts`.
2. A 'Guard Agent' or compliance policy layer that performs safety checks on modifications to `CLAUDE.md` or system instructions before they are loaded into the runtime.
"""

import json
import logging
import re
import functools
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PromptGuard")

# Common prompt injection patterns
INJECTION_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"bypass", re.IGNORECASE),
    re.compile(r"do not follow", re.IGNORECASE),
    re.compile(r"forget", re.IGNORECASE),
    re.compile(r"DAN\s*mode", re.IGNORECASE),
    re.compile(r"developer\s*mode", re.IGNORECASE),
]

@dataclass
class UFPPayload:
    """Universal Format Payload (UFP) Schema."""
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_bytes(cls, data: Union[bytes, str]) -> Optional['UFPPayload']:
        """Parses a UFPPayload from bytes or JSON string safely."""
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            parsed = json.loads(data)
            return cls(
                role=parsed.get('role', 'user'),
                content=parsed.get('content', ''),
                metadata=parsed.get('metadata')
            )
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse payload: {e}")
            return None

    def validate(self) -> bool:
        """
        Validates the UFP Payload schema strictly.
        """
        if not isinstance(self.role, str) or self.role not in ["user", "system", "assistant"]:
            logger.warning(f"Validation failed: Invalid role '{self.role}'.")
            return False
        
        if not isinstance(self.content, str) or not self.content.strip():
            logger.warning("Validation failed: Content is empty or not a string.")
            return False
            
        if self.metadata is not None and not isinstance(self.metadata, dict):
            logger.warning("Validation failed: Metadata must be a dictionary.")
            return False

        # Additional strict validation for system payloads to prevent injection
        if self.role == "system":
            if GuardAgent.contains_injection(self.content):
                logger.warning("Validation failed: Potential prompt injection detected in system payload!")
                return False
                
        return True


class GuardAgent:
    """
    Guard Agent / Compliance Policy Layer.
    Responsible for checking modifications to CLAUDE.md or system instructions
    before they are loaded into the runtime.
    """

    @staticmethod
    def contains_injection(text: str) -> bool:
        """Checks for common prompt injection patterns."""
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                logger.warning(f"Prompt injection pattern detected: {pattern.pattern}")
                return True
        return False

    def validate_system_instructions(self, source_name: str, new_content: str) -> bool:
        """
        Performs safety checks on modifications to CLAUDE.md or system instructions 
        before they are loaded into the runtime.
        """
        logger.info(f"Guard Agent: Analyzing modifications for {source_name}")
        
        # 1. Size constraint check (e.g., abnormally large system prompt)
        max_size = 50000
        if len(new_content) > max_size:
            logger.error(f"Guard Agent [{source_name}]: Rejected modification - Content exceeds maximum size of {max_size} characters.")
            return False

        # 2. Injection pattern check
        if self.contains_injection(new_content):
            logger.error(f"Guard Agent [{source_name}]: Rejected modification - Injection patterns detected in the system instructions.")
            return False

        # 3. Check for specific dangerous tags or system-level overrides
        dangerous_tags = ["<|system|>", "<|endoftext|>", "<|user|>"]
        for tag in dangerous_tags:
            if tag in new_content:
                logger.error(f"Guard Agent [{source_name}]: Rejected modification - Dangerous control tags detected ({tag}).")
                return False

        logger.info(f"Guard Agent [{source_name}]: Modification passed safety checks.")
        return True

    def sanitize_ufp_payload(self, payload_dict: Dict[str, Any]) -> Optional[UFPPayload]:
        """
        Strictly validates and returns a UFPPayload from an untrusted dictionary.
        Returns None if the payload fails schema or safety validation.
        """
        try:
            payload = UFPPayload(
                role=payload_dict.get("role", ""),
                content=payload_dict.get("content", ""),
                metadata=payload_dict.get("metadata")
            )
            if payload.validate():
                return payload
            return None
        except Exception as e:
            logger.error(f"Guard Agent: UFP Payload validation exception: {e}")
            return None


def secure_ufp_handler(func: Callable) -> Callable:
    """
    Decorator to intercept and validate UFP messages before they are processed by an agent.
    Assumes the decorated function takes (self, msg_payload: bytes/str, ...) or (msg_payload: bytes/str, ...)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Heuristic to find the payload argument (usually the first or second string/bytes arg)
        payload_arg = None
        for arg in args:
            if isinstance(arg, (bytes, str)):
                payload_arg = arg
                break
        
        if payload_arg is None and 'payload' in kwargs:
            payload_arg = kwargs['payload']
            
        if payload_arg:
            parsed_payload = UFPPayload.from_bytes(payload_arg)
            if not parsed_payload or not parsed_payload.validate():
                logger.error("secure_ufp_handler: Dropping message due to payload validation failure.")
                # Depending on the agent architecture, we could raise an exception or return an error code.
                raise ValueError("Security Policy Violation: Invalid or malicious payload detected.")
                
        return func(*args, **kwargs)
    return wrapper
