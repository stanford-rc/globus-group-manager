# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This holds the code used to work with Globus Groups.

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

from collections.abc import Collection, Iterator, Set
from dataclasses import dataclass
from itertools import chain
from typing import NamedTuple, Optional, Union
from uuid import UUID

import globus_sdk

from ggm.globus.client import GlobusClients
from ggm.environ import config


# Functions to add or remove domains from Globus Identity Usernames
def scope_usernames(
    users: Collection[str],
    domain: str,
) -> Iterator[str]:
    """Scope a collection of users (adding a domain).

    @param users The collection of users needing to be scoped.

    @param domain The domain to add.
    """
    for user in users:
        yield user + '@' + domain

def descope_usernames(
    usernames: Collection[str],
    domain: Optional[str] = None,
) -> Iterator[str]:
    """De-scope a collection of usernames (removing a domain).

    @param usernames The collectin of usernames to be de-scoped.

    @param domain An optional domain to check for.

    @raise KeyError If the username's domain does not match the expected domain.
    """
    for username in usernames:
        (username_user, username_domain) = username.split('@')
        if domain is not None and username_domain != domain:
            raise KeyError(username)
        yield username_user


# Create a Globus Group
def create_group(
    client: GlobusClients,
    name: str,
    high_risk: bool,
    additional_admins: Collection[Union[UUID, str]] = list(),
    description: Optional[str] = None,
) -> tuple[UUID, Optional[Exception]]:
    """Create a Globus Group and return its UUID.

    This creates a new Globus Group, provisions it, adds optional
    administrators, and returns the UUID of the group.

    Created groups are configured to only allow people to be added by a group
    administrator or manager.  Group members can see the list of other members,
    but the group itself is private (it will not appear in searches made by
    non-members).  If a group is marked 'high-risk', it is marked as a High
    Assurance group.

    By default, only the Confidential Client used to create the group will be
    in the list of administrators.  To allow others to administer the group,
    include a collection of either Globus Identity UUIDs, or Globus Identity
    Usernames; the latter will be converted to UUIDs.  If a string is provided
    that is not an existing Globus Identity, a new Globus Identity will be
    provisioned, using the string as the Identity Username.

    @param name The name of the group.

    @param description An optional description.

    @param high_risk True if used for High Risk data, else False.

    @param additional_admins A list of additional administrators, as identity usernames or UUIDs.

    @returns The group's UUID, along with any errors encountered after initial creation.  If errors are encountered, the client should delete the group and start again.

    @raises AssertionError One of the required strings is empty.

    @raises KeyError One of the UUIDs provided does not exist.

    @raises PermissionError Permission error creating group.

    @raises IOError Issue communicating with Globus APIs.
    """

    # Make sure our strings are not empty
    assert(len(name) > 0)
    if description is not None:
        assert(len(description) > 0)

    # If we have a prefix, add it to the name.
    if config['GLOBUS_PREFIX'] != '':
        real_name = '[' + config['GLOBUS_PREFIX'] + '] ' + name
    else:
        real_name = name

    # Do we have additional admins?  Validate each one and get the UUIDs.

    # Do we have additional admins?  Check and convert to UUIDs.
    # First, seed them into the mapper.  Then, do the lookup.
    for admin in additional_admins:
        client.mapper.add(admin)
    admin_uuids: set[UUID] = set()
    for admin in additional_admins:
        try:
            admin_uuids.add(UUID(client.mapper[admin]['id']))
        except KeyError:
            raise
        except globus_sdk.GlobusAPIError as e:
            if e.http_status == 500:
                raise IOError(f"Globus API transient error looking up {admin}")
            else:
                raise IOError(f"Unknown error looking up {admin}: {e.code}-{e.message}")
        except globus_sdk.NetworkError as e:
            raise IOError(f"Network issue looking up {admin}")

    # Make the group!
    create_request = {
        'name': real_name,
    }
    if description is not None:
        create_request['description'] = description
    try:
        create_response = client.groups.create_group(data=create_request)
    except globus_sdk.GlobusAPIError as e:
        if e.http_status == 404:
            raise KeyError(group_id)
        elif e.http_status in (401, 403):
            raise PermissionError(group_id)
        elif e.http_status == 500:
            raise IOError(f"Globus API transient error creating Group '{description}'")
        else:
            raise IOError(f"Unknown error in creation of Group '{description}': {e.code}-{e.message}")
    except globus_sdk.NetworkError as e:
        raise IOError(f"Network issue creating Group '{description}'")
    if create_response.http_status == 201:
        group_id = UUID(create_response['id'])
    else:
        raise IOError(f"Unknown error in creation of Group '{description}': {create_response.code}-{create_response.message}")

    # NOTE: We now have a group ID!  If we encounter errors at this point,
    # here's what we need to do:
    # 1. Try to delete the group.  If successful, throw our exception.
    # 2. Otherwise, return the Group ID and our exception.

    # Set Group policies
    policy_request = globus_sdk.GroupPolicies(
        is_high_assurance = high_risk,
        group_visibility = globus_sdk.GroupVisibility.private,
        group_members_visibility = globus_sdk.GroupMemberVisibility.members,
        join_requests = False,
        signup_fields = list(),
    )
    try:
        policy_response = client.groups.set_group_policies(
            group_id=group_id,
            data=policy_request,
        )
    except globus_sdk.GlobusAPIError as error:
        if error.http_status == 500:
            e = IOError(f"Globus API transient error creating Group '{description}'")
        else:
            e = IOError(f"Unknown error in creation of Group '{description}': {e.code}-{e.message}")
        if _try_delete(group_id):
            raise e
        else:
            return (group_id, e)
    except globus_sdk.NetworkError as error:
        e = IOError(f"Network issue creating Group '{description}'")
        if _try_delete(group_id):
            raise e
        else:
            return (group_id, e)

    if policy_response.http_status != 200:
        e = IOError(f"Unknown error in update of Group {group_id}: {create_response.code}-{create_response.message}")
        if _try_delete(group_id):
            raise e
        else:
            return (group_id, e)

    # If we have any additional admins, add them now.
    if len(admin_uuids) > 0:
        admin_request = globus_sdk.BatchMembershipActions()
        admin_request.add_members(
            identity_ids=admin_uuids,
            role=globus_sdk.GroupRole.admin,
        )
        try:
            admin_response = client.groups.batch_membership_action(
                group_id=group_id,
                actions=admin_request,
            )
        except globus_sdk.GlobusAPIError as error:
            if error.http_status == 500:
                e = IOError(f"Globus API transient error adding admins to Group '{description}'")
            else:
                e = IOError(f"Unknown error adding admins to Group '{description}': {e.code}-{e.message}")
            if _try_delete(group_id):
                raise e
            else:
                return (group_id, e)
        except globus_sdk.NetworkError as error:
            e = IOError(f"Network issue adding admins to Group '{description}'")
            if _try_delete(group_id):
                raise e
            else:
                return (group_id, e)
        if admin_response.http_status != 200:
            e = IOErrorIOError(f"Unknown error adding admins to Group '{description}': {e.code}-{e.message}")
            if _try_delete(group_id):
                raise e
            else:
                return (group_id, e)

    # Return the group UUID (… and any exceptions that occurred)!
    return (group_id, None)


# Delete a Group.
def delete_group(
    client: GlobusClients,
    group_id: UUID,
) -> None:
    """Try to delete a Globus Group.

    @param client A Globus Groups client.

    @param group_id The ID of the Group to delete.

    @raises KeyError Group not found.

    @raises PermissionError Permission error creating group.

    @raises IOError Issue communicating with Globus APIs.
    """
    try:
        delete_response = client.groups.delete_group(group_id)
    except globus_sdk.GlobusAPIError as e:
        if e.http_status == 404:
            raise KeyError(group_id)
        elif e.http_status in (401, 403):
            raise PermissionError(group_id)
        elif e.http_status == 500:
            raise IOError(f"Globus API transient error deleting Group {group_id}")
        else:
            raise IOError(f"Unknown error deleting Group {group_id}: {e.code}-{e.message}")
    except globus_sdk.NetworkError as e:
        raise IOError(f"Network issue deleting Group {group_id}")
    if delete_response.http_status != 200:
        raise IOError(f"Unknown error deleting Group {group_id}: {e.code}-{e.message}")


# Try to delete a Group.  An internal method which raises no exceptions.
def _try_delete(
    client: GlobusClients,
    group_id: UUID,
) -> bool:
    """Try to delete a Globus Group.

    @param client A Globus Groups client.

    @param group_id The ID of the Group to delete.

    @return True if the Group is successfully deleted, else False.
    """
    try:
        client.groups.delete_group(group_id)
        return True
    except Exception:
        pass
    return False


# These classes represent members of a Globus Group.

@dataclass(frozen=True)
class GroupMembers(Set):
    """Group members.

    This has all members of a Globus Group, regardless of access level.
    """
    people: frozenset[str]

    def __contains__(
        self,
        item: str,
    ) -> bool:
        return item in self.people

    def __len__(self) -> int:
        return len(self.people)

    def __iter__(self) -> Iterator[str]:
        return iter(self.people)


@dataclass(frozen=True)
class GroupMembersByLevel(Collection):
    """Group members by level of membership.

    This class is used to group members by their level of membership.  Each
    Globus Group has one or more administrators, followed by zero or more
    managers, followed by zero or more members.  Managers have the privileges
    of members, and admins have the privileges of managers and members.
    """
    members: frozenset[str]
    managers: frozenset[str]
    admins: frozenset[str]

    def __contains__(
        self,
        item: str,
    ) -> bool:
        items_found = sum(item in s for s in (self.members, self.managers, self.admins))
        if items_found == 0:
            return False
        if items_found == 1:
            return True
        else:
            raise RuntimeError(f"{item} found in multiple sets")

    def __len__(self) -> int:
        return sum(len(s) for s in (self.members, self.managers, self.admins))

    def __iter__(self) -> Iterator[str]:
        return chain(iter(self.members), iter(self.managers), iter(self.admins))

    def all(self) -> GroupMembers:
        """Return all members in a single set.
        """
        return GroupMembers(
            self.members.union(self.managers).union(self.admins)
        )


def get_members(
    client: GlobusClients,
    group_id: UUID,
) -> GroupMembersByLevel:
    """Get the membership of a Globus Group.

    Given a Client ID, returns the set of members, grouped by level of access.
    Each set is a set of Globus Identity usernames.

    If an Identity-mapper instance is provided, each group member will be added
    to the mapper.

    @param client Globus Auth and Transfer clients.

    @param group_id The Group ID to look up.

    @param mapper An optional Globus Identity Mapper.

    @return The list of members, by level of access.

    @raise KeyError The Group could not be found.

    @raise PermissionError Permission error creating group.

    @raise IOError Issue communicating with Globus APIs.
    """

    # Get the Group, including the list of members
    try:
        get_response = client.groups.get_group(
            group_id=group_id,
            include='memberships',
        )
    except globus_sdk.GlobusAPIError as e:
        if e.http_status == 404:
            raise KeyError(group_id)
        elif e.http_status in (401, 403):
            raise PermissionError(group_id)
        elif e.http_status == 500:
            raise IOError(f"Globus API transient error looking up group {group_id}")
        else:
            raise Exception(f"Unknown error in lookup of Group {group_id}: {e.code}-{e.message}")
    except globus_sdk.NetworkError as e:
        raise IOError(f"Network issue looking up group {group_id}")

    # Each user can fit into one of three sets.
    members = set()
    managers = set()
    admins = set()

    # Go through the list, placing users in the appropriate set.
    # Also seed the mapper
    for person in get_response['memberships']:
        username = person['username']
        client.mapper.add(username)

        # Is the person a member, manager, or admin?
        if person['role'] == 'member':
            members.add(username)
        elif person['role'] == 'manager':
            managers.add(username)
        elif person['role'] == 'admin':
            admins.add(username)
        else:
            raise TypeError('Unknown type ' + person['role'] + ' for ' + person['username'])

    # We've finished going through users, let's build and return our response!
    return GroupMembersByLevel(
        admins = frozenset(admins),
        managers = frozenset(managers),
        members = frozenset(members),
    )


def add_members(
    client: GlobusClients,
    group_id: UUID,
    members: set[str],
    provision: bool = False,
) -> None:
    """Add members to a Globus Group.

    Given a set of either 

    @param client Globus clients.

    @param members The set of member usernames to add.

    @param provision If True, unknown usernames will be provisioned.

    @raise KeyError One of the new members could not be found, and provision is False.

    @raise FileNotFoundError Group ID not found.

    @raise PermissionError Permission error creating group.

    @raise IOError Issue communicating with Globus APIs.
    """

    # How many additions can we make at once?
    BATCH_SIZE = 100

    # Add all of the members to our mapper
    for member in members:
        client.mapper.add(member)

    # Split up the set of new members into batches.
    # This is also where we do UUID resolution, and optional provisioning.
    batches: list[list[UUID]] = list()
    next_batch: list[UUID] = list()
    for member in members:
        try:
            next_batch.append(client.mapper[member]['id'])
        except KeyError:
            pass
        except globus_sdk.GlobusAPIError as error:
            if error.http_status in (401, 403):
                raise PermissionError(group_id)
            if error.http_status == 500:
                raise IOError(f"Globus API transient error adding admins to Group '{description}'")
            else:
                raise IOError(f"Unknown error adding admins to Group '{description}': {e.code}-{e.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue adding admins to Group '{description}'")

        # Check if we should start up the next batch.
        if len(next_batch) == BATCH_SIZE:
            batches.append(next_batch)
            next_batch = set()

    # Add the final batch to the list
    batches.append(next_batch)
    del next_batch

    # Go through each batch, submitting requests!
    for batch in batches:
        # Create a request document.
        member_request = globus_sdk.BatchMembershipActions()
        member_request.add_members(
            identity_ids=batch,
            role=globus_sdk.GroupRole.member,
        )
        try:
            member_response = client.groups.batch_membership_action(
                group_id=group_id,
                actions=member_request,
            )
        except globus_sdk.GlobusAPIError as error:
            if error.http_status == 404:
                raise FileNotFoundError(group_id)
            elif error.http_status in (401, 403):
                raise PermissionError(group_id)
            if error.http_status == 500:
                raise IOError(f"Globus API transient error adding admins to Group '{description}'")
            else:
                raise IOError(f"Unknown error adding admins to Group '{description}': {e.code}-{e.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue adding admins to Group '{description}'")
        if admin_response.http_status != 200:
            raise IOErrorIOError(f"Unknown error adding admins to Group '{description}': {e.code}-{e.message}")

    # All done!
