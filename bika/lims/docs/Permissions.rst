===========
Permissions
===========

All objects in Bika LIMS are permission aware.
Therefore, only users with the right **roles** can view or edit contents.
Each role may contain one or more **permissions**.

Test Setup
==========

    >>> from plone import api as ploneapi
    >>> from AccessControl.PermissionRole import rolesForPermissionOn

    >>> portal = self.getPortal()
    >>> portal_url = portal.absolute_url()
    >>> bika_setup = portal.bika_setup
    >>> bika_setup_url = portal_url + "/bika_setup"
    >>> browser = self.getBrowser()

    >>> def get_roles_for_permission(permission, context):
    ...     allowed = set(rolesForPermissionOn(permission, context))
    ...     return sorted(allowed)

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

    >>> get_roles_for_permission("View", labcontacts)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("View", labcontact)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_for_permission("Access contents information", labcontacts)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("Access contents information", labcontact)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_for_permission("List folder contents", labcontacts)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("List folder contents", labcontact)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_for_permission("Modify portal content", labcontacts)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("Modify portal content", labcontact)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_for_permission("Delete objects", labcontacts)
    ['Manager']

    >>> get_roles_for_permission("Delete objects", labcontact)
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

    >>> get_roles_for_permission("View", instruments)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("View", instrument)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_for_permission("Access contents information", instruments)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("Access contents information", instrument)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_for_permission("List folder contents", instruments)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("List folder contents", instrument)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_for_permission("Modify portal content", instruments)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("Modify portal content", instrument)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_for_permission("Delete objects", instruments)
    ['Manager']

    >>> get_roles_for_permission("Delete objects", instrument)
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

.. Note::

    A method should have the its own defined roles for a certain permssion from
    the `bika_inactive_workflow` and the inherited roles from its parent folder,
    which got customized in the `setuphandler` explicitly. Therefore, please
    refer to both, the assigned workflow and the setuphandler for the merged set
    of alloed roles for a permission.


Exactly these roles have should have a `View` permission::

    >>> get_roles_for_permission("View", methods)
    ['Anonymous', 'Authenticated', 'Manager', 'Member']

    >>> get_roles_for_permission("View", method)
    ['Analyst', 'Anonymous', 'Authenticated', 'LabClerk', 'LabManager', 'Manager', 'Member', 'Owner']

Exactly these roles have should have the `Access contents information` permission::

    >>> get_roles_for_permission("Access contents information", methods)
    ['Anonymous', 'Authenticated', 'Manager', 'Member']

    >>> get_roles_for_permission("Access contents information", method)
    ['Analyst', 'Anonymous', 'Authenticated', 'LabClerk', 'LabManager', 'Manager', 'Member', 'Owner']

Exactly these roles have should have the `List folder contents` permission::

    >>> get_roles_for_permission("List folder contents", methods)
    ['Anonymous', 'Authenticated', 'Member']

    >>> get_roles_for_permission("List folder contents", method)
    ['Analyst', 'Anonymous', 'Authenticated', 'LabClerk', 'LabManager', 'Manager', 'Member', 'Owner']

Exactly these roles have should have the `Modify portal content` permission::

    >>> get_roles_for_permission("Modify portal content", methods)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

    >>> get_roles_for_permission("Modify portal content", method)
    ['Analyst', 'LabClerk', 'LabManager', 'Manager', 'Owner']

Exactly these roles have should have the `Delete objects` permission::

    >>> get_roles_for_permission("Delete objects", methods)
    ['LabManager', 'Manager']

    >>> get_roles_for_permission("Delete objects", method)
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
