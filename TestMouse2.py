#!/usr/bin/env python3

import struct

infile_path = "/dev/input/event9"
# infile_path = "/dev/hidraw5"

# struct input_event {
#     struct timeval time;
#     unsigned short type;
#     unsigned short code;
#     unsigned int value;
# };

EVENT_FORMAT = "llHHI"; # long, long, unsigned short, unsigned short, unsigned int
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

with open(infile_path, "rb") as file:
    event = file.read(EVENT_SIZE)
    while event:
        #(tv_sec, tv_usec, type, code, value) = struct.unpack(EVENT_FORMAT, event)
        print(struct.unpack(EVENT_FORMAT, event))
        event = file.read(EVENT_SIZE)
