# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This defines the `scopes` group of CLI sub-commands.  SGGM has at least one
# Globus Auth Scope, and since Scopes may only be created through the API, code
# is needed to handle Scope creation.  This provides access to that code
# through the CLI.

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

@click.group('scopes')
def scopes_group() -> None:
    """Manage Globus Auth Scopes related to this service.

    This service uses Globus Auth credentials.  If we accepted any Globus Auth
    credential, it would be possible for an attacker to harvest a Globus Auth
    credential from somewhere else, and use it to access this service.  So, we
    have our own set of Globus Auth Scopes.

    Users accessing this service must use a Globus OAuth 2.0 Access Token that
    includes our scopes.
    """
    pass


@scopes_group.command('create')
def create() -> None:
    """Create Globus Auth Scopes related to this service.

    After creating a Globus Auth Client, but before making this service
    available to users, Scopes must be created.  This is an operation that is
    only available through the API.  This command uses the Globus Auth API to
    create required scopes.

    This command is indempotent: If a Scope already exists, it will be skipped.
    """
    import ggm.globus
    import ggm.scope
    clients = ggm.globus.GlobusClients.from_config()
    for (suffix, scope) in ggm.scope.SCOPES.items():
        scope_uri = ggm.scope.uri_for_scope(clients.auth.client_id, suffix)
        if ggm.scope.has_scope_uri(clients.auth, scope_uri):
            print(f"Skipping {scope_uri}")
        else:
            print(f"Creating {scope_uri}…")
            ggm.scope.create_scope(clients.auth, suffix, scope)


@scopes_group.command('list')
@click.option(
    '-d', '--delimiter',
    type=str,
    default=' ',
    help='When there are multiple scopes, use this as the delimiter.',
)
def list(
    delimiter: str,
) -> None:
    """List Globus Auth Scopes associated with this service.

    This lists all of the scopes that a user needs in order to use this
    service.  Scopes are returned as a list of one of more URIs, using the
    delimiter you specify.  If you do not specify a delimiter, the URIs will be
    space-separated.

    NOTE: This is not necessarily the _minimum_ set of scopes required.  This
    is the list of all scopes needed for a user in order to use the entire
    service.

    NOTE: This lists scopes even if they have not been created in Globus Auth.
    """
    import ggm.globus
    import ggm.scope
    clients = ggm.globus.GlobusClients.from_config()
    scopes_list = ggm.scope.scopes_as_list(clients.auth.client_id)
    print(delimiter.join(scopes_list))
