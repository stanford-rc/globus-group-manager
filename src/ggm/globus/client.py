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
from typing import Optional, TypedDict
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


class GlobusUserClientsDict(TypedDict):
    auth: str
    groups: str
    user_id: str
    username: str
    provider_id: str
    provider_name: str
    token: str
    refresh: Optional[str]
    expires: int
    last_checked: int

@dataclass
class GlobusUserClients(GlobusClients):
    user_id: UUID
    username: str
    provider_id: UUID
    provider_name: str
    token: str
    refresh_token: Optional[str]
    expires: datetime.datetime
    last_checked: datetime.datetime

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
        debug(f"Creating OAuth 2.0 Auth Code Flow Manager for client {client_id}")
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
        debug(f"Login Step 1 with state '{state}', redirecting to {redirect_uri}")

        # Make the Flow Manager
        flow = GlobusUserClients._login_flow(
            redirect_uri=redirect_uri,
            renewable=renewable,
            state=state,
        )

        # Return the URL
        return flow.get_authorize_url(query_params={
            'session_required_single_domain': config['DOMAIN'],
            'session_required_mfa': True,
        })

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

        Given an authorization code, plus other parameters set up at the start
        of the Flow, get tokens from Globus Auth and use them to instantiate
        our class.

        This also checks the domain of the authenticated user against our
        server-configured domain.

        @param code The Authorization Code.

        @param renewable True if refresh tokens are desired.

        @param state An optional string to be checked at the end of the Flow.

        @raise FileNotFoundError A login was made with the wrong domain.
        """
        debug(f"Login Step 2 with state '{state}'")

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

        # Extract the username, and check against our domain
        username = userinfo['preferred_username']
        username_domain = username.rsplit('@', 1)[1]
        if username_domain != config['DOMAIN']:
            raise FileNotFoundError(f"{username} domain {username_domain} is not the required domain {config['DOMAIN']}")

        # Make and return the instance!
        info(f"Login successful for {username}!")
        return cls(
            auth=auth_client,
            groups=groups_client,
            user_id=UUID(userinfo['sub']),
            username=username,
            provider_id=UUID(userinfo['identity_provider']),
            provider_name=userinfo['identity_provider_display_name'],
            token=ggm_token,
            refresh_token=None,
            expires=datetime.datetime.fromtimestamp(
                tokens[client_id]['expires_at_seconds'],
                tz=datetime.timezone.utc,
            ),
            last_checked=datetime.datetime.now(datetime.timezone.utc),
        )

    # Are tokens valid?
    def _check_tokens(
        self,
        force: bool = False,
    ) -> bool:
        """Check with Globus if tokens are still valid.

        This checks with Globus to see if all tokens in an instance are valid,
        assuming it has been more than APP_TOKEN_CHECK_GRACE seconds since the
        last check.

        .. note: This does not check for expiration, and we do not trigger a
        logout if things fail.  Stuff like that is done by `is_logged_in()`.

        @param force If True, do the check regardless of how long it's been since the last check.

        @return True if the tokens are still valid.
        """
        debug(f"In token check for {self.username}")

        # Should we check?
        should_check = False

        # If our User ID is the null UUID, then we know the tokens are invalid.
        if self.user_id == UUID('00000000-0000-0000-0000-000000000000'):
            debug('Token check for a not-logged-in user')
            return False

        # What time is it now?  How long between checks?
        now = datetime.datetime.now(datetime.timezone.utc)
        check_grace_secs = datetime.timedelta(
            seconds=config['APP_TOKEN_CHECK_GRACE'],
        )

        # Has it been long enough since our last check?
        time_since_last_check = now - self.last_checked
        debug(
            f"Time since last check is {str(time_since_last_check)}, vs. "
            f"grace period of {str(check_grace_secs)}."
        )
        if time_since_last_check >= check_grace_secs:
            info(f"Due to check tokens for {self.username}")
            should_check = True

        # If we force, then definitely check
        if force is True:
            info(f"Forcing check tokens for {self.username}")
            should_check = True

        # If we don't need to check, then assume OK!
        if should_check is False:
            return True

        # If we're here, we need to check

        # Get a Server Auth client to do the check.
        auth_client = GlobusServerClients.from_config().auth

        # If we have a refresh token, check that first.
        can_refresh = False
        if self.refresh_token is not None:
            debug('Checking a refresh token')
            # Hopefully we get a positive response.
            check_response = auth_client.oauth2_validate_token(
                self.refresh_token,
            )
            if (
                'active' in check_response.data and
                check_response.data['active'] is True
            ):
                # We have a good refresh token!
                debug(f"Refresh token for {self.username} is good")
                can_refresh = True
            else:
                # Unfortunately, the check failed
                info(f"Refresh token for {self.username} is revoked")
                return False

        # NOTE: is_logged_in() handles an expiration check, which is why we
        # don't do that here.

        # Now, build the list of access tokens to check
        tokens: set(str) = set((
            self.auth.authorizer.access_token,
            self.groups.authorizer.access_token,
            self.token,
        ))

        # Check each token!
        for token in tokens:
            # This time, we're looking for a negative response.
            check_response = auth_client.oauth2_validate_token(
                token,
            )
            if (
                'active' not in check_response.data or
                check_response.data['active'] is False
            ):
                # We found a token that is not valid.
                # If we can refresh, do so now.  Else we're dead.
                if can_refresh:
                    debug('Found a revoked token, doing refresh')
                    pass # TODO: Trigger refresh
                else:
                    info(f"An access token for {self.username} is revoked")
                    return False

        # We've checked each token, and all are good!
        debug(f"All tokens good for {self.username}!")
        self.last_checked = now
        return True

    # Is the user logged in?
    def is_logged_in(self) -> bool:
        """Check if a client is still logged in

        @return True if the client is still logged in, else False
        """
        debug(f"Login check for {self.username}")

        # If our User ID is the null UUID, we're logged out.
        if self.user_id == UUID('00000000-0000-0000-0000-000000000000'):
            debug('Login check for a not-logged-in user')
            return False

        # What time is it now?
        now = datetime.datetime.now(datetime.timezone.utc)

        # Has the token expired?
        if self.expires <= now:
            info(f"Login check by {self.username} with expired token")
            self.logout()
            return False
        else:
            # The token isn't expired, but does it expire soon?
            early_warning_secs = datetime.timedelta(
                seconds=config['APP_TOKEN_EXPIRES_EARLY'],
            )
            remaining_time = self.expires - now
            if remaining_time <= early_warning_secs:
                info(
                    f"Login check by {self.username} expires in " +
                    f"{str(remaining_time)}, less than {str(early_warning_secs)}"
                )
                self.logout()
                return False
            else:
                debug(f"Login check by {self.username} expires in {str(remaining_time)}")

        # OK, so we're not expired yet.  Have we checked recently enough?
        if self._check_tokens(force=False) is False:
            warning(
                f"Login check by {self.username} has revoked tokens",
            )
            self.logout()
            return False

        # Our tokens have not expired, and we checked them recently.
        # We are logged in!
        debug(f"Login check by {self.username} is logged in!")
        return True

    # A logout method!
    def logout(self) -> None:
        """Log out the user.

        This logs out the user by invalidating all tokens and setting instance
        attributes to values which should clearly indicate that the user has
        been logged out.

        .. note:: This does not log the user out of Globus.
        """
        # What time is it now?
        now = datetime.datetime.now(datetime.timezone.utc)

        # If our User ID is the null UUID, and we're expired, then we're
        # already logged out.
        if (
            self.user_id == UUID('00000000-0000-0000-0000-000000000000') and
            self.expires <= now
        ):
            return
        info(f"Logging out user {self.username}!")

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
        self.last_checked = datetime.datetime.now(datetime.timezone.utc),

        # Clear some other fields
        self.user_id = UUID('00000000-0000-0000-0000-000000000000')
        self.username = 'LOGGED_OUT@example.com'
        self.provider_id = self.user_id
        self.provider_name = 'LOGGED OUT'

        # All done!

    # Methods for converting to/from dict

    def to_dict(self) -> dict:
        debug(f"In to_dict for user {self.username}")
        # Assemble a dict, in a way type-checkers can handle.
        result: GlobusUserClientsDict = {
            'auth': self.auth.authorizer.access_token,
            'groups': self.groups.authorizer.access_token,
            'user_id': str(self.user_id),
            'username': self.username,
            'provider_id': str(self.provider_id),
            'provider_name': self.provider_name,
            'token': self.token,
            'refresh': self.refresh_token,
            'expires': int(self.expires.timestamp()),
            'last_checked': int(self.last_checked.timestamp()),
        }
        return result

    @classmethod
    def from_dict(
        cls,
        src: GlobusUserClientsDict
    ) -> 'GlobusUserClients':
        debug(f"In from_dict for user {src['username']}")

        # Pull out the Auth token and make a client
        auth_authorizer = globus_sdk.AccessTokenAuthorizer(
            src['auth'],
        )
        auth_client = globus_sdk.AuthClient(
            authorizer=auth_authorizer,
        )

        # Pull out the Groups token and make a client
        groups_authorizer = globus_sdk.AccessTokenAuthorizer(
            src['groups'],
        )
        groups_client = globus_sdk.GroupsClient(
            authorizer=groups_authorizer,
        )

        # Make and return the instance
        return cls(
            auth=auth_client,
            groups=groups_client,
            user_id=UUID(src['user_id']),
            username=src['username'],
            provider_id=UUID(src['provider_id']),
            provider_name=src['provider_name'],
            token=src['token'],
            refresh_token=(None if 'refresh' not in src else src['refresh']),
            expires=datetime.datetime.fromtimestamp(
                src['expires'],
                tz=datetime.timezone.utc,
            ),
            last_checked=datetime.datetime.fromtimestamp(
                src['last_checked'],
                tz=datetime.timezone.utc,
            ),
        )
