# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# The `plumbing` commands are ones that should not be in regular use.  They are
# meant to make development and testing easier.

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
from typing import *




@click.group('plumbing')
def plumbing_group() -> None:
    """Internal commands for testing and development.

    These commands are not meant for normal, day-to-day use.  Instead, they are
    meant to make development, testing, troubleshooting, and the like easier to
    accomplish.  These commands provide direct access to many of the internal
    functions of this package.
    """
    pass
