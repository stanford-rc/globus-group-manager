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
import datetime
import globus_sdk
import logging
from typing import Optional
from uuid import UUID

from ggm.environ import config
from ggm.scope import scopes_as_list

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
        self.auth = globus_client
        #globus_auth_auth = globus_sdk.ClientCredentialsAuthorizer(
        #    confidential_client=globus_client,
        #    scopes=globus_sdk.scopes.AuthScopes.view_identities,
        #)
        #globus_auth_auth = globus_sdk.BasicAuthorizer(
        #    username=client_id,
        #    password=client_secret,
        #)
        #self.auth = globus_sdk.AuthClient(
        #    client_id=client_id,
        #    authorizer=globus_auth_auth,
        #)

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


@dataclass
class GlobusUserClients(GlobusClients):
    user_id: UUID
    username: str
    provider_id: UUID
    provider_name: str
    token: str
    refresh_token: Optional[str]
    expires: datetime.datetime

    # Client login support method for making Flow Managers
    @staticmethod
    def _login_flow(
        redirect_uri: str,
        renewable: bool,
        state: str,
    ) -> globus_sdk.services.auth.flow_managers.GlobusOAuthFlowManager:
        """Return a Globus Auth Flow Manager suitable for user authentication.

        This does the work of creating the Flow Manager, since these actions
        happen at both ends of the OAuth 2.0 flow.

        @param renewable True if refresh tokens are desired.

        @param state An optional string to be checked at the end of the Flow.

        @returens A Flow Manager, suitable for URL and token generation.
        """

        # Begin by making an Auth Client for our Confidential App
        client_id = config['GLOBUS_CLIENT_ID']
        globus_client = globus_sdk.ConfidentialAppAuthClient(
            client_id=client_id,
            client_secret=config['GLOBUS_CLIENT_SECRET'],
        )

        # Return the flow!

        return globus_client.oauth2_start_flow(
            redirect_uri=redirect_uri,
            requested_scopes = scopes_as_list(client_id),
            state=state,
            refresh_tokens=renewable,
        )

    # Client login step 1: Get a login URL
    @staticmethod
    def login_url(
        redirect_uri: str,
        renewable: bool = False,
        state: str = '_default',
    ) -> str:
        """Return a URL for authenticating to Globus.

        @param redirect_uri The URI to send the client after authentication.

        @param renewable True if refresh tokens are desired.

        @param state An optional string to be checked at the end of the Flow.
        """
        # Make the Flow Manager
        flow = GlobusUserClients._login_flow(
            redirect_uri=redirect_uri,
            renewable=renewable,
            state=state,
        )

        # Return the URL
        return flow.get_authorize_url()

    # Client login step 2: Convert an authorization code into tokens
    @classmethod
    def from_auth_code(
        cls,
        code: str,
        redirect_uri: str,
        renewable: bool = False,
        state: str = '_default',
    ) -> 'GlobusUserClients':
        """Instantiate clients using an OAuth 2.0 authorization code.

        @param code The Authorization Code.

        @param renewable True if refresh tokens are desired.

        @param state An optional string to be checked at the end of the Flow.
        """

        # TODO: Handle renewable tokens
        if renewable is True:
            raise NotImplementedError('Renewable tokens')

        # Make the Flow Manager
        flow = GlobusUserClients._login_flow(
            redirect_uri=redirect_uri,
            renewable=renewable,
            state=state,
        )

        # Exchange the code
        try:
            tokens = flow.exchange_code_for_tokens(code).by_resource_server
        except Exception:
            pass # TODO

        # Pull out the Auth token and make a client
        auth_authorizer = globus_sdk.AccessTokenAuthorizer(
            tokens['auth.globus.org']['access_token']
        )
        auth_client = globus_sdk.AuthClient(
            authorizer=auth_authorizer,
        )

        # Pull out the Groups token and make a client
        groups_authorizer = globus_sdk.AccessTokenAuthorizer(
            tokens['groups.api.globus.org']['access_token']
        )
        groups_client = globus_sdk.GroupsClient(
            authorizer=groups_authorizer,
        )

        # Pull out our token
        client_id = config['GLOBUS_CLIENT_ID']
        ggm_token = tokens[client_id]['access_token']
        ggm_expires = tokens[client_id]['expires_at_seconds']

        # Use the Auth client to get OIDC information
        userinfo = auth_client.oauth2_userinfo().data

        # Make and return the instance!
        return cls(
            auth=auth_client,
            groups=groups_client,
            user_id=UUID(userinfo['sub']),
            username=userinfo['preferred_username'],
            provider_id=UUID(userinfo['identity_provider']),
            provider_name=userinfo['identity_provider_display_name'],
            token=ggm_token,
            refresh_token=None,
            expires=datetime.datetime.fromtimestamp(
                tokens[client_id]['expires_at_seconds'],
                tz=datetime.timezone.utc,
            ),
        )

    # A logout method!
    def logout(self) -> None:
        # Assemble a list of tokens to revoke
        tokens: set(str) = set((
            self.auth.authorizer.access_token,
            self.groups.authorizer.access_token,
            self.token,
        ))

        # Add the refresh token, if we have one
        if self.refresh_token is not None:
            tokens.add(self.refresh_token)

        # Get a server Auth client
        server_auth = GlobusServerClients.from_config().auth

        # Do the revocations
        for token in tokens:
            server_auth.oauth2_revoke_token(token)

        # Clear the refresh token and set expires to now
        self.refresh_token = None
        self.expires = datetime.datetime.now(datetime.timezone.utc)

        # Clear some other fields
        self.user_id = UUID('00000000-0000-0000-0000-000000000000')
        self.username = 'LOGGED_OUT@example.com'
        self.provider_id = self.user_id
        self.provider_name = 'LOGGED OUT'

        # All done!
