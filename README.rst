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

