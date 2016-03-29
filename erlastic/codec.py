
from __future__ import division

import six
import struct
import zlib

from erlastic.compat import *
from erlastic.constants import *
from erlastic.types import *

__all__ = ["ErlangTermEncoder", "ErlangTermDecoder", "EncodingError"]

class EncodingError(Exception):
    pass

class ErlangTermDecoder(object):
    def __init__(self):
        # Cache decode functions to avoid having to do a getattr
        self.decoders = {}
        for k in self.__class__.__dict__:
            v = getattr(self, k)
            if callable(v) and k.startswith('decode_'):
                try: self.decoders[int(k.split('_')[1])] = v
                except: pass

    def decode(self, buf, offset=0):
        version = six.indexbytes(buf, offset)
        if version != FORMAT_VERSION:
            raise EncodingError("Bad version number. Expected %d found %d" % (FORMAT_VERSION, version))
        return self.decode_part(buf, offset+1)[0]

    def decode_part(self, buf, offset=0):
        return self.decoders[six.indexbytes(buf, offset)](buf, offset+1)

    def decode_97(self, buf, offset):
        """SMALL_INTEGER_EXT"""
        return six.indexbytes(buf, offset), offset+1

    def decode_98(self, buf, offset):
        """INTEGER_EXT"""
        return struct.unpack(">l", buf[offset:offset+4])[0], offset+4

    def decode_99(self, buf, offset):
        """FLOAT_EXT"""
        return float(buf[offset:offset+31].split(six.b('\x00'), 1)[0]), offset+31

    def decode_70(self, buf, offset):
        """NEW_FLOAT_EXT"""
        return struct.unpack(">d", buf[offset:offset+8])[0], offset+8

    def decode_100(self, buf, offset):
        """ATOM_EXT"""
        atom_len = struct.unpack(">H", buf[offset:offset+2])[0]
        atom = buf[offset+2:offset+2+atom_len]
        return self.convert_atom(atom), offset+atom_len+2

    def decode_115(self, buf, offset):
        """SMALL_ATOM_EXT"""
        atom_len = six.indexbytes(buf, offset)
        atom = buf[offset+1:offset+1+atom_len]
        return self.convert_atom(atom), offset+atom_len+1

    def decode_104(self, buf, offset):
        """SMALL_TUPLE_EXT"""
        arity = six.indexbytes(buf, offset)
        offset += 1

        items = []
        for i in range(arity):
            val, offset = self.decode_part(buf, offset)
            items.append(val)
        return tuple(items), offset

    def decode_105(self, buf, offset):
        """LARGE_TUPLE_EXT"""
        arity = struct.unpack(">L", buf[offset:offset+4])[0]
        offset += 4

        items = []
        for i in range(arity):
            val, offset = self.decode_part(buf, offset)
            items.append(val)
        return tuple(items), offset

    def decode_106(self, buf, offset):
        """NIL_EXT"""
        return [], offset

    def decode_107(self, buf, offset):
        """STRING_EXT"""
        length = struct.unpack(">H", buf[offset:offset+2])[0]
        st = buf[offset+2:offset+2+length]
        return st, offset+2+length

    def decode_108(self, buf, offset):
        """LIST_EXT"""
        length = struct.unpack(">L", buf[offset:offset+4])[0]
        offset += 4
        items = []
        for i in range(length):
            val, offset = self.decode_part(buf, offset)
            items.append(val)
        tail, offset = self.decode_part(buf, offset)
        if tail != []:
            # TODO: Not sure what to do with the tail
            raise NotImplementedError("Lists with non empty tails are not supported")
        return items, offset

    def decode_109(self, buf, offset):
        """BINARY_EXT"""
        length = struct.unpack(">L", buf[offset:offset+4])[0]
        return buf[offset+4:offset+4+length], offset+4+length

    def decode_110(self, buf, offset):
        """SMALL_BIG_EXT"""
        n = six.indexbytes(buf, offset)
        offset += 1
        return self.decode_bigint(n, buf, offset)

    def decode_111(self, buf, offset):
        """LARGE_BIG_EXT"""
        n = struct.unpack(">L", buf[offset:offset+4])[0]
        offset += 4
        return self.decode_bigint(n, buf, offset)

    def decode_112(self, buf, offset):
        """NEW_FUN_EXT"""
        size = struct.unpack(">L", buf[offset:offset+4])[0]
        arity = ord(buf[4])
        return "f/%d"%(arity), offset+size

    def decode_bigint(self, n, buf, offset):
        sign = six.indexbytes(buf, offset)
        offset += 1
        b = 1
        val = 0
        for i in range(n):
            val += six.indexbytes(buf, offset) * b
            b <<= 8
            offset += 1
        if sign != 0:
            val = -val
        return val, offset

    def decode_101(self, buf, offset):
        """REFERENCE_EXT"""
        node, offset = self.decode_part(buf, offset)
        if not isinstance(node, Atom):
            raise EncodingError("Expected atom while parsing REFERENCE_EXT, found %r instead" % node)
        reference_id, creation = struct.unpack(">LB", buf[offset:offset+5])
        return Reference(node, [reference_id], creation), offset+5

    def decode_114(self, buf, offset):
        """NEW_REFERENCE_EXT"""
        id_len = struct.unpack(">H", buf[offset:offset+2])[0]
        node, offset = self.decode_part(buf, offset+2)
        if not isinstance(node, Atom):
            raise EncodingError("Expected atom while parsing NEW_REFERENCE_EXT, found %r instead" % node)
        creation = six.indexbytes(buf, offset)
        reference_id = struct.unpack(">%dL" % id_len, buf[offset+1:offset+1+4*id_len])
        return Reference(node, reference_id, creation), offset+1+4*id_len

    def decode_102(self, buf, offset):
        """PORT_EXT"""
        node, offset = self.decode_part(buf, offset)
        if not isinstance(node, Atom):
            raise EncodingError("Expected atom while parsing PORT_EXT, found %r instead" % node)
        port_id, creation = struct.unpack(">LB", buf[offset:offset+5])
        return Port(node, port_id, creation), offset+5

    def decode_103(self, buf, offset):
        """PID_EXT"""
        node, offset = self.decode_part(buf, offset)
        if not isinstance(node, Atom):
            raise EncodingError("Expected atom while parsing PID_EXT, found %r instead" % node)
        pid_id, serial, creation = struct.unpack(">LLB", buf[offset:offset+9])
        return PID(node, pid_id, serial, creation), offset+9

    def decode_113(self, buf, offset):
        """EXPORT_EXT"""
        module, offset = self.decode_part(buf, offset)
        if not isinstance(module, Atom):
            raise EncodingError("Expected atom while parsing EXPORT_EXT, found %r instead" % module)
        function, offset = self.decode_part(buf, offset)
        if not isinstance(function, Atom):
            raise EncodingError("Expected atom while parsing EXPORT_EXT, found %r instead" % function)
        arity, offset = self.decode_part(buf, offset)
        if not isinstance(arity, six.integer_types):
            raise EncodingError("Expected integer while parsing EXPORT_EXT, found %r instead" % arity)
        return Export(module, function, arity), offset+1

    def decode_80(self, buf, offset):
        """Compressed term"""
        usize = struct.unpack(">L", buf[offset:offset+4])[0]
        buf = zlib.decompress(buf[offset+4:offset+4+usize])
        return self.decode_part(buf, 0)

    def convert_atom(self, atom):
        if atom == b"true":
            return True
        elif atom == b"false":
            return False
        elif atom == b"none":
            return None
        return Atom(atom.decode('latin-1'))

class ErlangTermEncoder(object):
    def __init__(self, encoding="utf-8", unicode_type="binary"):
        self.encoding = encoding
        self.unicode_type = unicode_type

    def encode(self, obj, compressed=False):
        ubuf = six.b('').join(self.encode_part(obj))
        if compressed is True:
            compressed = 6
        if not (compressed is False \
                    or (isinstance(compressed, six.integer_types) \
                            and compressed >= 0 and compressed <= 9)):
            raise TypeError("compressed must be True, False or "
                            "an integer between 0 and 9")
        if compressed:
            cbuf = zlib.compress(ubuf, compressed)
            if len(cbuf) < len(ubuf):
                usize = struct.pack(">L", len(ubuf))
                ubuf = "".join([COMPRESSED, usize, cbuf])
        return pack_bytes([FORMAT_VERSION]) + ubuf

    def encode_part(self, obj):
        if obj is False:
            return [pack_bytes([ATOM_EXT]), struct.pack(">H", 5), b"false"]
        elif obj is True:
            return [pack_bytes([ATOM_EXT]), struct.pack(">H", 4), b"true"]
        elif obj is None:
            return [pack_bytes([ATOM_EXT]), struct.pack(">H", 4), b"none"]
        elif isinstance(obj, six.integer_types):
            if 0 <= obj <= 255:
                return [pack_bytes([SMALL_INTEGER_EXT,obj])]
            elif -2147483648 <= obj <= 2147483647:
                return [pack_bytes([INTEGER_EXT]), struct.pack(">l", obj)]
            else:
                sign = obj < 0
                obj = abs(obj)

                big_buf = []
                while obj > 0:
                    big_buf.append(obj & 0xff)
                    obj >>= 8

                if len(big_buf) < 256:
                    return [pack_bytes([SMALL_BIG_EXT,len(big_buf),sign]),
                            pack_bytes(big_buf)]
                else:
                    return [pack_bytes([LARGE_BIG_EXT]),
                            struct.pack(">L", len(big_buf)),
                            pack_bytes([sign]), pack_bytes(big_buf)]
        elif isinstance(obj, float):
            floatstr = ("%.20e" % obj).encode('ascii')
            return [pack_bytes([FLOAT_EXT]), floatstr + b"\x00"*(31-len(floatstr))]
        elif isinstance(obj, Atom):
            st = obj.encode('latin-1')
            return [pack_bytes([ATOM_EXT]), struct.pack(">H", len(st)), st]
        elif isinstance(obj, six.text_type):
            st = obj.encode('utf-8')
            return [pack_bytes([BINARY_EXT]), struct.pack(">L", len(st)), st]
        elif isinstance(obj, six.string_types) or isinstance(obj, six.binary_type):
            # https://pythonhosted.org/six/#six.string_types
            # https://pythonhosted.org/six/#six.binary_type
            return [pack_bytes([BINARY_EXT]), struct.pack(">L", len(obj)), obj]
        elif isinstance(obj, tuple):
            n = len(obj)
            if n < 256:
                buf = [pack_bytes([SMALL_TUPLE_EXT,n])]
            else:
                buf = [pack_bytes([LARGE_TUPLE_EXT]), struct.pack(">L", n)]
            for item in obj:
                buf += self.encode_part(item)
            return buf
        elif obj == []:
            return [pack_bytes([NIL_EXT])]
        elif isinstance(obj, list):
            buf = [pack_bytes([LIST_EXT]), struct.pack(">L", len(obj))]
            for item in obj:
                buf += self.encode_part(item)
            buf.append(pack_bytes([NIL_EXT])) # list tail - no such thing in Python
            return buf
        elif isinstance(obj, Reference):
            return [pack_bytes([NEW_REFERENCE_EXT]), struct.pack(">H", len(obj.ref_id)),
                    pack_bytes([ATOM_EXT]), struct.pack(">H", len(obj.node)),
                    obj.node.encode('latin-1'), pack_bytes([obj.creation]),
                    struct.pack(">%dL" % len(obj.ref_id), *obj.ref_id)]
        elif isinstance(obj, Port):
            return [pack_bytes([PORT_EXT]), pack_bytes([ATOM_EXT]),
                    struct.pack(">H", len(obj.node)), obj.node.encode('latin-1'),
                    struct.pack(">LB", obj.port_id, obj.creation)]
        elif isinstance(obj, PID):
           return [pack_bytes([PID_EXT]), pack_bytes([ATOM_EXT]),
                   struct.pack(">H", len(obj.node)), obj.node.encode('latin-1'),
                   struct.pack(">LLB", obj.pid_id, obj.serial, obj.creation)]
        elif isinstance(obj, Export):
            return [pack_bytes([EXPORT_EXT]), pack_bytes([ATOM_EXT]),
                    struct.pack(">H", len(obj.module)), obj.module.encode('latin-1'),
                    pack_bytes([ATOM_EXT]), struct.pack(">H", len(obj.function)),
                    obj.function.encode('latin-1'), pack_bytes([SMALL_INTEGER_EXT,obj.arity])]
        else:
            raise NotImplementedError("Unable to serialize %r" % obj)
