"""
MEMSHADOW Protocol CLI Tools
"""

import argparse
import sys
from typing import List, Optional

from . import __version__, get_implementation_info
from .dsmil_protocol import MemshadowHeader, MessageType, Priority

def create_parser() -> argparse.ArgumentParser:
    """Create the main CLI parser"""
    parser = argparse.ArgumentParser(
        description='MEMSHADOW Protocol CLI Tools',
        prog='memshadow-cli'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'memshadow-protocol {__version__}'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # info command
    info_parser = subparsers.add_parser('info', help='Show implementation information')
    info_parser.set_defaults(func=show_info)

    # header command
    header_parser = subparsers.add_parser('header', help='Work with MEMSHADOW headers')
    header_subparsers = header_parser.add_subparsers(dest='header_command', help='Header operations')

    # pack header
    pack_parser = header_subparsers.add_parser('pack', help='Pack a header from values')
    pack_parser.add_argument('--priority', type=int, default=2, choices=range(5),
                           help='Message priority (0-4)')
    pack_parser.add_argument('--type', type=int, default=1,
                           help='Message type')
    pack_parser.add_argument('--payload-len', type=int, default=0,
                           help='Payload length')
    pack_parser.add_argument('--sequence', type=int, default=0,
                           help='Sequence number')
    pack_parser.set_defaults(func=pack_header)

    # unpack header
    unpack_parser = header_subparsers.add_parser('unpack', help='Unpack a header from hex')
    unpack_parser.add_argument('hex_data', help='Header data as hex string')
    unpack_parser.set_defaults(func=unpack_header)

    return parser

def show_info(args):
    """Show implementation information"""
    info = get_implementation_info()
    print(f"MEMSHADOW Protocol v{info['version']}")
    print(f"Implementation: {info['implementation']}")
    print(f"C Binary Available: {info['c_binary_available']}")

def pack_header(args):
    """Pack a header from command line arguments"""
    import time

    header = MemshadowHeader(
        version=3,
        priority=args.priority,
        msg_type=args.type,
        payload_len=args.payload_len,
        timestamp_ns=int(time.time() * 1e9),
        sequence_num=args.sequence,
    )

    packed = header.pack()
    print(f"Packed header ({len(packed)} bytes):")
    print(packed.hex())

def unpack_header(args):
    """Unpack a header from hex string"""
    try:
        data = bytes.fromhex(args.hex_data)
        header = MemshadowHeader.unpack(data)
        print("Unpacked header:")
        print(f"  Magic: 0x{header.magic:016x}")
        print(f"  Version: {header.version}")
        print(f"  Priority: {header.priority}")
        print(f"  Message Type: {header.msg_type}")
        print(f"  Flags/Batch: {header.flags_batch}")
        print(f"  Payload Length: {header.payload_len}")
        print(f"  Timestamp: {header.timestamp_ns}")
        print(f"  Sequence: {header.sequence_num}")
    except Exception as e:
        print(f"Error unpacking header: {e}")
        sys.exit(1)

def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
