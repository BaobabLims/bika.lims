===========
Permissions
===========

All objects in Bika LIMS are permission aware.
Therefore, only users with the right **roles** can view or edit contents.
Each role may contain one or more **permissions**.

Test Setup
==========

    >>> from plone import api as ploneapi

    >>> portal = self.getPortal()
    >>> portal_url = portal.absolute_url()
    >>> bika_setup = portal.bika_setup
    >>> bika_setup_url = portal_url + "/bika_setup"
    >>> browser = self.getBrowser()

    >>> def get_roles_of_permission(context, permission, *roles):
    ...     # Merges the given roles with the granted roles for comparison
    ...     permissions = context.rolesOfPermission(permission)
    ...     granted = filter(lambda role: role, map(
    ...                      lambda permission: permission.get("selected") == "SELECTED"
    ...                          and permission.get("name") or None, permissions))
    ...     return sorted(set(granted).union(set(roles)))

    >>> def create(container, portal_type, title=None):
    ...     # Creates a content in a container and manually calls processForm
    ...     title = title is None and "Test {}".format(portal_type) or title
    ...     _ = container.invokeFactory(portal_type, id="tmpID", title=title)
    ...     obj = container.get(_)
    ...     obj.processForm()
    ...     return obj

    >>> def get_workflows_for(context):
    ...     # Returns a tuple of assigned workflows for the given context
    ...     workflow = ploneapi.portal.get_tool("portal_workflow")
    ...     return workflow.getChainFor(context)

    >>> def get_workflow_status_of(context):
    ...     # Returns the workflow status of the given context
    ...     return ploneapi.content.get_state(context)


Test Workflows and Permissions
==============================

Workflows control the allowed roles for specific permissions.
A role is a container for several permissions.


Lab Contact(s)
--------------

Lab Contacts are the employees of the lab.

Test Workflow
.............

A `labcontact` lives in the `bika_setup/bika_labcontacts` folder::

    >>> labcontacts = bika_setup.bika_labcontacts
    >>> labcontact = create(labcontacts, "LabContact")

The `bika_labcontacts` folder follows the `bika_one_state_workflow` and is
initially in the `active` state::

    >>> get_workflows_for(labcontacts)
    ('bika_one_state_workflow',)

    >>> get_workflow_status_of(labcontacts)
    'active'

A `labcontact` follows the `bika_inactive_workflow` and has an initial state of `active`::

    >>> get_workflows_for(labcontact)
    ('bika_inactive_workflow',)

    >>> get_workflow_status_of(labcontacts)
    'active'

Test Permissions
................

Exactly these roles have should have a `View` permission::

    >>> get_roles_of_permission(labcontacts, "View")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(labcontact, "View")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_of_permission(labcontacts, "Access contents information")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(labcontact, "Access contents information")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_of_permission(labcontacts, "List folder contents")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(labcontact, "List folder contents")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_of_permission(labcontacts, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(labcontact, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_of_permission(labcontacts, "Delete objects")
    ['Manager']

    >>> get_roles_of_permission(labcontact, "Delete objects")
    ['Manager']

Anonymous Browser Test
......................

Anonymous should not be able to view the `bika_labcontacts` folder::

    >>> browser.open(labcontacts.absolute_url() + "/base_view")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to view a `labcontact`::

    >>> browser.open(labcontact.absolute_url() + "/base_view")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to edit the `bika_labcontacts` folder::

    >>> browser.open(labcontacts.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to edit a `labcontact`::

    >>> browser.open(labcontact.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...


Instrument(s)
-------------

Instruments represent the measuring hardware of the lab.

Test Workflow
.............

A `instrument` lives in the `bika_setup/bika_instruments` folder::

    >>> instruments = bika_setup.bika_instruments
    >>> instrument = create(instruments, "Instrument")

The `bika_instruments` folder follows the `bika_one_state_workflow` and is
initially in the `active` state::

    >>> get_workflows_for(instruments)
    ('bika_one_state_workflow',)

    >>> get_workflow_status_of(instruments)
    'active'

A `instrument` follows the `bika_inactive_workflow` and has an initial state of `active`::

    >>> get_workflows_for(instrument)
    ('bika_inactive_workflow',)

    >>> get_workflow_status_of(instruments)
    'active'

Test Permissions
................

Exactly these roles have should have a `View` permission::

    >>> get_roles_of_permission(instruments, "View")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(instrument, "View")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_of_permission(instruments, "Access contents information")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(instrument, "Access contents information")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_of_permission(instruments, "List folder contents")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(instrument, "List folder contents")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_of_permission(instruments, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(instrument, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_of_permission(instruments, "Delete objects")
    ['Manager']

    >>> get_roles_of_permission(instrument, "Delete objects")
    ['Manager']

Anonymous Browser Test
......................

Anonymous should not be able to view the `bika_instruments` folder::

    >>> browser.open(instruments.absolute_url() + "/base_view")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to view a `instrument`::

    >>> browser.open(instrument.absolute_url() + "/base_view")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to edit the `bika_instruments` folder::

    >>> browser.open(instruments.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to edit a `instrument`::

    >>> browser.open(instrument.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...


Method(s)
---------

Methods describe the sampling methods of the lab.

Methods should be viewable by unauthenticated users for information purpose.

.. Note::

    The permissions of the `methods` folder get explicitly set by the
    `setuphandler` during the installation. Thus, the permissions deviate from
    the assigned workflow.


Test Workflow
.............

A `method` lives in the `methods` folder::

    >>> methods = portal.methods
    >>> method = create(methods, "Method")

The `methods` folder follows the `bika_one_state_workflow` and is initially in
the `active` state::

    >>> get_workflows_for(methods)
    ('bika_one_state_workflow',)

    >>> get_workflow_status_of(methods)
    'active'

A `method` follows the `bika_inactive_workflow` and has an initial state of `active`::

    >>> get_workflows_for(method)
    ('bika_inactive_workflow',)

    >>> get_workflow_status_of(methods)
    'active'

Test Permissions
................

Exactly these roles have should have a `View` permission::

    >>> get_roles_of_permission(methods, "View")
    ['Anonymous', 'Authenticated', 'Manager', 'Member']

    >>> get_roles_of_permission(method, "View")
    ['Anonymous', 'Authenticated', 'Analyst', 'LabClerk', 'LabManager', 'Manager', 'Member', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_of_permission(methods, "Access contents information")
    ['Anonymous', 'Authenticated', 'Manager', 'Member']

    >>> get_roles_of_permission(method, "Access contents information")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_of_permission(methods, "List folder contents")
    ['Anonymous', 'Authenticated', 'Member']

    >>> get_roles_of_permission(method, "List folder contents")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_of_permission(methods, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_of_permission(method, "Modify portal content")
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_of_permission(methods, "Delete objects")
    ['LabManager', 'Manager']

    >>> get_roles_of_permission(method, "Delete objects")
    ['Manager']

Anonymous Browser Test
......................

Anonymous should not be able to view the `methods` folder::

    >>> browser.open(methods.absolute_url() + "/base_view")
    >>> "methods" in browser.contents
    True

Anonymous should not be able to view a `method`::

    >>> browser.open(method.absolute_url() + "/base_view")

Anonymous should not be able to edit the `methods` folder::

    >>> browser.open(methods.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...

Anonymous should not be able to edit a `method`::

    >>> browser.open(method.absolute_url() + "/base_edit")
    Traceback (most recent call last):
    ...
    Unauthorized: ...
