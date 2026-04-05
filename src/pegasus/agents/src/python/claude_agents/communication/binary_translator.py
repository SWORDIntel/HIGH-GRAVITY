#!/usr/bin/env python3
"""
Binary Message Translator Module
==================================

Translates binary agent communication messages to human-readable format and vice versa.
Integrates with the Ultra-Fast Protocol (UFP) binary communication layer.

Features:
- Binary to human-readable JSON conversion
- Human-readable to binary message encoding
- Message type interpretation
- Payload decoding and encoding
- Performance metrics tracking
- Support for all UFP message types

Author: SWORDSwarm Agent Communication System
Version: 1.0.0
Status: PRODUCTION
"""

import json
import struct
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Ultra-Fast Protocol message types"""

    REQUEST = 0x01
    RESPONSE = 0x02
    BROADCAST = 0x03
    HEARTBEAT = 0x04
    ACK = 0x05
    ERROR = 0x06
    VETO = 0x07
    TASK = 0x08
    RESULT = 0x09
    STATE_SYNC = 0x0A
    RESOURCE_REQ = 0x0B
    RESOURCE_RESP = 0x0C
    DISCOVERY = 0x0D
    SHUTDOWN = 0x0E
    EMERGENCY = 0x0F


class Priority(Enum):
    """Message priority levels"""

    CRITICAL = 0x00
    HIGH = 0x01
    MEDIUM = 0x02
    LOW = 0x03
    BACKGROUND = 0x04


@dataclass
class BinaryMessage:
    """Binary message structure matching C UFP format"""

    msg_id: int
    msg_type: MessageType
    priority: Priority
    source: str
    targets: List[str]
    payload: bytes
    timestamp: int
    correlation_id: int = 0
    flags: int = 0

    # Metadata
    decoded_at: Optional[datetime] = None
    human_readable_payload: Optional[Dict[str, Any]] = None


@dataclass
class HumanReadableMessage:
    """Human-readable message format for display and logging"""

    message_id: int
    message_type: str
    priority: str
    source_agent: str
    target_agents: List[str]
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[int] = None
    flags: int = 0

    # Metadata
    decoded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload_size_bytes: int = 0

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), indent=indent)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class BinaryMessageTranslator:
    """Translates between binary protocol and human-readable formats"""

    # Binary format constants
    MAGIC_NUMBER = 0xAF42CAFE
    HEADER_SIZE = 64  # bytes
    MAX_AGENT_NAME_SIZE = 64
    MAX_TARGETS = 256

    def __init__(self):
        self.stats = {
            'messages_translated': 0,
            'binary_to_human': 0,
            'human_to_binary': 0,
            'errors': 0,
            'total_bytes_processed': 0,
        }

    def binary_to_human(self, binary_data: bytes) -> HumanReadableMessage:
        """
        Translate binary message to human-readable format

        Args:
            binary_data: Raw binary message bytes

        Returns:
            HumanReadableMessage object
        """
        try:
            # Parse binary header
            if len(binary_data) < self.HEADER_SIZE:
                raise ValueError(f"Binary data too short: {len(binary_data)} < {self.HEADER_SIZE}")

            # Unpack header (simplified format)
            # Format: magic(4) msg_id(4) msg_type(1) priority(1) timestamp(8) correlation_id(4) flags(1)
            header_format = '<I I B B x x x x Q I B x x x'
            header_data = struct.unpack_from(header_format, binary_data)

            magic = header_data[0]
            if magic != self.MAGIC_NUMBER:
                raise ValueError(f"Invalid magic number: 0x{magic:08X}")

            msg_id = header_data[1]
            msg_type_raw = header_data[2]
            priority_raw = header_data[3]
            timestamp = header_data[4]
            correlation_id = header_data[5]
            flags = header_data[6]

            # Parse source and targets (after header)
            offset = self.HEADER_SIZE

            # Read source agent name (null-terminated string, max 64 bytes)
            source_end = binary_data.find(b'\x00', offset, offset + self.MAX_AGENT_NAME_SIZE)
            if source_end == -1 or source_end == offset:
                source_end = offset + self.MAX_AGENT_NAME_SIZE
            source = binary_data[offset:source_end].decode('utf-8', errors='replace').rstrip('\x00')
            offset += self.MAX_AGENT_NAME_SIZE

            # Read target count
            target_count = struct.unpack_from('<B', binary_data, offset)[0]
            offset += 1

            # Read targets
            targets = []
            for _ in range(min(target_count, self.MAX_TARGETS)):
                target_end = binary_data.find(b'\x00', offset, offset + self.MAX_AGENT_NAME_SIZE)
                if target_end == -1 or target_end == offset:
                    target_end = offset + self.MAX_AGENT_NAME_SIZE
                target = binary_data[offset:target_end].decode('utf-8', errors='replace').rstrip('\x00')
                targets.append(target)
                offset += self.MAX_AGENT_NAME_SIZE

            # Read payload size
            payload_size = struct.unpack_from('<I', binary_data, offset)[0]
            offset += 4

            # Read payload
            payload_bytes = binary_data[offset:offset + payload_size]

            # Decode payload based on message type
            payload_dict = self._decode_payload(
                MessageType(msg_type_raw),
                payload_bytes
            )

            # Create human-readable message
            message = HumanReadableMessage(
                message_id=msg_id,
                message_type=MessageType(msg_type_raw).name,
                priority=Priority(priority_raw).name,
                source_agent=source,
                target_agents=targets,
                payload=payload_dict,
                timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                correlation_id=correlation_id if correlation_id != 0 else None,
                flags=flags,
                payload_size_bytes=len(payload_bytes)
            )

            # Update stats
            self.stats['messages_translated'] += 1
            self.stats['binary_to_human'] += 1
            self.stats['total_bytes_processed'] += len(binary_data)

            return message

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error translating binary to human: {e}")
            raise

    def human_to_binary(self, message: HumanReadableMessage) -> bytes:
        """
        Translate human-readable message to binary format

        Args:
            message: HumanReadableMessage object

        Returns:
            Binary message bytes
        """
        try:
            # Encode payload
            payload_bytes = self._encode_payload(
                MessageType[message.message_type],
                message.payload
            )

            # Build header
            header = struct.pack(
                '<I I B B x x x x Q I B x x x',
                self.MAGIC_NUMBER,
                message.message_id,
                MessageType[message.message_type].value,
                Priority[message.priority].value,
                int(datetime.fromisoformat(message.timestamp).timestamp()),
                message.correlation_id or 0,
                message.flags
            )

            # Add source agent name (padded to MAX_AGENT_NAME_SIZE)
            source_bytes = message.source_agent.encode('utf-8')[:self.MAX_AGENT_NAME_SIZE - 1]
            source_bytes += b'\x00' * (self.MAX_AGENT_NAME_SIZE - len(source_bytes))

            # Add target count and targets
            target_count = min(len(message.target_agents), self.MAX_TARGETS)
            targets_section = struct.pack('<B', target_count)

            for target in message.target_agents[:self.MAX_TARGETS]:
                target_bytes = target.encode('utf-8')[:self.MAX_AGENT_NAME_SIZE - 1]
                target_bytes += b'\x00' * (self.MAX_AGENT_NAME_SIZE - len(target_bytes))
                targets_section += target_bytes

            # Add payload size and payload
            payload_section = struct.pack('<I', len(payload_bytes)) + payload_bytes

            # Combine all sections
            binary_data = header + source_bytes + targets_section + payload_section

            # Update stats
            self.stats['messages_translated'] += 1
            self.stats['human_to_binary'] += 1
            self.stats['total_bytes_processed'] += len(binary_data)

            return binary_data

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error translating human to binary: {e}")
            raise

    def _decode_payload(self, msg_type: MessageType, payload: bytes) -> Dict[str, Any]:
        """
        Decode payload based on message type

        Args:
            msg_type: Message type
            payload: Raw payload bytes

        Returns:
            Decoded payload dictionary
        """
        if len(payload) == 0:
            return {}

        # Try to decode as JSON first
        try:
            return json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # Message-type specific decoding
        if msg_type == MessageType.TASK:
            return self._decode_task_payload(payload)
        elif msg_type == MessageType.RESULT:
            return self._decode_result_payload(payload)
        elif msg_type == MessageType.HEARTBEAT:
            return self._decode_heartbeat_payload(payload)
        elif msg_type == MessageType.ERROR:
            return self._decode_error_payload(payload)
        elif msg_type == MessageType.RESOURCE_REQ:
            return self._decode_resource_request_payload(payload)
        else:
            # Default: return as hex string
            return {
                'raw_data': payload.hex(),
                'size_bytes': len(payload),
                'note': 'Binary payload, displayed as hex'
            }

    def _decode_task_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode task message payload"""
        try:
            # Task format: task_id(4) priority(1) task_description(str)
            task_id = struct.unpack_from('<I', payload, 0)[0]
            priority = struct.unpack_from('<B', payload, 4)[0]

            # Rest is task description
            task_desc = payload[5:].decode('utf-8', errors='replace').rstrip('\x00')

            return {
                'task_id': task_id,
                'priority': priority,
                'description': task_desc
            }
        except Exception as e:
            return {'error': f'Failed to decode task payload: {e}', 'raw': payload.hex()}

    def _decode_result_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode result message payload"""
        try:
            # Result format: task_id(4) status(1) result_data(str)
            task_id = struct.unpack_from('<I', payload, 0)[0]
            status = struct.unpack_from('<B', payload, 4)[0]

            # Rest is result data
            result_data = payload[5:].decode('utf-8', errors='replace').rstrip('\x00')

            return {
                'task_id': task_id,
                'status': 'success' if status == 0 else 'failed',
                'status_code': status,
                'result': result_data
            }
        except Exception as e:
            return {'error': f'Failed to decode result payload: {e}', 'raw': payload.hex()}

    def _decode_heartbeat_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode heartbeat message payload"""
        try:
            # Heartbeat format: load(1) queue_depth(2) uptime(8)
            if len(payload) >= 11:
                load = struct.unpack_from('<B', payload, 0)[0]
                queue_depth = struct.unpack_from('<H', payload, 1)[0]
                uptime = struct.unpack_from('<Q', payload, 3)[0]

                return {
                    'load_percent': load,
                    'queue_depth': queue_depth,
                    'uptime_seconds': uptime
                }
            return {'status': 'alive'}
        except Exception as e:
            return {'error': f'Failed to decode heartbeat payload: {e}'}

    def _decode_error_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode error message payload"""
        try:
            # Error format: error_code(4) error_message(str)
            error_code = struct.unpack_from('<I', payload, 0)[0]
            error_msg = payload[4:].decode('utf-8', errors='replace').rstrip('\x00')

            return {
                'error_code': error_code,
                'error_message': error_msg
            }
        except Exception as e:
            return {'error': f'Failed to decode error payload: {e}'}

    def _decode_resource_request_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode resource request payload"""
        try:
            # Resource format: resource_type(1) quantity(4) description(str)
            resource_type = struct.unpack_from('<B', payload, 0)[0]
            quantity = struct.unpack_from('<I', payload, 1)[0]
            description = payload[5:].decode('utf-8', errors='replace').rstrip('\x00')

            return {
                'resource_type': resource_type,
                'quantity': quantity,
                'description': description
            }
        except Exception as e:
            return {'error': f'Failed to decode resource request: {e}'}

    def _encode_payload(self, msg_type: MessageType, payload_dict: Dict[str, Any]) -> bytes:
        """
        Encode payload dictionary to binary format

        Args:
            msg_type: Message type
            payload_dict: Payload dictionary

        Returns:
            Encoded payload bytes
        """
        # Try JSON encoding first
        try:
            return json.dumps(payload_dict).encode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to encode payload as JSON: {e}, using fallback")

            # Fallback: convert to string
            return str(payload_dict).encode('utf-8')

    def format_conversation(
        self,
        messages: List[HumanReadableMessage],
        show_metadata: bool = True,
        show_timestamps: bool = True
    ) -> str:
        """
        Format multiple messages as a conversation transcript

        Args:
            messages: List of messages
            show_metadata: Include metadata in output
            show_timestamps: Include timestamps

        Returns:
            Formatted conversation string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("AGENT CONVERSATION TRANSCRIPT")
        lines.append("=" * 80)
        lines.append("")

        for i, msg in enumerate(messages, 1):
            lines.append(f"[Message {i}]")

            if show_timestamps:
                lines.append(f"Timestamp: {msg.timestamp}")

            lines.append(f"From: {msg.source_agent}")
            lines.append(f"To: {', '.join(msg.target_agents)}")
            lines.append(f"Type: {msg.message_type} (Priority: {msg.priority})")

            if msg.correlation_id:
                lines.append(f"Correlation ID: {msg.correlation_id} (Reply to previous message)")

            lines.append("\nPayload:")
            lines.append(json.dumps(msg.payload, indent=2))

            if show_metadata:
                lines.append(f"\nMetadata:")
                lines.append(f"  - Message ID: {msg.message_id}")
                lines.append(f"  - Payload Size: {msg.payload_size_bytes} bytes")
                lines.append(f"  - Flags: 0x{msg.flags:02X}")

            lines.append("\n" + "-" * 80 + "\n")

        lines.append(f"Total messages in conversation: {len(messages)}")
        lines.append("=" * 80)

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get translator statistics"""
        return dict(self.stats)

    def reset_stats(self):
        """Reset statistics"""
        for key in self.stats:
            self.stats[key] = 0


# Convenience functions
def binary_to_human(binary_data: bytes) -> HumanReadableMessage:
    """Quick conversion from binary to human-readable"""
    translator = BinaryMessageTranslator()
    return translator.binary_to_human(binary_data)


def human_to_binary(message: HumanReadableMessage) -> bytes:
    """Quick conversion from human-readable to binary"""
    translator = BinaryMessageTranslator()
    return translator.human_to_binary(message)


def format_conversation(messages: List[HumanReadableMessage]) -> str:
    """Quick conversation formatting"""
    translator = BinaryMessageTranslator()
    return translator.format_conversation(messages)


if __name__ == '__main__':
    # Example usage
    translator = BinaryMessageTranslator()

    # Create a sample human-readable message
    sample_message = HumanReadableMessage(
        message_id=12345,
        message_type='TASK',
        priority='HIGH',
        source_agent='ORCHESTRATOR',
        target_agents=['DEBUGGER', 'PATCHER'],
        payload={
            'task_id': 42,
            'action': 'analyze_crash',
            'parameters': {
                'crash_dump': '/tmp/crash.dmp',
                'priority': 'high'
            }
        },
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    print("Human-Readable Message:")
    print(sample_message.to_json())
    print("\n" + "=" * 80 + "\n")

    # Convert to binary
    binary_data = translator.human_to_binary(sample_message)
    print(f"Binary representation ({len(binary_data)} bytes):")
    print(binary_data[:100].hex(), "...")
    print("\n" + "=" * 80 + "\n")

    # Convert back to human-readable
    decoded_message = translator.binary_to_human(binary_data)
    print("Decoded Message:")
    print(decoded_message.to_json())
    print("\n" + "=" * 80 + "\n")

    # Show statistics
    print("Translator Statistics:")
    print(json.dumps(translator.get_stats(), indent=2))
