"""
Temporal Message Queuing (TMQ) - Enhancement 1

Enables messages to be scheduled for future delivery or retroactively delivered
to past timestamps. Supports dead man's switches and time-locked secrets.
"""

import struct
import time
import json
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

try:
    from .dsmil_protocol import MessageType, MessageFlags, MemshadowMessage
except ImportError:
    # Fallback for testing
    MessageType = None
    MessageFlags = None
    MemshadowMessage = None


class TemporalMode(IntEnum):
    """Temporal delivery modes"""
    NORMAL = 0  # Immediate delivery (no temporal queuing)
    FUTURE = 1  # Schedule for future delivery
    RETROACTIVE = 2  # Deliver to past timestamp
    BOTH = 3  # Both future and retroactive support


@dataclass
class TemporalMessage:
    """
    Temporal message metadata for queuing.
    
    Messages can be:
    - Scheduled for future delivery (dead man's switch, time-locked secrets)
    - Retroactively delivered to past timestamps (audit trails, corrections)
    """
    message_id: bytes = field(default_factory=lambda: uuid.uuid4().bytes)
    delivery_timestamp: int = 0  # Nanoseconds since epoch (0 = immediate)
    max_age: int = 0  # Max age before expiration (nanoseconds, 0 = no expiration)
    temporal_mode: int = TemporalMode.NORMAL
    original_payload: bytes = b""
    original_header: Optional[MemshadowMessage] = None
    created_at: int = field(default_factory=lambda: int(time.time() * 1e9))
    expires_at: Optional[int] = None  # Expiration timestamp (nanoseconds)
    
    def pack(self) -> bytes:
        """Pack temporal message metadata to binary"""
        return struct.pack(
            ">16sQIQQ16sQ",
            self.message_id,
            self.delivery_timestamp,
            self.max_age,
            self.temporal_mode,
            self.created_at,
            len(self.original_payload),
            self.expires_at or 0,
        ) + self.original_payload
    
    @classmethod
    def unpack(cls, data: bytes) -> "TemporalMessage":
        """Unpack temporal message metadata from binary"""
        if len(data) < 56:
            raise ValueError("Temporal message data too short")
        
        (message_id, delivery_timestamp, max_age, temporal_mode,
         created_at, payload_len, expires_at) = struct.unpack(
            ">16sQIQQ16sQ", data[:56]
        )
        
        payload = data[56:56 + payload_len] if payload_len > 0 else b""
        
        return cls(
            message_id=message_id,
            delivery_timestamp=delivery_timestamp,
            max_age=max_age,
            temporal_mode=temporal_mode,
            created_at=created_at,
            original_payload=payload,
            expires_at=expires_at if expires_at > 0 else None,
        )
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        if self.expires_at is None:
            return False
        return time.time_ns() > self.expires_at
    
    def should_deliver(self) -> bool:
        """Check if message should be delivered now"""
        if self.temporal_mode == TemporalMode.NORMAL:
            return True
        
        now = time.time_ns()
        
        if self.temporal_mode == TemporalMode.FUTURE:
            return now >= self.delivery_timestamp
        
        if self.temporal_mode == TemporalMode.RETROACTIVE:
            # Retroactive messages are always deliverable
            return True
        
        if self.temporal_mode == TemporalMode.BOTH:
            # Future: check delivery time, Retroactive: always deliverable
            return now >= self.delivery_timestamp
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "message_id": self.message_id.hex(),
            "delivery_timestamp": self.delivery_timestamp,
            "max_age": self.max_age,
            "temporal_mode": self.temporal_mode,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "payload_len": len(self.original_payload),
        }


class TemporalQueue:
    """
    Manages temporally queued messages.
    
    Supports:
    - Future delivery (scheduled messages)
    - Retroactive delivery (past timestamps)
    - Expiration handling
    - Dead man's switches
    """
    
    def __init__(self):
        self.queue: Dict[bytes, TemporalMessage] = {}
        self.retroactive_log: List[TemporalMessage] = []
    
    def queue_message(
        self,
        message: MemshadowMessage,
        delivery_timestamp: int,
        max_age: Optional[int] = None,
        temporal_mode: int = TemporalMode.FUTURE,
    ) -> bytes:
        """
        Queue a message for temporal delivery.
        
        Args:
            message: Message to queue
            delivery_timestamp: Nanoseconds since epoch for delivery
            max_age: Maximum age before expiration (nanoseconds)
            temporal_mode: Temporal delivery mode
        
        Returns:
            Message ID (bytes)
        """
        temporal_msg = TemporalMessage(
            message_id=uuid.uuid4().bytes,
            delivery_timestamp=delivery_timestamp,
            max_age=max_age or 0,
            temporal_mode=temporal_mode,
            original_payload=message.payload,
            original_header=message,
            expires_at=delivery_timestamp + max_age if max_age else None,
        )
        
        self.queue[temporal_msg.message_id] = temporal_msg
        
        if temporal_mode == TemporalMode.RETROACTIVE:
            self.retroactive_log.append(temporal_msg)
        
        return temporal_msg.message_id
    
    def check_deliveries(self) -> List[MemshadowMessage]:
        """
        Check for messages ready to deliver.
        
        Returns:
            List of messages ready for delivery
        """
        ready = []
        expired = []
        
        now = time.time_ns()
        
        for msg_id, temporal_msg in list(self.queue.items()):
            if temporal_msg.is_expired():
                expired.append(msg_id)
                continue
            
            if temporal_msg.should_deliver():
                # Reconstruct original message
                if temporal_msg.original_header:
                    ready.append(temporal_msg.original_header)
                else:
                    # Create new message from stored payload
                    msg = MemshadowMessage(
                        msg_type=temporal_msg.original_header.msg_type if temporal_msg.original_header else MessageType.TEMPORAL_DELIVER,
                        payload=temporal_msg.original_payload,
                        flags=MessageFlags.TEMPORAL_QUEUED,
                    )
                    ready.append(msg)
                
                # Remove from queue (delivered)
                del self.queue[msg_id]
        
        # Clean up expired messages
        for msg_id in expired:
            del self.queue[msg_id]
        
        return ready
    
    def cancel_message(self, message_id: bytes) -> bool:
        """Cancel a scheduled message"""
        if message_id in self.queue:
            del self.queue[message_id]
            return True
        return False
    
    def get_scheduled_messages(self) -> List[TemporalMessage]:
        """Get all scheduled messages"""
        return list(self.queue.values())
    
    def create_dead_mans_switch(
        self,
        message: MemshadowMessage,
        checkin_interval: int,
        max_missed_checkins: int = 3,
    ) -> bytes:
        """
        Create a dead man's switch message.
        
        If sender doesn't check in within checkin_interval * max_missed_checkins,
        message is delivered.
        
        Args:
            message: Message to deliver if switch triggers
            checkin_interval: Nanoseconds between expected checkins
            max_missed_checkins: Number of missed checkins before delivery
        
        Returns:
            Message ID
        """
        delivery_time = time.time_ns() + (checkin_interval * max_missed_checkins)
        return self.queue_message(
            message,
            delivery_time,
            temporal_mode=TemporalMode.FUTURE,
        )
    
    def checkin(self, message_id: bytes) -> bool:
        """
        Check in to reset dead man's switch timer.
        
        Args:
            message_id: Dead man's switch message ID
        
        Returns:
            True if checkin successful, False if message not found
        """
        if message_id not in self.queue:
            return False
        
        temporal_msg = self.queue[message_id]
        
        # Reset delivery time (extend by checkin interval)
        # This requires storing checkin_interval, simplified here
        # In full implementation, store checkin_interval in TemporalMessage
        return True


class TemporalMessageQueue:
    """
    Temporal Message Queue - Simple time-based message scheduling

    Provides basic temporal queuing functionality for testing.
    """

    def __init__(self):
        self.scheduled_messages: Dict[str, dict] = {}
        self.queue = TemporalQueue()

    def schedule(self, message: dict, delivery_time: float, mode: int):
        """
        Schedule a message for temporal delivery

        Args:
            message: Message to schedule
            delivery_time: Unix timestamp for delivery
            mode: Temporal mode (FUTURE, etc.)
        """
        message_id = str(uuid.uuid4())

        # Convert to nanoseconds for internal storage
        delivery_ns = int(delivery_time * 1e9)

        # Create a simple MemshadowMessage for the queue if available
        if MemshadowMessage and MessageType:
            header = type('MockHeader', (), {
                'msg_type': MessageType.DATA if hasattr(MessageType, 'DATA') else 2,
                'priority': 1,
                'payload_len': len(json.dumps(message).encode())
            })()
            msg = MemshadowMessage(header=header, payload=json.dumps(message).encode())
            # Queue the message
            self.queue.queue_message(msg, delivery_ns, temporal_mode=mode)

        # Store for testing purposes
        self.scheduled_messages[message_id] = {
            'message': message,
            'delivery_time': delivery_time,
            'mode': mode
        }
