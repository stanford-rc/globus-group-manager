# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This module holds the code related to Globus clients.  Each Globus service
# has a separate client.

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

from dataclasses import dataclass
import globus_sdk
import logging

from ggm.environ import config

# Set up logging and bring logging functions into this namespace.
# Also add a Null handler (as we're a library).
logger = logging.getLogger(__name__)
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
exception = logger.exception
logger.addHandler(logging.NullHandler())


@dataclass
class GlobusClients:
    """A base class containing Globus clients

    This is a base class containing the Globus clients that would be used in
    both server and user contexts.  It doesn't provide anything directly, other
    than holding an Auth client and a Groups client.

    This should be subclassed into specialized uses for user and server
    contexts.
    """
    auth: globus_sdk.AuthClient
    groups: globus_sdk.GroupsClient


@dataclass
class GlobusServerClients(GlobusClients):
    mapper: globus_sdk.IdentityMap

    def __init__(
        self,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Return a Globus Groups client, given a Confidential Client ID and Secret.

        @param client_id The Client ID

        @param client_secret The Client secret

        @returns A Globus Groups client, suitable for use with this module.
        """

        # Begin by making an Auth Client for our Confidential App
        globus_client = globus_sdk.ConfidentialAppAuthClient(
            client_id=client_id,
            client_secret=client_secret,
        )

        # Start with the Globus Auth.  Get authorizer and make client.
        #globus_auth_auth = globus_sdk.ClientCredentialsAuthorizer(
        #    confidential_client=globus_client,
        #    scopes=globus_sdk.scopes.AuthScopes.view_identities,
        #)
        globus_auth_auth = globus_sdk.BasicAuthorizer(
            username=client_id,
            password=client_secret,
        )
        self.auth = globus_sdk.AuthClient(
            client_id=client_id,
            authorizer=globus_auth_auth,
        )

        # Do the same 
        globus_groups_auth = globus_sdk.ClientCredentialsAuthorizer(
            confidential_client=globus_client,
            scopes=globus_sdk.scopes.GroupsScopes.all,
        )
        self.groups = globus_sdk.GroupsClient(
            authorizer=globus_groups_auth,
        )

        # Set up our mapper
        self.mapper = globus_sdk.IdentityMap(
            auth_client=self.auth
        )

    @classmethod
    def from_config(
        cls,
    ) -> 'GlobusServerClients':
        """Make Globus Clients from configured ID and Secret.

        Look up the Globus Client ID and Secret from the configuration, and
        instantiate Globus Client objects.
        """
        debug('Creating Globus clients from server config')
        return cls(
            client_id=config['GLOBUS_CLIENT_ID'],
            client_secret=config['GLOBUS_CLIENT_SECRET'],
        )
