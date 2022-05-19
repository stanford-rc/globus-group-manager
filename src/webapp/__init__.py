# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This is the root of the Stanford Globus Group Manager webapp!

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

import flask
from flask import abort, Flask, g, redirect, render_template, request, session, url_for
from flask.logging import default_handler
import json
import logging
import os
import secrets
from typing import Any, cast
import urllib.parse

from ggm.globus.client import GlobusUserClients, GlobusUserClientsDict
from ggm.environ import config


# Create our Flask webapp
app = Flask(__name__)

# Create JSON handlers for GlobusUserClients
class JSONEncoder(flask.json.JSONEncoder):
    def default(
        self,
        o: Any
    ) -> Any:
        # We catch all GlobusUserClients instances, converting them to dict
        if isinstance(o, GlobusUserClients):
            result = o.to_dict()
            result['_type'] = 'GlobusUserClients'
            return result
        else:
            return super().default(o)
class JSONDecoder(flask.json.JSONDecoder):
    # We set ourselves up by inserting a custom object hook, called after JSON
    # object are deserialized.  We also make a note of any existing hook.
    def __init__(self, **kwargs):
        # Capture any parent object hook
        self.parent_object_hook = None
        if 'object_hook' in kwargs:
            self.parent_object_hook = kwargs['object_hook']
            del kwargs['object_hook']
        super().__init__(
            object_hook=self.decode_dict,
            **kwargs
        )
    # On every dict, if we recognize it, decode it.  Else passs to parent hook.
    def decode_dict(
        self,
        dct: dict[Any, Any],
    ) -> Any:
        if '_type' in dct and dct['_type'] == 'GlobusUserClients':
            dct = cast(GlobusUserClientsDict, dct)
            return GlobusUserClients.from_dict(dct)
        else:
            if self.parent_object_hook is not None:
                return self.parent_object_hook(dct)
# Install the JSON encoder & decoder
app.json_encoder = JSONEncoder
app.json_decoder = JSONDecoder

# Set up the root logger's log level
root_logger = logging.getLogger()
if 'LOG_LEVEL' in os.environ:
    root_logger.setLevel(os.environ['LOG_LEVEL'])
# Make Flask's handler the default handler for everything
app.logger.removeHandler(default_handler)
root_logger.addHandler(default_handler)

# Effectively disable logging in the libraries we use.
logging.getLogger('urllib3').setLevel('CRITICAL')
logging.getLogger('globus_sdk').setLevel('CRITICAL')

# Set up logging
logger = app.logger
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
exception = logger.exception

# Load the app secret
try:
    app.secret_key = config['APP_SECRET'].encode('UTF-8')
    app.logger.debug('Using session key from config')
except ValueError:
    app.logger.warning('Generating one-time session key')
    app.secret_key = secrets.token_bytes()

# Set a before-request to check if the user is logged in.
@app.before_request
def is_logged_in() -> None:
    # Make sure at least something is in g
    g.clients = None

    # If we have a client object, and it's logged in, put it into g
    if 'clients' in session:
        if session['clients'].is_logged_in():
            # clients could have been modified by the login check.
            session.modified = True
            g.clients = session['clients']
        else:
            # We have clients, but not logged in, so clean them up
            del session['clients']

# Time to actually route traffic!

@app.route('/')
def hello():
    # If we have clients, check if they're valid
    return render_template('hello.html',
        name=(g.clients.username if g.clients is not None else None)
    )

@app.route('/login', methods=['GET'])
def login_begin():
    # Generate a secret value for state, and store it in session
    state = secrets.token_urlsafe()
    session['login_state'] = state

    # If we have a URL to send the client to after login, save it in session.
    if 'login_url' in request.args:
        session['login_url'] = urllib.parse.quote(request.args['login_url'])

    # Get our /login/complete URL
    redirect_url = url_for('login_end', _external=True)

    # Send the user to the URL
    return redirect(GlobusUserClients.login_url(
        redirect_uri=redirect_url,
        renewable=False,
        state=state,
    ))


@app.route('/login/complete', methods=['GET'])
def login_end():
    # Make sure we have both a code and state
    if 'code' not in request.args:
        warning('Missing code')
        abort(400)
    if 'state' not in request.args:
        warning('Missing state from URL')
        abort(400)
    if 'login_state' not in session:
        warning('Missing state from session')
        abort(400)

    # Pull the state from the session
    session_state = session['login_state']
    del session['login_state']

    # Make sure our session state matches the request state
    if session_state != request.args['state']:
        warning('Session state does not match URL state')
        abort(401)

    # Get our /login/complete URL
    redirect_url = url_for('login_end', _external=True)

    # Exchange code for tokens
    try:
        clients = GlobusUserClients.from_auth_code(
            code=request.args['code'],
            redirect_uri=redirect_url,
            renewable=False,
        )
    except Exception:
        exception('Error exchanging code for tokens')
        abort(401)

    # Add this to the session, and to g!
    session['clients'] = clients
    g.clients = session['clients']

    # Send the user along!
    if 'login_url' in session:
        login_url = urllib.parse.unquote(
            session['login_url'],
        )
        del session['login_url']
    else:
        login_url = url_for('hello', _external=True)
    return redirect(login_url)


@app.route('/logout', methods=['GET'])
def logout():
    # Do we have any clients?
    if 'clients' in session:
        info(f"Logout for {session['clients'].username}")

        # Start by logging out the user and deleting from the session
        session['clients'].logout()
        del session['clients']

        # Send them to Globus to finish logout
        globus_logout_url = 'https://auth.globus.org/v2/web/logout'
        globus_logout_query = {
            'client_id': config['GLOBUS_CLIENT_ID'],
            'redirect_uri': url_for('hello', _external=True),
            'redirect_name': 'Globus Group Manager',
        }
        globus_logout_query_string = urllib.parse.urlencode(
            globus_logout_query,
            encoding='utf-8',
            quote_via=urllib.parse.quote,
            safe='',
        )

        # Do the redirect!
        return redirect(
            globus_logout_url + '?' + globus_logout_query_string
        )
    else:
        # If they're already logged out, just send them home.
        debug('Logout called for no user')
        return redirect(url_for('hello'))
