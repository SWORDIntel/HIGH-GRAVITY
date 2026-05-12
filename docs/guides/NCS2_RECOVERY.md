# NCS2 Recovery

The NCS2 path has three separate states:

- USB passthrough: Docker can see `/dev/bus/usb`.
- Runtime visibility: OpenVINO lists `MYRIAD` devices.
- Compile usability: OpenVINO can compile a tiny model on `MYRIAD`.

The failure `MYRIAD device is not opened` or `Failed to find booted device after boot`
means the first two states may be true while the device firmware boot/open step still
failed.

## Commands

Probe without changing hardware:

```bash
./hg.sh khoj ncs2 probe
```

Show the last known recovery summary:

```bash
./hg.sh khoj ncs2 status
```

Explicitly reset the detected Movidius USB devices, then probe again:

```bash
./hg.sh khoj ncs2 reset
```

Recreate Khoj after a reset if the container needs to reacquire USB/OpenVINO state:

```bash
./hg.sh khoj ncs2 restart-khoj
```

No command reboots the machine. The reset command uses `usbreset` when available,
otherwise it toggles the matching USB device's sysfs `authorized` flag.
