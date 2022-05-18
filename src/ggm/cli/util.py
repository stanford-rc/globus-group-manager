# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# These are utility functions used by CLI commands.
# NOTE: This does not contain the commands themselves!

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

import secrets

import ggm.globus.client


# Log in a user.
def get_user_clients(
) -> ggm.globus.client.GlobusUserClients:
    """Prompt the user to auth and return Globus clients.

    This steps the user through the OAuth 2.0 authorization code flow.  It asks
    the user to go to the appropriate login URL, then to enter the code, which
    is used to make the Globus Clients instance.

    @returns A set of Globus Clients, representing the user.
    """

    # Use a static URI for now
    # TODO: This means the user will have to extract the code from a URL.
    redirect_uri = 'http://localhost/'

    # Make 64 bits of random state
    state = secrets.token_urlsafe()

    # Get the login URL
    login_url = ggm.globus.client.GlobusUserClients.login_url(
        redirect_uri=redirect_uri,
        state=state,
        renewable=False,
    )

    # Prompt for auth and code
    print(f"Please go to {login_url}")
    access_code = input("Enter code: ")

    # Exchange code for tokens, and return!
    return ggm.globus.client.GlobusUserClients.from_auth_code(
        code=access_code,
        redirect_uri=redirect_uri,
        state=state,
        renewable=False,
    )
