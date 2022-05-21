# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# Convert between UUID and Workgroup-compatible names

# © 2022, The Board of Trustees of the Leland Stanford Junior University.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from base64 import b32decode, b32encode
import binascii
import logging
from typing import *
from uuid import UUID


# Set up logging and bring logging functions into this namespace.
# Also add a Null handler (as we're a library).
logger = logging.getLogger(__name__)
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
exception = logger.exception
logger.addHandler(logging.NullHandler())


# These constants are related to encoding the UUID into a form suitable for use
# as a Workgroup name.  Workgroup names may contain letters and numbers, so we
# use Base32 encoding, with an extra 'g' prefix added at the start, to ensure
# the workgroup name starts with a letter.
# Globus Group UUIDs are 128 bits (16 bytes) long.
# RFC 3548 Base32 encoding encodes 5 bits per byte, but it works in groups of
# 40 bits.  Padding bits increase the length to 160 bits.  Those 32 extra
# bits mean there will be floor(32 ÷ 5) = 6 extra padding characters at the
# end, which we want to remove.
B32_ENCODED_LEN = 32
B32_PADDING_LEN = 6
B32_PREFIX_LEN = 1

def ggroup_uuid_to_wg_name(
    ggroup_uuid: UUID,
) -> str:
    """Given a UUID, return a Workgroup name.

    Globus group UUIDs do not work well as workgroup names, since they are long
    and contain hyphens.  This function encodes the UUID in a form that may be
    used as a workgroup name.

    The UUID is converted to a string of bytes, Base32-encoded, stripped of
    padding, and converted to lowercase.  With a 'g' prefix added, the
    workgroup name (not counting stem) is 27 characters.

    Note that the encoded workgroup name is still not very readable, but that
    is not a goal of this method.  Workgroups using this naming format must
    have some useful description.

    @param A UUID

    @returns A string suitable for use as a Workgroup name.
    """
    debug(f"Converting {ggroup_uuid} to a Workgroup name")

    # Start by encoding our UUID and stripping the padding
    ggroup_base32 = b32encode(ggroup_uuid.bytes)
    assert(len(ggroup_base32) == B32_ENCODED_LEN)
    ggroup_base32_bytes = ggroup_base32.removesuffix(b'='*B32_PADDING_LEN)
    assert(len(ggroup_base32_bytes) == B32_ENCODED_LEN - B32_PADDING_LEN)

    # Prepend a 'G', convert to ASCII, lowercase, and return
    return 'g' + ggroup_base32_bytes.decode('ASCII').lower()

def wg_name_to_ggroup_uuid(
    wg_name: str,
) -> UUID:
    """Given a Workgroup name, return a UUID.

    Assuming a UUID was encoded with :func:`ggroup_uuid_to_wg_name`, this
    takes the encoded string and returns the UUID.

    @param A Workgroup name

    @returns A UUID

    @raises IndexError The input string was not 27 characters long.

    @raises ValueError The input string was not of a valid format.
    """

    # Start with a basic length and prefix check
    if len(wg_name) != (B32_ENCODED_LEN - B32_PADDING_LEN + B32_PREFIX_LEN):
        raise IndexError(f"String '{wg_name}' is not the right length")
    if wg_name[0] != 'g':
        raise ValueError(f"String '{wg_name}' missing correct prefix")

    # Remove leading 'g', uppercase, encode to bytes, and add Base32 padding
    try:
        ggroup_base32 = wg_name[1:].upper().encode('ASCII') + b'='*B32_PADDING_LEN
    except UnicodeError:
        raise ValueError(f"String '{wg_name}' is not ASCII")[1:]

    # Decode as base32
    try:
        ggroup_uuid_bytes = b32decode(ggroup_base32)
    except binascii.Error:
        raise ValueError(f"String '{wg_name}' not Base32-encoded")

    # Decode as UUID and return
    return UUID(bytes=ggroup_uuid_bytes)
