"""Erlang External Term Format serializer/deserializer"""
import struct
import sys
import six

from erlastic.codec import ErlangTermDecoder, ErlangTermEncoder
from erlastic.types import *

encode = ErlangTermEncoder().encode
decode = ErlangTermDecoder().decode

if six.PY3:
    stdread = sys.stdin.buffer.read
    stdwrite = sys.stdout.buffer.write
else:
    stdread = sys.stdin.read
    stdwrite = sys.stdout.write


def mailbox_gen():
    while True:
        len_bin = stdread(4)
        if len(len_bin) != 4:
            return
        (length,) = struct.unpack('!I', len_bin)
        yield decode(stdread(length))


def port_gen():
    while True:
        term = encode((yield))
        stdwrite(struct.pack('!I', len(term)))
        stdwrite(term)


def port_connection():
    port = port_gen()
    next(port)
    return mailbox_gen(), port
