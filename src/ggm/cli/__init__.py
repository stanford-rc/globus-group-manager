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
import coloredlogs
import logging
from typing import *

from ggm.cli.plumbing import plumbing_group
from ggm.cli.scopes import scopes_group


# Set up logging for the CLI
# We use coloredlogs here, since it integrates well with logging and gives us
# nice formatting.
# By default, we limit ourselves to the WARNING level.
logger = logging.getLogger()
coloredlogs.install(level=logging.WARNING, logger=logger)

# Effectively disable logging in the libraries we use.
logging.getLogger('urllib3').setLevel('CRITICAL')
logging.getLogger('globus_sdk').setLevel('CRITICAL')


# Catch instances of -v (or --verbose).
# Should be called once, with the value being the # of times -v is used.
def set_verbose(
    ctx: click.Context,
    param: click.Option,
    value: Any,
) -> None:
    if param.human_readable_name != 'verbose':
        raise NotImplementedError('set_verbose only handles verbose')
    if isinstance(value, int):
        # Set log level based on how many -v we get
        if value == 0:
            pass # This should never be hit, as we won't be called.
        elif value == 1:
            coloredlogs.set_level(logging.INFO)
            logger.info('Log level set to INFO')
        else: # value >= 2
            coloredlogs.set_level(logging.DEBUG)
            logger.debug('Log level set to DEBUG')


# Create the root of our command!
@click.group()
@click.version_option()
@click.option(
    '-v', '--verbose',
    count=True,
    callback=set_verbose,
    expose_value=False,
)
def main() -> None:
    pass

main.add_command(plumbing_group)
main.add_command(scopes_group)
