import sys

from array import array

__all__ = ['pack_bytes']

if sys.version_info < (3,):
    pack_bytes = lambda a: array('B', a).tostring()
else:
    pack_bytes = bytes
