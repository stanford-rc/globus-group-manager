# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# The ggm.cli module is used to implement CLI commands, which are run on the
# server hosting SGGM.  Everything is accessed through one CLI command,
# `stanford-globus-group-manager`, which is created in this file.  Sub-commands
# are defined in sub-modules, imported, and then added to the top-level
# command.

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

from ggm.cli.scopes import scopes_group


@click.group()
@click.version_option()
def main() -> None:
    pass

main.add_command(scopes_group)
