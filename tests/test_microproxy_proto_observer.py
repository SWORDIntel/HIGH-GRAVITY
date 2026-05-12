#!/usr/bin/env python3
"""Tests for passive Connect/protobuf observer helpers."""

import gzip
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from microproxy import proto_observer  # noqa: E402


def _varint(value):
    encoded = bytearray()
    while value > 0x7F:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def _length_delimited(field_number, value):
    key = (field_number << 3) | 2
    return _varint(key) + _varint(len(value)) + value


def _connect_frame(payload, flags=0):
    return bytes([flags]) + len(payload).to_bytes(4, "big") + payload


class MicroproxyProtoObserverTests(unittest.TestCase):
    def test_parse_connect_frames_reads_complete_envelopes(self):
        first_payload = b"alpha"
        second_payload = b"beta"
        body = (
            _connect_frame(first_payload)
            + _connect_frame(second_payload, flags=1)
            + b"\x00\x00"
        )

        frames = proto_observer.parse_connect_frames(body)

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].offset, 0)
        self.assertEqual(frames[0].payload, first_payload)
        self.assertFalse(frames[0].compressed)
        self.assertEqual(frames[1].payload, second_payload)
        self.assertTrue(frames[1].compressed)
        self.assertEqual(frames[1].compression, "gzip")

    def test_parse_connect_frames_rejects_oversized_frame_before_copying(self):
        body = b"\x00" + (100).to_bytes(4, "big") + b"small"

        with self.assertRaisesRegex(
            proto_observer.ProtoObserverError,
            "exceeds limit",
        ):
            proto_observer.parse_connect_frames(body, max_frame_bytes=10)

    def test_gzip_decompress_copy_is_bounded_and_non_mutating(self):
        payload = bytearray(gzip.compress(b"hello gzip connect frame"))
        original = bytes(payload)

        decompressed = proto_observer.gzip_decompress_copy(payload)

        self.assertEqual(decompressed, b"hello gzip connect frame")
        self.assertEqual(bytes(payload), original)
        with self.assertRaisesRegex(
            proto_observer.ProtoObserverError,
            "gzip output exceeds limit",
        ):
            proto_observer.gzip_decompress_copy(payload, max_output_bytes=4)

    def test_extract_length_delimited_utf8_strings_from_protobuf_wire(self):
        message = (
            _varint(8)
            + _varint(7)
            + _length_delimited(2, b"hello observer sidecar")
            + _length_delimited(3, b"\xff\xfe")
            + _length_delimited(4, b"ok")
            + _length_delimited(5, b"hello observer sidecar")
        )

        strings = proto_observer.extract_length_delimited_utf8_strings(message)

        self.assertEqual(strings, ["hello observer sidecar"])

    def test_observe_connect_proto_builds_proto_observed_event(self):
        message = _length_delimited(
            1,
            b"future observer sidecar extracts useful request text",
        )
        compressed = gzip.compress(message)
        body = _connect_frame(compressed, flags=1)
        original = bytes(body)

        event = proto_observer.observe_connect_proto(
            body,
            request_id="req-1",
            content_type="application/connect+proto",
            direction="request",
            ts="2026-05-11T10:00:00.000Z",
            metadata={"connection_id": "conn-1"},
        )

        self.assertEqual(body, original)
        self.assertEqual(event["schema_version"], 1)
        self.assertEqual(event["event"], "proto_observed")
        self.assertEqual(event["request_id"], "req-1")
        self.assertEqual(event["connection_id"], "conn-1")
        details = event["details"]
        self.assertEqual(details["proto"], "connect+proto")
        self.assertEqual(details["content_type"], "application/connect+proto")
        self.assertEqual(details["connect_frame_count"], 1)
        self.assertEqual(details["gzip_frame_count"], 1)
        self.assertEqual(details["connect_flags"], [1])
        self.assertEqual(details["connect_frame_lengths"], [len(compressed)])
        self.assertEqual(details["strings"], [
            "future observer sidecar extracts useful request text"
        ])
        self.assertEqual(details["string_count"], 1)

    def test_observe_connect_proto_handles_unframed_protobuf_snapshot(self):
        body = _length_delimited(1, b"unframed protobuf text copy")

        event = proto_observer.observe_connect_proto(
            body,
            request_id="req-2",
            ts="2026-05-11T10:00:00.000Z",
        )

        self.assertEqual(event["details"]["connect_frame_count"], 0)
        self.assertEqual(event["details"]["gzip_frame_count"], 0)
        self.assertEqual(event["details"]["strings"], [
            "unframed protobuf text copy"
        ])


if __name__ == "__main__":
    unittest.main()
