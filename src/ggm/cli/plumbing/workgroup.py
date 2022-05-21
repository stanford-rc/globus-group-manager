# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# These are plumbing commands for Workgroup Manager things.

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

import click
from collections.abc import Collection
import sys
from typing import Optional
from uuid import UUID

import ggm.workgroup.uuid


@click.group('workgroup')
def workgroup_group() -> None:
    """Workgroup internal commands.

    These commands used for working with Workgroup methods.
    """
    pass


@workgroup_group.command()
@click.argument('uuid',
    type=click.UUID,
)
def uuid_to_group(
    uuid: UUID,
) -> None:
    """Given a UUID (from a Globus Group), return a compatible Workgroup name.
    """
    # Click ensures that what we get is a UUID.
    # So, just convert to string!
    print(ggm.workgroup.uuid.ggroup_uuid_to_wg_name(uuid))


@workgroup_group.command()
@click.argument('name',
    type=str,
)
def group_to_uuid(
    name: str,
) -> None:
    """Given an encoded UUID (from a Workgroup name), return the UUID.
    """
    print(ggm.workgroup.uuid.wg_name_to_ggroup_uuid(name))
