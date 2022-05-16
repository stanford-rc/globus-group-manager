# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# These are plumbing commands for 

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

from ggm.globus.client import GlobusServerClients
import ggm.globus.group


@click.group('globus')
def globus_group() -> None:
    """Globus internal commands.

    These commands used for working with Globus methods.
    """
    pass


@globus_group.command()
@click.argument('domain', type=str)
def scope(
    domain: str,
) -> None:
    while (input_line := sys.stdin.readline().rstrip()):
        print(
            list(ggm.globus.group.scope_usernames((input_line,), domain))[0]
        )


@globus_group.command()
@click.argument('domain')
def descope(
    domain: str,
) -> None:
    while (input_line := sys.stdin.readline().rstrip()):
        # This is more complex, since we have to be on the lookout for an
        # exception.
        try:
            output = list(ggm.globus.group.descope_usernames((input_line,), domain))[0]
        except KeyError:
            output = ''
            print(f"Non-matching domain for {input_line}", file=sys.stderr)
        except ValueError:
            output = ''
            print(f"No domain for {input_line}", file=sys.stderr)
        print(output)


@globus_group.command()
@click.option('--high-risk',
    is_flag=True,
    help='Group will be used with High-Risk data',
)
@click.option('--admin', '-a',
    multiple=True,
    help='Globus identity usernames or UUIDs of Group administrators',
)
@click.argument('name')
@click.argument('description', type=str, required=False)
def create(
    name: str,
    description: Optional[str],
    high_risk: bool,
    admin: Collection[str],
) -> None:
    group_id: Optional[UUID]
    error: Optional[Exception]
    try:
        (group_id, error) = ggm.globus.group.create_group(
            client=GlobusServerClients.from_config(),
            name=name,
            description=description,
            high_risk=high_risk,
            additional_admins=admin,
        )
    except Exception as e:
        (group_id, error) = (None, e)

    if error is not None:
        if isinstance(error, KeyError):
            print('Could not find Globus Identity ' + str(error), file=sys.stderr)
        elif isinstance(error, PermissionError):
            print('No permissions to create group', file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
    if group_id is not None:
        print(group_id)


@globus_group.command()
@click.argument('group', type=click.UUID)
def delete(
    group: UUID,
) -> None:
    try:
        ggm.globus.group.delete_group(
            client=GlobusServerClients.from_config(),
            group_id=group,
        )
    except PermissionError:
        print('No permission to delete group', file=sys.stderr)
    except KeyError:
        print('Group not found', file=sys.stderr)
    except IOError as e:
        print(str(e), file=sys.stderr)


@globus_group.command()
@click.argument('group', type=click.UUID)
def members(
    group: UUID,
) -> None:
    try:
        members=ggm.globus.group.get_members(
            client=GlobusServerClients.from_config(),
            group_id=group,
        )
    except KeyError:
        print('Group not found', file=sys.stderr)
    except PermissionError:
        print('No permission to list group', file=sys.stderr)
    except IOError as e:
        print(str(e), file=sys.stderr)

    member_levels = {
        'member': members.members,
        'manager': members.managers,
        'admin': members.admins,
    }
    for (label, group) in member_levels.items():
        for member in group:
            print(' '.join((label, member)))


@globus_group.command()
@click.option('--provision',
    is_flag=True,
    help='Provision unrecognized Identity usernames'
)
@click.option('--member', '-m',
    multiple=True,
    required=True,
    help='Globus Identity username of the new member',
)
@click.argument('group', type=click.UUID)
def add(
    group: UUID,
    member: Collection[str],
    provision: Optional[bool] = False,
) -> None:
    members: set[str] = set(member)
    try:
        members=ggm.globus.group.add_members(
            client=GlobusServerClients.from_config(),
            group_id=group,
            members=members,
            provision=provision,
        )
    except FileNotFoundError:
        print('Group not found', file=sys.stderr)
    except KeyError as e:
        print('User not found: ' + str(e), file=sys.stderr)
    except PermissionError:
        print('No permission to list group', file=sys.stderr)
    except IOError as e:
        print(str(e), file=sys.stderr)

    # Nothing to output here.


@globus_group.command()
@click.option('--member', '-m',
    multiple=True,
    required=True,
    help='Globus Identity username of the member to remove',
)
@click.argument('group', type=click.UUID)
def remove(
    group: UUID,
    member: Collection[str],
) -> None:
    members: set[str] = set(member)
    try:
        members=ggm.globus.group.remove_members(
            client=GlobusServerClients.from_config(),
            group_id=group,
            members=members,
        )
    except FileNotFoundError:
        print('Group not found', file=sys.stderr)
    except KeyError as e:
        print('User not found: ' + str(e), file=sys.stderr)
    except PermissionError:
        print('No permission to list group', file=sys.stderr)
    except IOError as e:
        print(str(e), file=sys.stderr)

    # Nothing to output here.
