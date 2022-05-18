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
from flask import abort, Flask, redirect, render_template, request, session, url_for
import json
import secrets
from typing import Any, cast

from ggm.globus.client import GlobusUserClients, GlobusUserClientsDict
from ggm.environ import config


# Create our Flask webapp
app = Flask(__name__)

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

# Time to actually route traffic!

@app.route('/')
def hello():
    return "Hello!"
