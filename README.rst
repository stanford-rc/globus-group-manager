=============================
Stanford Globus Group Manager
=============================

The Stanford Globus Group Manager (SGGM) is used to create `Globus Groups`_,
create matching `Stanford Workgroups`_, and keep the former's membership in
sync with the latter.  These are known as "Workgroup-linked Globus Groups",
"linked Globus Groups", or simply "linked groups".

.. _Globus Groups: https://www.globus.org/platform/services/groups
.. _Stanford Workgroups: https://uit.stanford.edu/service/workgroup

Goals
-----

SGGM has the following goals.

* **Support creation by Stanford users.**
  Groups may be created by anyone with a valid SUNetID.
  I am also considering making "… trusted Confidential Clients" part of
  the goal.  This would allow for Globus Confidential Clients to create linked
  groups

* **Workgroups are the source of truth for membership.**
  When a Globus Group is synced, by the end of the sync, the only members of
  the Globus Group will be members of the Workgroup, along with any
  Confidential Clients that are administrators.  Globus Group members will be
  added and removed as needed to bring it in sync with the Workgroup.

* **Globus Groups are the source of truth for Workgroup descriptions.**
  The Workgroup description will be pulled from the Globus Group's short
  description, with the Globus Group's UUID added.

* **Globus Groups are updated every 30 minutes.**
  Changes to Workgroup membership are reflected in the Globus Group's
  membership within 30 minutes of the Workgroup change, assuming all systems
  are operating normally.  This is in line with other UIT-provided batch
  services, such as DNS.

Non-Goals
^^^^^^^^^

SGGM has a number of non-goals, set intentionally.

* **Globus Group membership only comes from Workgroup membership.**
  Other than the Globus Confidential Client for the SGGM service, and possibly
  other Confidential Clients, the only members of the Globus Group will be the
  members of the workgroup.  If another person is somehow added to the Globus
  Group, that person would be removed during the next sync with the Workgroup.

  If you want to give non-SUNetIDs access to something via a Group, you will
  need to make your own Globus Group to hold those non-SUNetID members.  Most
  parts of Globus that allow Globus Groups will allow multiple Globus Groups.

* **Workgroup names are controlled by SGGM; only one stem is used.**
  SGGM needs some way to ensure that it is looking at the correct Workgroup.
  The unique identifier for workgroups is the workgroup's name.  So, SGGM has
  full control over what name it gives to the Workgroup.

  Also, linked groups only exist within one Workgroup stem, ``globus:``.  This
  is to limit the parts of Workgroup Manager that need to be searched for
  workgroups and changes.

  In the future, if Globus Groups is made into a fully-supported integration,
  this non-goal will be removed.

* **One workgroup per Globus Group.**
  Each Globus Group is synced to only one Workgroup.  This matches how other
  integration work.

* **Globus Groups are not synced in real-time.**  There is currently no support
  for SGGM being notified whenever a Workgroup changes.  So, SGGM cannot
  receive real-time notice of Workgroups updating.

Major Version
-------------

SGGM will exist in three major versions.

* **SGGM version 1** is this version.  The ``main1`` branch contains the latest
  code for this series.

* **SGGM version 2** will be similar to version 1, but will support being
  notified of Workgroup changes in real-time.  The non-goal for real-time
  updating will disappear, and the goal for changes to be applied every 30
  minutes will also change.

  This requires work on the Workgroups side to send 'workgroup changed'
  notifications to SGGM.

  When SGGM version 2 work begins, it will take place in the ``main2`` branch.
  Eventually the ``main1`` branch will be archived, and stop receiving updates.

* **SGGM version 3** will be a major change to SGGM.  With SGGM version 3, SGGM
  will no longer exist as a separate product that users interact with.
  Instead, users would request a Globus Groups integration through Workgroup
  Manager.  The Workgroup would become the source of truth for Globus Group
  name, description, and membership.

  It is entirely possible that SGGM version 3 will not exist as a downloadable
  product.  Instead, it is likely to be integrated as part of Stanford's
  Workgroup Manager and related systems.  If that happens, this entire
  repository will be archived.

Documentation
-------------

Documentation for the head of the currently-active branch may be found at
`<https://stanford-rc.github.io/globus-group-manager/>`_.

Copyright & License
-------------------

The contents of this repository are © 2022 The Board of Trustees of the Leland
Stanford Junior University.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

A copy of the GNU Affero General Public License should be in the ``LICENSE``
file in the root of this repository.  If not, see
<https://www.gnu.org/licenses/>.

In addition, for the documentation, Permission is granted to copy, distribute
and/or modify this document under the terms of the GNU Free Documentation
License, Version 1.3; with no Invariant Sections, no Front-Cover Texts, and no
Back-Cover Texts.  A copy of the license is included in the file named
``LICENSE``, located in the ``docs`` folder.  If not, see
<https://www.gnu.org/licenses/>.

Configuration
-------------

Core configuration is provided through environment variables.  This section
describes the environment variables which must be populated, and how the data
may be stored or accessed.

Required Variables
^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^

* ``GLOBUS_PREFIX``: If present, this string will be included in created Globus
  Group names, and in Workgroup descriptions.  It is meant to denote
  non-production, so the convention is to leave this variable un-set in the
  producton environment.

  If set, the value will be uppercased and placed in square brackets at the
  start of the Globus Group's name, in the format "[$prefix] …".  In the
  Workgroup, it will be lowercased and placed at the start of the Workgroup
  description in the format "$prefix environment—".

Hard-Coded Variables
^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^

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
^^^^^^^^^

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

Installation
------------

This program can be installed and run in multiple ways. 

Virtualenv
^^^^^^^^^^

To install from a Python virtual environment, download a repository export to a
local directory, create a venv, and install the code into that venv.

.. code-block:: shell

   python3.9 -m venv .
   . bin/activate
   pip install --upgrade pip
   pip install .

As long as the venv is active in your shell, the ``sggm`` command will be
available.

In this situation, we suggest using a dotenv file to store configuration.

.. warning:: Use caution when working from a Git worktree (that is, the result of a ``git clone``.  Running in a Git worktree introduces the possibility of running unexpected code, or committing secrets.
