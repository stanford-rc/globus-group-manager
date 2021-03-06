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
import enum
import globus_sdk
from itertools import chain
import logging
from typing import NamedTuple, Optional, Union
from uuid import UUID

from ggm.globus.client import GlobusClients, GlobusServerClients
from ggm.environ import config

# Set up logging and bring logging functions into this namespace.
# Also add a Null handler (as we're a library).
logger = logging.getLogger(__name__)
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
exception = logger.exception
logger.addHandler(logging.NullHandler())


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
    domain: str,
) -> Iterator[str]:
    """De-scope a collection of usernames (removing a domain).

    @param usernames The collectin of usernames to be de-scoped.

    @param domain The domain to remove.

    @raise KeyError If the username's domain does not match the expected domain.

    @raise ValueError The domain is not present in the username.
    """
    for username in usernames:
        try:
            (username_user, username_domain) = username.rsplit('@', maxsplit=1)
        except ValueError:
            raise ValueError(username)
        if username_domain != domain:
            raise KeyError(username)
        yield username_user


# List the Globus Groups where the client is any kind of member.
class MemberType(enum.IntEnum):
    MEMBER = 0
    MANAGER = 1
    ADMIN = 2

class GlobusGroup(NamedTuple):
    id: UUID
    name: str
    description: Optional[str]
    high_risk: bool
    member_level: MemberType

def list_groups(
    client: GlobusClients,
) -> set[GlobusGroup]:
    """Get a list of Globus Groups where the client is a member.

    @raises IOError Issue communicating with Globus APIs.
    """
    debug(f"In list_groups")

    # This is an easy request to make!
    try:
        groups_response = client.groups.get_my_groups()
    except globus_sdk.GlobusAPIError as e:
        if e.http_status == 500:
            raise IOError(f"Globus API transient error looking up {admin}")
        else:
            raise IOError(f"Unknown error looking up {admin}: {e.code}-{e.message}")
    except globus_sdk.NetworkError as e:
        raise IOError(f"Network issue looking up {admin}")

    # Go through each group and make the responses
    result: set[GlobusGroup] = set()
    for group in groups_response.data:
        debug(f"Found Group {group['id']}")
        # Start by capturing the basic stuff
        details = {
            'id': UUID(group['id']),
            'name': group['name'],
            'description': group['description'],
            'high_risk': True if group['policies']['is_high_assurance'] is True else False,
        }

        # Check memberships to see what our level is
        member_level = MemberType.MEMBER
        for membership in group['my_memberships']:
            # Loop through all memberships.  If we are only a member, meh, skip.
            # If we are a manager, then log that ONLY IF we aren't an admin.
            # If we are an admin, then log that.
            if membership['role'] == 'admin':
                debug('Client identity is an admin')
                member_level = MemberType.ADMIN
            elif membership['role'] == 'manager' and member_level != MemberType.ADMIN:
                debug('Client identity is a manager')
                member_level = MemberType.MANAGER
            else:
                debug('Client identity is a member')
        debug(f"Final membership verdict: {member_level.name}")
        details['member_level'] = member_level

        # Make a Group object and add to the result
        result.add(GlobusGroup(**details))

    # All done!  Return the final set.
    return result


# Create a Globus Group
def create_group(
    client: GlobusServerClients,
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
    debug(f"In create_group for {name}")

    # Make sure our strings are not empty
    assert(len(name) > 0)
    if description is not None:
        assert(len(description) > 0)

    # If we have a prefix, add it to the name.
    if config['GLOBUS_PREFIX'] != '':
        real_name = '[' + config['GLOBUS_PREFIX'] + '] ' + name
        debug(f"Using prefix, new name is {real_name}")
    else:
        real_name = name

    # Do we have additional admins?  Validate each one and get the UUIDs.

    # Do we have additional admins?  Check and convert to UUIDs.
    # First, seed them into the mapper.  Then, do the lookup.
    for admin in additional_admins:
        client.mapper.add(admin)
    admin_uuids: set[UUID] = set()
    for admin in additional_admins:
        info(f"Looking up Globus Identity ID for {admin}")
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
    info(f"Creating Globus Group {real_name}")
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
        debug('Bare group creation successful')
        info(f"Globus Group ID {group_id}")
    else:
        raise IOError(f"Unknown error in creation of Group '{description}': {create_response.code}-{create_response.message}")

    # NOTE: We now have a group ID!  If we encounter errors at this point,
    # here's what we need to do:
    # 1. Try to delete the group.  If successful, throw our exception.
    # 2. Otherwise, return the Group ID and our exception.

    # Set Group policies
    info("Setting Globus Group policies")
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
    else:
        debug('Policy set successful')

    # If we have any additional admins, add them now.
    if len(admin_uuids) > 0:
        info("Adding additional administrators")
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
        else:
            debug('Admin add successful')

    # Return the group UUID (… and any exceptions that occurred)!
    return (group_id, None)


# Delete a Group.
def delete_group(
    client: GlobusServerClients,
    group_id: UUID,
) -> None:
    """Try to delete a Globus Group.

    @param client A Globus Groups client.

    @param group_id The ID of the Group to delete.

    @raises KeyError Group not found.

    @raises PermissionError Permission error creating group.

    @raises IOError Issue communicating with Globus APIs.
    """
    info(f"Deleting Globus Group {group_id}")
    try:
        delete_response = client.groups.delete_group(group_id)
        debug('Deletion successful')
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
    client: GlobusServerClients,
    group_id: UUID,
) -> bool:
    """Try to delete a Globus Group.

    @param client A Globus Groups client.

    @param group_id The ID of the Group to delete.

    @return True if the Group is successfully deleted, else False.
    """
    debug(f"In _try_delete {group_id}")
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
    client: GlobusServerClients,
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
    debug(f"Fetching membership for Group {group_id}")

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
    debug(f"Found {len(members)} member(s), {len(managers)} manager(s), {len(admins)} admin(s)")
    return GroupMembersByLevel(
        admins = frozenset(admins),
        managers = frozenset(managers),
        members = frozenset(members),
    )


def add_members(
    client: GlobusServerClients,
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
    debug(f"In add_members for Group {group_id}")

    # How many additions can we make at once?
    BATCH_SIZE = 100

    # Add all of the members to our mapper
    for member in members:
        client.mapper.add(member)

    # Go through all members, and try to look up Globus Identity IDs.
    # Also track members that don't have an ID yet.
    member_uuids: list[UUID] = list()
    missing_members: list[str] = list()

    # Get UUIDs for all members, and identify members with no UUID.
    # If we find a member with no Globus Identity ID, possibly bail out.
    for member in members:
        try:
            debug(f"Looking up {member}")
            member_uuids.append(client.mapper[member]['id'])
        except KeyError:
            info(f"{member} needs a Globus Account")
            missing_members.append(member)
        except globus_sdk.GlobusAPIError as error:
            if error.http_status in (401, 403):
                raise PermissionError(group_id)
            if error.http_status == 500:
                raise IOError(f"Globus API transient error adding members to Group '{group_id}'")
            else:
                raise IOError(f"Unknown error adding members to Group '{group_id}': {error.code}-{error.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue adding members to Group '{group_id}'")

    # If we have missing members, and we aren't provisioning, bail out.
    if len(missing_members) > 0 and not provision:
        raise KeyError(missing_members.pop())

    # At this point, we either have no missing members, or we're provisioning.
    if len(missing_members) > 0:
        info(f"Provisioning Globus accounts for {len(missing_members)} people")
        # We're going to have to do all this ourselves, since the Identity
        # Mapper doesn't do provisioning.  That means we'll have to do our own
        # batching.
        provision_batches: list[list[str]] = list()
        next_provision: list[str] = list()

        # Split up missing_members into batches
        for missing_member in missing_members:
            debug(f"Adding {missing_member} to provisioning batch")
            next_provision.append(missing_member)
            if len(next_provision) == BATCH_SIZE:
                provision_batches.append(next_provision)
                next_provision = list()

        # Add the final batch to the list
        provision_batches.append(next_provision)
        del next_provision

        # Do a provisioning lookup for each batch
        for provision_batch in provision_batches:
            try:
                debug(f"Running provisioning batch of {len(provision_batch)}")
                provision_response = client.auth.get_identities(
                    usernames=provision_batch,
                    provision=True,
                )
            except globus_sdk.GlobusAPIError as error:
                if error.http_status == 400:
                    raise KeyError(error.message)
                if error.http_status in (401, 403):
                    raise PermissionError(group_id)
                if error.http_status == 500:
                    raise IOError(f"Globus API transient error provisioning Globus Identities")
                else:
                    raise IOError(f"Unknown error provisioning Globus Identities")
            except globus_sdk.NetworkError as error:
                raise IOError(f"Network issue provisioning Globus Identities")

            # Add the new IDs to the list
            member_uuids.extend(u['id'] for u in provision_response['identities'])

    # member_uuids is now complete!

    # Split up the set of new members into batches.
    batches: list[list[UUID]] = list()
    next_batch: list[UUID] = list()
    for member_uuid in member_uuids:
        next_batch.append(member_uuid)
        if len(next_batch) == BATCH_SIZE:
            batches.append(next_batch)
            next_batch = set()

    # Add the final batch to the list
    batches.append(next_batch)
    del next_batch

    # Go through each batch, submitting requests!
    for batch in batches:
        debug(f"Running add batch of {len(batch)}")
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
                raise IOError(f"Globus API transient error adding members to Group '{group_id}'")
            else:
                raise IOError(f"Unknown error adding members to Group '{group_id}': {error.code}-{error.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue adding members to Group '{group_id}'")
        if member_response.http_status != 200:
            raise IOError(f"Unknown error adding members to Group '{group_id}': {error.code}-{error.message}")

        # Make sure we processed all entries
        members_added = len(member_response['add'])
        members_errored = 0 if 'errors' not in member_response else len(member_response['errors']['add'])
        if members_added + members_errored != len(batch):
            warning(
                f"Batch had {len(batch)} entries, {members_added} added, and "
                f"{members_errored} errors.  Does not add up!"
            )
        if members_errored > 0:
            debug(f"Batch had {members_errored} errors")

            # "Already Active" errors are OK
            for member_errored in member_response['errors']['add']:
                if member_errored['code'] == 'ALREADY_ACTIVE':
                    debug(
                            'Skipping already active member ' +
                            client.mapper[member_errored['identity_id']]['username']
                        )
                else:
                    warning(
                        'Add of member ' +
                        client.mapper[member_errored['identity_id']]['username'] +
                        ' had error: [' + member_errored['code'] + '] ' +
                        member_errored['detail']

                    )

        # Done processing this batch of new members

    # Done processing new members!


def remove_members(
    client: GlobusServerClients,
    group_id: UUID,
    members: set[str],
) -> None:
    """Remove members from a Globus Group.

    Given a set of Globus Identity usernames, remove them from the Globus
    Group.  This operation is indempotent; if you remove someone who is already
    removed, or was never in the Group, the operation will still succeed.
    However the operation will fail if the username cannot be found.

    @param client Globus clients.

    @param members The set of member usernames to remove.

    @raise KeyError One of the members could not be found in Globus.

    @raise FileNotFoundError Group ID not found.

    @raise PermissionError Permission error creating group.

    @raise IOError Issue communicating with Globus APIs.
    """
    debug(f"In remove_members for Group {group_id}")

    # How many additions can we make at once?
    BATCH_SIZE = 100

    # Add all of the members to our mapper
    for member in members:
        client.mapper.add(member)

    # Go through all members, and try to look up Globus Identity IDs.
    # Also track members that don't have an ID yet.
    member_uuids: list[UUID] = list()

    # Get UUIDs for all members, and identify members with no UUID.
    for member in members:
        try:
            debug(f"Looking up {member}")
            member_uuids.append(client.mapper[member]['id'])
        except KeyError:
            raise KeyError(member)
        except globus_sdk.GlobusAPIError as error:
            if error.http_status in (401, 403):
                raise PermissionError(group_id)
            if error.http_status == 500:
                raise IOError(f"Globus API transient error removing users from Group '{group_id}'")
            else:
                raise IOError(f"Unknown error removing users from Group '{group_id}': {e.code}-{e.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue removing users from Group '{group_id}'")

    # Split up the set of new members into batches.
    batches: list[list[UUID]] = list()
    next_batch: list[UUID] = list()
    for member_uuid in member_uuids:
        next_batch.append(member_uuid)
        if len(next_batch) == BATCH_SIZE:
            batches.append(next_batch)
            next_batch = set()

    # Add the final batch to the list
    batches.append(next_batch)
    del next_batch

    # Go through each batch, submitting requests!
    for batch in batches:
        # Create a request document.
        debug(f"Running remove batch of {len(batch)}")
        member_request = globus_sdk.BatchMembershipActions()
        member_request.remove_members(
            identity_ids=batch,
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
                raise IOError(f"Globus API transient error removing users from Group '{group_id}'")
            else:
                raise IOError(f"Unknown error removing users from Group '{group_id}': {error.code}-{error.message}")
        except globus_sdk.NetworkError as error:
            raise IOError(f"Network issue removing users from Group '{group_id}'")
        if member_response.http_status != 200:
            raise IOError(f"Unknown error removing users from Group '{group_id}': {error.code}-{error.message}")

        # Make sure we processed all entries
        members_removed = len(member_response['remove'])
        members_errored = 0 if 'errors' not in member_response else len(member_response['errors']['remove'])
        if members_removed + members_errored != len(batch):
            warning(
                f"Batch had {len(batch)} entries, {members_removed} removed, and "
                f"{members_errored} errors.  Does not add up!"
            )
        if members_errored > 0:
            debug(f"Batch had {members_errored} errors")

            # "Cannot remove non-active" errors are OK
            for member_errored in member_response['errors']['remove']:
                if member_errored['code'] == 'REMOVE_NON_ACTIVE_FORBIDDEN':
                    debug(
                            'Skipping already removed member ' +
                            client.mapper[member_errored['identity_id']]['username']
                        )
                else:
                    warning(
                        'Removal of member ' +
                        client.mapper[member_errored['identity_id']]['username'] +
                        ' had error: [' + member_errored['code'] + '] ' +
                        member_errored['detail']
                    )

        # Done processing this batch of removed members

    # All done!
