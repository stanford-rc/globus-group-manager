Configuration
=============

Core configuration is provided through environment variables.  This section
describes the environment variables which must be populated, and how the data
may be stored or accessed.

Required Variables
------------------

* ``WORKGROUP_STEM``: This is the name of the Workgroup stem that will be used to
  hold SGGM-created Workgroups.  The trailing colon must *not* be present.

* ``WORKGROUP_API_TIER``: The tier to use for the Workgroups API.  This can
  either be 'PROD' or 'UAT'.

* ``WORKGROUP_API_KEY``: The private key used to connect to the Workgroups API.
  This key needs to be PEM-encoded, with no encryption passphrase.

* ``WORKGROUP_API_CERT``: The certificate—matching the private key set in
  ``WORKGROUP_API_KEY``—to use for authenticating to the Workgroups API.  It
  must also be PEM-encoded.

* ``GLOBUS_CLIENT_ID``: The ID of the Globus Auth Confidential Client used by
  this application.

* ``GLOBUS_CLIENT_SECRET``: A Client Secret for the Globus Auth Confidential
  Client.

Optional Variables
------------------

* ``GLOBUS_PREFIX``: If present, this string will be included in created Globus
  Group names, and in Workgroup descriptions.  It is meant to denote
  non-production, so the convention is to leave this variable un-set in the
  producton environment.

  If set, the value will be uppercased and placed in square brackets at the
  start of the Globus Group's name, in the format "[$prefix] …".  In the
  Workgroup, it will be lowercased and placed at the start of the Workgroup
  description in the format "$prefix environment—".

Hard-Coded Variables
--------------------

Some settings are hard-coded, because it is very unlikely that they will
change.

* ``APPS_DOMAIN``: All Globus Identity usernames take the form of
  ``user@domain``.  Every Globus Auth Confidential Client has its own Globus
  Identity, in a common domain.  This setting holds that common domain.  Right
  now it is ``clients.auth.globus.org``.

* ``DOMAIN``: Every Stanford person has a Globus Identity in a common domain.
  This setting holds that domain.  Right now it is ``stanford.edu``.

  .. note:: Stanford people who log in to Globus via Google will have an Identity username of the form ``sunetid@stanford.edu@accounts.google.com``.  This setting does not recognize those Globus Identities as Stanford people, so clients will need to take care to check that users are logging in via "Stanford University", not via SAML.


Value Formats
-------------

For some environment variables, it is not safe storing the actual value in the
environment variable.  For this reason, all values are first parsed through
Python's ``urlparse`` function.  If a recognized scheme is found, the value of
the environment variable is taken as a URL to find the variable's *actual*
value.

The following schemes are recognized:

* **Files**: If the scheme is ``file``, the value is taken as a path to a file.

  The format is ``file:path`` for paths relative to the current working
  directory, and ``file:/path`` for absolute paths.

* **Google Cloud Secrets**: If the scheme is ``gcs``, the value is taken from a
  Secret in Google Cloud Secret Manger.

  The format is ``gcs://project/name?version``.  All three components are
  required, but you can use the special string "latest" to refer to the latest
  version of a specific Secret.

  This required that SGGM is built with the ``gcs`` option.

.env File
---------

In local installations, it is possible to put configuration into a local file,
named ``.env``.  That file should be placed in the project's root directory
(whatever that means for your installation).

Here is an example dotenv file:

.. code-block:: ini

   GLOBUS_PREFIX=DEV
   GLOBUS_CLIENT_ID=67a9fc42-cbe6-11ec-9a66-bb2cbd847dfd
   GLOBUS_CLIENT_SECRET=gcs://myproject/globus?latest

   WORKGROUP_STEM=globus
   WORKGROUP_API_TIER=UAT
   WORKGROUP_API_CERT=file:workgroup.pem
   WORKGROUP_API_KEY=gcs://myproject/workgroup?latest

The contents of the "dotenv" file are read when the program is first started,
and will be overridden by variables that are set in the actual environment.  In
other words, if your dotenv file sets ``GLOBUS_PREFIX`` to "a", and the OS
environment sets it to "b", the actual value used will be "b".

Both the dotenv file and the OS environment are read at program start only, so
a full program restart is needed in order to pick up changes.
