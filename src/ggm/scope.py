# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# A Globus Auth Scope is used to authorize working with SGGM.  This code is
# responsible for setting up that Scope.  The code supports a future where
# there are multiple scopes.  It supports creating scopes, checking if scopes
# already exist, and getting scope URIs.

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

from functools import cache
import globus_sdk
from typing import *
from uuid import UUID

from ggm.environ import config

# These are the types of tuples that hold information about our scopes.
class DependentScopeURI(NamedTuple):
    uri: str
    optional: bool = False
    requires_refresh_token: bool = False
class DependentScopeUUID(NamedTuple):
    uuid: UUID
    optional: bool = False
    requires_refresh_token: bool = False
class ScopeInfo(NamedTuple):
    name: str
    description: str
    advertised: bool
    allows_refresh_token: bool
    dependent_scopes: Collection[Union[DependentScopeURI,DependentScopeUUID]]

# This is the list of scopes that we use in our application.
# The ScopeInfo class explains what fields each scope must have.
# The list of dependent scopes can be empty, and it can contain scopes
# identified by URI or by UUID.
SCOPES: Dict[str, ScopeInfo] = {
    'manage_linked_workgroups': ScopeInfo(
        name = 'Workgroup-linked Globus Groups',
        description = 'Create and manage Globus Groups linked to Stanford Workgroups',
        advertised = False,
        allows_refresh_token = True,
        dependent_scopes = (
            DependentScopeURI(
                uri='urn:globus:auth:scope:groups.api.globus.org:all',
                optional=False,
                requires_refresh_token=False,
            ),
        ),
    ),
}


# Check if a Scope URI exists in Globus Auth.
def has_scope_uri(
    client: globus_sdk.AuthClient,
    uri: str,
) -> bool:
    """Check if a Scope URI exists.

    This does not actually return the details of the scope, it just checks if
    the scope exists.

    @param client A Globus Auth client

    @param uri The Scope URI

    @return True if a scope with that URI exists, else False.
    """

    # Look up our scope
    lookup_response = client.get('/v2/api/scopes',
        query_params={
            'scope_strings': uri,
        }
    )
    if lookup_response.http_status != 200:
        raise Exception # TODO
    if len(lookup_response['scopes']) > 1:
        raise Exception # TODO
    return True if len(lookup_response['scopes']) == 1 else False


# Create a scope, given a Globus Auth Client, a Suffix, and scope details.
def create_scope(
    client: globus_sdk.AuthClient,
    suffix: str,
    scope: ScopeInfo,
) -> None:
    """Create a Globus Auth Scope for a Client.

    This creates a single new Globus Auth Scope.

    @param client A Globus Auth client

    @param suffix The Scope Suffix, which—combined with the Client ID—will form the Scope's URI.

    @param scope The details of the Scope to create.
    """

    # Prepare a scope request
    scope_request = {
        'scope_suffix': suffix,
        'name': scope.name,
        'description': scope.description,
        'dependent_scopes': list(),
        'advertised': scope.advertised,
        'allows_refresh_token': scope.allows_refresh_token,
    }

    # Go through the dependent scopes, converting URIs to UUIDs
    for dependent_scope in scope.dependent_scopes:
        # How we populate the request's list of dependent scopes depends on
        # what information we have already.
        if isinstance(dependent_scope, DependentScopeUUID):
            # If we already have a Scope ID, we just have some fields to copy.
            scope_request['dependent_scopes'].append({
                'scope': str(dependent_scope.uuid),
                'optional': dependent_scope.optional,
                'requires_refresh_token': dependent_scope.requires_refresh_token,
            })

        elif isinstance(dependent_scope, DependentScopeURI):
            # If we have a Scope URI, we need to convert that into a Scope ID.
            lookup_response = client.get('/v2/api/scopes',
                query_params={'scope_strings': dependent_scope.uri}
            )
            if lookup_response.http_status != 200:
                raise Exception # TODO
            if len(lookup_response['scopes']) != 1:
                raise Exception # TODO

            # Create an entry in a temporary list, with UUID instead of URI
            scope_request['dependent_scopes'].append({
                'scope': lookup_response['scopes'][0]['id'],
                'optional': dependent_scope.optional,
                'requires_refresh_token': dependent_scope.requires_refresh_token,
            })

        else:
            # If we have some other type, fail.
            return NotImplementedError('Entry in scope.dependent_scopes is unknown type')

    # Create the scope
    scope_response = client.post(f"/v2/api/clients/{client.client_id}/scopes",
        data={'scope': scope_request},
    )
    if scope_response.http_status != 201:
        raise Exception # TODO


# Given a Client and a Suffix, return a Scope URI.
# NOTE: This does not actually check if the Scope exists.
def uri_for_scope(
    client_id: Union[str, UUID],
    suffix: str,
) -> str:
    """Return a URI for a given scope Client ID and Suffix.

    Scopes in Globus are identified by a UUID and a URI (also known as the
    "scope string").  This helper function constructs a URI from a Client ID
    and Suffix.

    @param client_id The Client ID which owns the scope.

    @param suffix The scope suffix.

    @return A Scope URI
    """
    if isinstance(suffix, UUID):
        client_id_str = str(client_id)
    else:
        client_id_str = client_id
    return f"https://auth.globus.org/scopes/{client_id_str}/{suffix}"

# Return the required scope URIs, either as a sequence or as a list

def scopes_as_list(
    client_id: Union[str, UUID],
) -> Collection[str]:
    return list(uri_for_scope(client_id, k) for k in SCOPES.keys())

def scopes_as_str(
    client_id: Union[str, UUID],
) -> str:
    return " ".join(scopes_as_list(client_id))
