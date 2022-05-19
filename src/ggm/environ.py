# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This code is used to access configuration variables, either from the
# environment, a local file, or through some other platform.

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

from collections.abc import Mapping
from dotenv import dotenv_values
from functools import cache
import logging
from os import environ
from urllib.parse import urlparse


# This is the list of configuration variables we recognize.
CONFIG_ITEMS = (
    'APP_SECRET',
    'WORKGROUP_STEM',
    'WORKGROUP_API_URL',
    'WORKGROUP_API_KEY',
    'WORKGROUP_API_CERT',
    'GLOBUS_PREFIX',
    'GLOBUS_CLIENT_ID',
    'GLOBUS_CLIENT_SECRET',
)

# This is configuration that is kept in code, as it's very unlikely to change!
STATIC_CONFIG_ITEMS = {
    'APP_TOKEN_CHECK_GRACE': 600, # Check token validity every X seconds
    'APP_TOKEN_EXPIRES_EARLY': 600, # Expire a token X seconds in advance
    'APPS_DOMAIN': 'clients.auth.globus.org',
    'DOMAIN': 'stanford.edu',
}

# This is the list of configuration variables which may be undefined.
OPTIONAL_ITEMS = (
    'GLOBUS_PREFIX',
)

# Set up logging and bring logging functions into this namespace.
# Also add a Null handler (as we're a library).
logger = logging.getLogger(__name__)
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
exception = logger.exception
logger.addHandler(logging.NullHandler())

# Populate the environment first from the local .env file, then from the OS.
ENVIRONMENT = {
    **dotenv_values('.env'),
    **environ,
}


# The main part of this module is the `config` mapping.
# The setup used here is based on how `os.environ` works.
# The `Config` class acts as our mapping.
# Later on, code will be run (during setup) to instantiate `Config` at module
# load-time, under the `config` name.

class Config(Mapping):
    """Accessing program configuraiton.
    """

    # Here are a few simple methods needed for a Mapping
    def __len__(self) -> int:
        """Return the number of recognized configuration items.
        """
        return len(CONFIG_ITEMS) + len(STATIC_CONFIG_ITEMS)

    def __contains__(
        self,
        item
    ) -> bool:
        """Returns True if the given item is a known configuration item.
        """
        if item in CONFIG_ITEMS or item in STATIC_CONFIG_ITEMS:
            return True
        else:
            return False

    # Fetch a configuration item
    def __getitem__(
        self,
        item: str
    ) -> str:
        """Fetch and return a configuration variable.

        @param item The configuration item to return.

        @raise KeyError The configuration item is not recognized.

        @raise ValueError The configuration item is not present in the environment.

        @raise ImportError An optional package is required.

        @raise FileNotFoundError The configuration variable could not be looked up; the URL could not be resolved.

        @raise RuntimeError A configuration variable could not be looked up.  See the exception string for more details.
        """
        debug(f"Getting config item '{item}'")

        # Check if we're fetching a valid item.
        if item not in self:
            raise KeyError(f"Unknown item {item}")

        # If we are fetching a static item, return it immediately.
        if item in STATIC_CONFIG_ITEMS:
            return STATIC_CONFIG_ITEMS[item]
        debug(f"Config item {item} is not static")

        # From this point on, we're pulling from the environment, so make sure
        # it's there.
        if item not in ENVIRONMENT:
            if item in OPTIONAL_ITEMS:
                return ''
            else:
                raise ValueError(f"{item} not in environment")

        environ_value = ENVIRONMENT[item]
        environ_urlparsed = urlparse(environ_value, allow_fragments=False)

        # Handle known URL schemes
        if environ_urlparsed.scheme == 'file':
            # Format is file:path or file:/path
            try:
                return self._fetch_from_file(environ_urlparsed.path)
            except Exception:
                raise RuntimeError(f"Could not read secret from {environ_urlparsed.path}")
        elif environ_urlparsed.scheme == 'gcs':
            # Format is gcs://project/name?version
            try:
                return self._fetch_from_gcs(
                    project=environ_urlparsed.netloc,
                    name=environ_urlparsed.path.lstrip('/'),
                    version=environ_urlparsed.query,
                )
            except ImportError as e:
                raise e
            except FileNotFoundError as e:
                raise e
            except PermissionError as e:
                raise e
            except Exception:
                raise RuntimeError(f"Could not read secret {environ_urlparsed.path} "
                              f"version {environ_urlparsed.query} "
                              f"from GCS project {environ_urlparsed.netloc}"
                )
        else:
            # For all other schemes (including 'no scheme found'), return the value
            # pulled in from the environment.
            debug("Returning value from environment")
            return environ_value


    # The iterator is required by the Mapping ABC
    def __iter__(self):
        """Iterate over the known configuration items, names and values.
        """
        for key in CONFIG_ITEMS:
            yield key
        for key in list(STATIC_CONFIG_ITEMS.keys()):
            yield key


    # Fetch a configuration item from a file
    @staticmethod
    @cache
    def _fetch_from_file(
        path: str,
    ) -> str:
        """Fetch a configuration item from a file.

        NOTE: The final newline from the file will be stripped.  Multi-line
        files will have all lines read in to the returned string, and the last
        newline will still be stripped.

        @param The path of the file to read.

        @returns The contents of the file, decoded as ASCII.

        @raise FileNotFoundError Could not find a file at the given path.

        @raise PermissionError Could not open the file at the given path.

        @raise IOError I/O Error reading file.
        """
        debug(f"Fetching secret from file at {path}")
        file = open(
            path,
            mode='r',
            encoding='ascii',
        )
        contents = file.read(-1).rstrip("\n")
        file.close()
        return contents


    # Fetch a configuration item from Google Cloud Secrets Manager
    @staticmethod
    @cache
    def _fetch_from_gcs(
        project: str,
        name: str,
        version: str,
    ) -> str:
        """Fetch an environment variable from Google Cloud Secret Manager.

        This fetches an environment variable from Google Cloud Secret Manager.
        The 

        @param project The Google Cloud project name.

        @param name The Google Cloud secret name.

        @param version The Google Cloud secret version.  This is often "latest".

        @returns The contents of the secret, decoded as ASCII.

        @raises ImportError Reinstall this package with the 'GCS' option.
        """
        debug(f"Fetching GCS Project {project} Secret {name} version {version}")

        # Import the Secret Manager code and instantiate a client
        import google.cloud.secretmanager
        import google.api_core.exceptions

        secrets = google.cloud.secretmanager.SecretManagerServiceClient()
        try:
            secret_bytes = secrets.access_secret_version(
                name=f"projects/{project}/secrets/{name}/versions/{version}",
            ).payload.data
            return secret_bytes.decode('ascii')
        except google.api_core.exceptions.NotFound:
            raise FileNotFoundError(f"Google Cloud secret projects/{project}/secrets/{name}/versions/{version} does not exist")
        except google.api_core.exceptions.Forbidden:
            raise PermissionError(f"Permission denied to Google Cloud secret projects/{project}/secrets/{name}/versions/{version}")


# This sets up `config`.
# Make a function to instantiate `Config`, call it, and then delete the
# function.
def _config() -> Config:
    return Config()
config = Config()
del _config
