# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

import sys
import logging
from decimal import Decimal
from operator import methodcaller

from AccessControl import ClassSecurityInfo
from DateTime import DateTime

from plone import api as ploneapi
from plone.indexer import indexer
from zope.interface import implements

from Products.CMFCore import permissions
from Products.CMFCore.permissions import View
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CMFPlone.utils import _createObjectByType

from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import BaseFolder
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import registerType
from Products.Archetypes.config import REFERENCE_CATALOG
from Products.Archetypes.references import HoldingReference

# AT Fields
from Products.Archetypes.atapi import TextField
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import BooleanField
from Products.Archetypes.atapi import ComputedField
from Products.Archetypes.atapi import ReferenceField
from Products.Archetypes.atapi import FixedPointField
from Products.ATExtensions.field import RecordsField

# Bika Fields
from bika.lims.browser.fields import ProxyField
from bika.lims.browser.fields import DateTimeField
from bika.lims.browser.fields import ARAnalysesField
from bika.lims.browser.fields import HistoryAwareReferenceField

# AT Widgets
from Products.Archetypes.Widget import RichWidget
from Products.Archetypes.atapi import StringWidget
from Products.Archetypes.atapi import BooleanWidget
from Products.Archetypes.atapi import ComputedWidget
from Products.Archetypes.atapi import TextAreaWidget

# Bika Widgets
from bika.lims.browser.widgets import DecimalWidget
from bika.lims.browser.widgets import DateTimeWidget
from bika.lims.browser.widgets import ReferenceWidget
from bika.lims.browser.widgets import SelectionWidget
from bika.lims.browser.widgets import RejectionWidget
from bika.lims.browser.widgets import SelectionWidget as BikaSelectionWidget

# Bika Permissions
from bika.lims.permissions import SampleSample
from bika.lims.permissions import ScheduleSampling
from bika.lims.permissions import EditARContact
from bika.lims.permissions import ManageInvoices
from bika.lims.permissions import Verify as VerifyPermission

# Bika Workflow
from bika.lims.workflow import skip
from bika.lims.workflow import doActionFor
from bika.lims.workflow import getTransitionDate
from bika.lims.workflow import isBasicTransitionAllowed

# Bika Utils
from bika.lims.utils import getUsers
from bika.lims.utils import dicts_to_dict
from bika.lims.utils.analysisrequest import notify_rejection

# Bika Interfaces
from bika.lims.interfaces import IAnalysisRequest
from bika.lims.interfaces import ISamplePrepWorkflow

from bika.lims import api
from bika.lims import deprecated
from bika.lims.config import PROJECTNAME
from bika.lims import bikaMessageFactory as _
from bika.lims.content.bikaschema import BikaSchema

"""The request for analysis by a client. It contains analysis instances.
"""


@indexer(IAnalysisRequest)
def Priority(instance):
    priority = instance.getPriority()
    if priority:
        return priority.getSortKey()


@indexer(IAnalysisRequest)
def BatchUID(instance):
    batch = instance.getBatch()
    if batch:
        return batch.UID()


@indexer(IAnalysisRequest)
def getDatePublished(instance):
    return getTransitionDate(instance, 'publish')


@indexer(IAnalysisRequest)
def SamplingRoundUID(instance):
    sr = instance.getSamplingRound()
    if sr:
        return sr.UID()


@indexer(IAnalysisRequest)
def getDepartmentUIDs(instance):
    """Returns department UIDs assigned to the Analyses
       from this Analysis Request
    """
    ans = [an.getObject() for an in instance.getAnalyses()]
    depts = [an.getService().getDepartment().UID() for an in ans
             if an.getService().getDepartment()]
    return depts


# SCHEMA DEFINITION
schema = BikaSchema.copy() + Schema((

    StringField(
        'RequestID',
        searchable=True,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=StringWidget(
            label=_("Request ID"),
            description=_("The ID assigned to the client's request by the lab"),
            visible={'view': 'invisible',
                     'edit': 'invisible'},
        ),
    ),

    ReferenceField(
        'Contact',
        required=1,
        default_method='getContactUIDForUser',
        vocabulary_display_path_bound=sys.maxsize,
        allowed_types=('Contact',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestContact',
        mode="rw",
        read_permission=permissions.View,
        write_permission=EditARContact,
        widget=ReferenceWidget(
            label=_("Contact"),
            render_own_label=True,
            size=20,
            helper_js=("bika_widgets/referencewidget.js",
                       "++resource++bika.lims.js/contact.js"),
            description=_("The primary contact of this analysis request, " \
                          "who will receive notifications and publications via email"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'prominent',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            base_query={'inactive_state': 'active'},
            showOn=True,
            popup_width='400px',
            colModel=[
                {'columnName': 'UID', 'hidden': True},
                {'columnName': 'Fullname', 'width': '50',
                 'label': _('Name')},
                {'columnName': 'EmailAddress', 'width': '50',
                 'label': _('Email Address')},
            ],
        ),
    ),

    ReferenceField(
        'CCContact',
        multiValued=1,
        vocabulary_display_path_bound=sys.maxsize,
        allowed_types=('Contact',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestCCContact',
        mode="rw",
        read_permission=permissions.View,
        write_permission=EditARContact,
        widget=ReferenceWidget(
            label=_("CC Contacts"),
            description=_("The contacts used in CC for email notifications"),
            render_own_label=True,
            size=20,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'prominent',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            base_query={'inactive_state': 'active'},
            showOn=True,
            popup_width='400px',
            colModel=[
                {'columnName': 'UID', 'hidden': True},
                {'columnName': 'Fullname', 'width': '50',
                 'label': _('Name')},
                {'columnName': 'EmailAddress', 'width': '50',
                 'label': _('Email Address')},
            ],
        ),
    ),

    StringField(
        'CCEmails',
        mode="rw",
        read_permission=permissions.View,
        write_permission=EditARContact,
        acquire=True,
        acquire_fieldname="CCEmails",
        widget=StringWidget(
            label=_("CC Emails"),
            description=_("Additional email addresses to be notified"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'prominent',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            render_own_label=True,
            size=20,
        ),
    ),

    ReferenceField(
        'Client',
        required=1,
        allowed_types=('Client',),
        relationship='AnalysisRequestClient',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Client"),
            description=_("The assigned client of this request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'invisible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'invisible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_received': {'view': 'invisible', 'edit': 'invisible'},
                'attachment_due': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'invisible', 'edit': 'invisible'},
                'verified': {'view': 'invisible', 'edit': 'invisible'},
                'published': {'view': 'invisible', 'edit': 'invisible'},
                'invalid': {'view': 'invisible', 'edit': 'invisible'},
                'rejected': {'view': 'invisible', 'edit': 'invisible'},
            },
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    ReferenceField(
        'Sample',
        vocabulary_display_path_bound=sys.maxsize,
        allowed_types=('Sample',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestSample',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sample"),
            description=_("Select a sample to create a secondary AR"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_catalog',
            base_query={'cancellation_state': 'active',
                        'review_state': ['sample_due', 'sample_received', ]},
            showOn=True,
        ),
    ),

    ReferenceField(
        'Batch',
        allowed_types=('Batch',),
        relationship='AnalysisRequestBatch',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Batch"),
            size=20,
            description=_("The assigned batch of this request"),
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_catalog',
            base_query={'review_state': 'open',
                        'cancellation_state': 'active'},
            showOn=True,
        ),
    ),

    ReferenceField(
        'SamplingRound',
        allowed_types=('SamplingRound',),
        relationship='AnalysisRequestSamplingRound',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sampling Round"),
            description=_("The assigned sampling round of this request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='portal_catalog',
            base_query={},
            showOn=True,
        ),
    ),

    ReferenceField(
        'SubGroup',
        required=False,
        allowed_types=('SubGroup',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestSubGroup',
        widget=ReferenceWidget(
            label=_("Batch Sub-group"),
            description=_("The assigned batch sub group of this request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            colModel=[
                {'columnName': 'Title', 'width': '30',
                 'label': _('Title'), 'align': 'left'},
                {'columnName': 'Description', 'width': '70',
                 'label': _('Description'), 'align': 'left'},
                {'columnName': 'SortKey', 'hidden': True},
                {'columnName': 'UID', 'hidden': True},
            ],
            base_query={'inactive_state': 'active'},
            sidx='SortKey',
            sord='asc',
            showOn=True,
        ),
    ),

    ReferenceField(
        'Template',
        allowed_types=('ARTemplate',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestARTemplate',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("AR Template"),
            description=_("The predefined values of the AR template are set in the request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # TODO: Profile'll be delated
    ReferenceField(
        'Profile',
        allowed_types=('AnalysisProfile',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestAnalysisProfile',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Analysis Profile"),
            description=_("Analysis profiles apply a certain set of analyses"),
            size=20,
            render_own_label=True,
            visible=False,
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=False,
        ),
    ),

    ReferenceField(
        'Profiles',
        multiValued=1,
        allowed_types=('AnalysisProfile',),
        referenceClass=HoldingReference,
        vocabulary_display_path_bound=sys.maxsize,
        relationship='AnalysisRequestAnalysisProfiles',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Analysis Profiles"),
            description=_("Analysis profiles apply a certain set of analyses"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'DateSampled',
        proxy="context.getSample()",
        mode="rw",
        read_permission=permissions.View,
        write_permission=SampleSample,
        widget=DateTimeWidget(
            label=_("Date Sampled"),
            description=_("The date when the sample was taken"),
            size=20,
            show_time=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'secondary': 'disabled',
                'header_table': 'prominent',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'visible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_due': {'view': 'invisible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'invisible', 'edit': 'invisible'},
                'attachment_due': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'invisible', 'edit': 'invisible'},
                'verified': {'view': 'invisible', 'edit': 'invisible'},
                'published': {'view': 'invisible', 'edit': 'invisible'},
                'invalid': {'view': 'invisible', 'edit': 'invisible'},
                'rejected': {'view': 'invisible', 'edit': 'invisible'},
            },
            render_own_label=True,
        ),
    ),

    # Sample field
    ProxyField(
        'Sampler',
        proxy="context.getSample()",
        mode="rw",
        read_permission=permissions.View,
        write_permission=SampleSample,
        vocabulary='getSamplers',
        widget=BikaSelectionWidget(
            format='select',
            label=_("Sampler"),
            description=_("The person who took the sample"),
            # see SamplingWOrkflowWidgetVisibility
            visible={
                'edit': 'visible',
                'view': 'visible',
                'header_table': 'prominent',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
            },
            render_own_label=True,
        ),
    ),

    # Sample field
    ProxyField(
        'ScheduledSamplingSampler',
        proxy="context.getSample()",
        mode="rw",
        read_permission=permissions.View,
        write_permission=ScheduleSampling,
        vocabulary='getSamplers',
        widget=BikaSelectionWidget(
            description=_("Define the sampler supposed to do the sample in "
                          "the scheduled date"),
            format='select',
            label=_("Sampler for scheduled sampling"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'header_table': 'visible',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_due': {'view': 'invisible', 'edit': 'invisible'},
                'sample_received': {'view': 'invisible', 'edit': 'invisible'},
                'expired': {'view': 'invisible', 'edit': 'invisible'},
                'disposed': {'view': 'invisible', 'edit': 'invisible'},
            },
            render_own_label=True,
        ),
    ),

    # Sample field
    ProxyField(
        'SamplingDate',
        proxy="context.getSample()",
        required=1,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=DateTimeWidget(
            label=_("Sampling Date"),
            description=_("The date when the sample will be taken"),
            size=20,
            show_time=True,
            render_own_label=True,
            # see SamplingWOrkflowWidgetVisibility
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'secondary': 'disabled',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    # Sample field
    ProxyField(
        'SampleType',
        proxy="context.getSample()",
        required=1,
        allowed_types='SampleType',
        relationship='AnalysisRequestSampleType',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sample Type"),
            description=_("Create a new sample of this type"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    RecordsField(
        'RejectionReasons',
        widget=RejectionWidget(
            label=_("Sample Rejection"),
            description=_("Set the Sample Rejection workflow and the reasons"),
            render_own_label=False,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'visible'},
                'invalid': {'view': 'visible', 'edit': 'visible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    ReferenceField(
        'Specification',
        required=0,
        allowed_types='AnalysisSpec',
        relationship='AnalysisRequestAnalysisSpec',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Analysis Specification"),
            description=_("Choose default AR specification values"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            colModel=[
                {'columnName': 'contextual_title',
                 'width': '30',
                 'label': _('Title'),
                 'align': 'left'},
                {'columnName': 'SampleTypeTitle',
                 'width': '70',
                 'label': _('SampleType'),
                 'align': 'left'},
                # UID is required in colModel
                {'columnName': 'UID', 'hidden': True},
            ],
            showOn=True,
        ),
    ),

    # see setResultsRange below.
    RecordsField(
        'ResultsRange',
        required=0,
        type='resultsrange',
        subfields=('keyword', 'min', 'max', 'error', 'hidemin', 'hidemax', 'rangecomment'),
        widget=ComputedWidget(visible=False),
    ),

    ReferenceField(
        'PublicationSpecification',
        required=0,
        allowed_types='AnalysisSpec',
        relationship='AnalysisRequestPublicationSpec',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.View,
        widget=ReferenceWidget(
            label=_("Publication Specification"),
            description=_(
                "Set the specification to be used before publishing an AR."),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'header_table': 'visible',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'invisible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_due': {'view': 'invisible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'invisible', 'edit': 'invisible'},
                'attachment_due': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'invisible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'visible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'SamplePoint',
        proxy="context.getSample()",
        allowed_types='SamplePoint',
        relationship='AnalysisRequestSamplePoint',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sample Point"),
            description=_("Location where sample was taken"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                # LIMS-1159
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'StorageLocation',
        proxy="context.getSample()",
        allowed_types='StorageLocation',
        relationship='AnalysisRequestStorageLocation',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Storage Location"),
            description=_("Location where sample is kept"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered':
                    {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    StringField(
        'ClientOrderNumber',
        searchable=True,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=StringWidget(
            label=_("Client Order Number"),
            description=_("The client side order number for this request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    # Sample field
    ProxyField(
        'ClientReference',
        proxy="context.getSample()",
        searchable=True,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=StringWidget(
            label=_("Client Reference"),
            description=_("The client side reference for this request"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered':
                    {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    # Sample field
    ProxyField(
        'ClientSampleID',
        proxy="context.getSample()",
        searchable=True,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=StringWidget(
            label=_("Client Sample ID"),
            description=_("The client side identifier of the sample"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    # Sample field
    ProxyField(
        'SamplingDeviation',
        proxy="context.getSample()",
        allowed_types=('SamplingDeviation',),
        relationship='AnalysisRequestSamplingDeviation',
        referenceClass=HoldingReference,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sampling Deviation"),
            description=_("Deviation between the sample and how it was sampled"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'SampleCondition',
        proxy="context.getSample()",
        allowed_types=('SampleCondition',),
        relationship='AnalysisRequestSampleCondition',
        referenceClass=HoldingReference,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Sample condition"),
            description=_("The current condition of the sample"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'EnvironmentalConditions',
        proxy="context.getSample()",
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=StringWidget(
            label=_("Environmental conditions"),
            description=_("The environmental condition during sampling"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'prominent',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            render_own_label=True,
            size=20,
        ),
    ),

    ReferenceField(
        'DefaultContainerType',
        allowed_types=('ContainerType',),
        relationship='AnalysisRequestContainerType',
        referenceClass=HoldingReference,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Default Container"),
            description=_("Default container for new sample partitions"),
            size=20,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            showOn=True,
        ),
    ),

    # Sample field
    ProxyField(
        'AdHoc',
        proxy="context.getSample()",
        default=False,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=BooleanWidget(
            label=_("Sampled AdHoc"),
            description=_("Was the sample taken in non-scheduled matter, " \
                          "e.g. out of a recurring sampling schedule?"),
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered':
                    {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'invisible'},
                'sampled': {'view': 'visible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'invisible'},
                'sample_due': {'view': 'visible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    # Sample field
    ProxyField(
        'Composite',
        proxy="context.getSample()",
        default=False,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=BooleanWidget(
            label=_("Composite"),
            description=_("Was the sample put together from multiple Samples?"),
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'secondary': 'disabled',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    BooleanField(
        'ReportDryMatter',
        default=False,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=BooleanWidget(
            label=_("Report as Dry Matter"),
            render_own_label=True,
            description=_("These results can be reported as dry matter"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    BooleanField(
        'InvoiceExclude',
        default=False,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=BooleanWidget(
            label=_("Invoice Exclude"),
            description=_("Should the analyses be excluded from the invoice?"),
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    ARAnalysesField(
        'Analyses',
        required=1,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ComputedWidget(
            visible={
                'edit': 'invisible',
                'view': 'invisible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'invisible'},
            }
        ),
    ),

    ReferenceField(
        'Attachment',
        multiValued=1,
        allowed_types=('Attachment',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestAttachment',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ComputedWidget(
            visible={
                'edit': 'invisible',
                'view': 'invisible',
            },
        )
    ),

    ReferenceField(
        'Invoice',
        vocabulary_display_path_bound=sys.maxsize,
        allowed_types=('Invoice',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestInvoice',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ComputedWidget(
            visible={
                'edit': 'invisible',
                'view': 'invisible',
            },
        )
    ),

    DateTimeField(
        'DateReceived',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=DateTimeWidget(
            label=_("Date Received"),
            description=_("The date when the sample was received"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'header_table': 'visible',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'invisible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_due': {'view': 'invisible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'visible', 'edit': 'invisible'},
            },
        ),
    ),

    DateTimeField(
        'DatePublished',
        mode="r",
        read_permission=permissions.View,
        widget=DateTimeWidget(
            label=_("Date Published"),
            description=_("The date when the request was published"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'invisible',
                'secondary': 'invisible',
                'header_table': 'visible',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_sampled': {'view': 'invisible', 'edit': 'invisible'},
                'scheduled_sampling': {'view': 'invisible', 'edit': 'invisible'},
                'sampled': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_preserved': {'view': 'invisible', 'edit': 'invisible'},
                'sample_due': {'view': 'invisible', 'edit': 'invisible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'invisible', 'edit': 'invisible'},
                'attachment_due': {'view': 'invisible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'invisible', 'edit': 'invisible'},
                'verified': {'view': 'invisible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
                'rejected': {'view': 'invisible', 'edit': 'invisible'},
            },
        ),
    ),

    TextField(
        'Remarks',
        searchable=True,
        default_content_type='text/x-web-intelligent',
        allowable_content_types=('text/plain',),
        default_output_type="text/plain",
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=TextAreaWidget(
            macro="bika_widgets/remarks",
            label=_("Remarks"),
            description=_("Remarks and comments for this request"),
            append_only=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'invisible',
                'sample_registered':
                    {'view': 'invisible', 'edit': 'invisible'},
            },
        ),
    ),

    FixedPointField(
        'MemberDiscount',
        default_method='getDefaultMemberDiscount',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=DecimalWidget(
            label=_("Member discount %"),
            description=_("Enter percentage value eg. 33.0"),
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'invisible',
                'sample_registered': {'view': 'invisible', 'edit': 'invisible'},
            },
        ),
    ),

    ComputedField(
        'ClientUID',
        searchable=True,
        expression='here.aq_parent.UID()',
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'SampleTypeTitle',
        searchable=True,
        expression="here.getSampleType().Title() if here.getSampleType() "
                   "else ''",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'SamplePointTitle',
        searchable=True,
        expression="here.getSamplePoint().Title() if here.getSamplePoint() "
                   "else ''",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'SampleUID',
        expression="here.getSample() and here.getSample().UID() or ''",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'SampleID',
        expression="here.getSample() and here.getSample().getId() or ''",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'ContactUID',
        expression="here.getContact() and here.getContact().UID() or ''",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'ProfilesUID',
        expression="here.getProfiles() and "
                   "[profile.UID() for profile in here.getProfiles()] or []",
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ComputedField(
        'Invoiced',
        expression='here.getInvoice() and True or False',
        default=False,
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    ReferenceField(
        'ChildAnalysisRequest',
        allowed_types=('AnalysisRequest',),
        relationship='AnalysisRequestChildAnalysisRequest',
        referenceClass=HoldingReference,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            visible=False,
        ),
    ),

    ReferenceField(
        'ParentAnalysisRequest',
        allowed_types=('AnalysisRequest',),
        relationship='AnalysisRequestParentAnalysisRequest',
        referenceClass=HoldingReference,
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            visible=False,
        ),
    ),

    StringField(
        'PreparationWorkflow',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        vocabulary='getPreparationWorkflows',
        acquire=True,
        widget=SelectionWidget(
            format="select",
            label=_("Preparation Workflow"),
            description=_("The needed preparation workflow for the sample in this request"),
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'invisible'},
                'attachment_due': {'view': 'visible', 'edit': 'invisible'},
                'to_be_verified': {'view': 'visible', 'edit': 'invisible'},
                'verified': {'view': 'visible', 'edit': 'invisible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
            },
            render_own_label=True,
        ),
    ),

    HistoryAwareReferenceField(
        'Priority',
        allowed_types=('ARPriority',),
        referenceClass=HoldingReference,
        relationship='AnalysisRequestPriority',
        mode="rw",
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=ReferenceWidget(
            label=_("Priority"),
            description=_("The urgency of this request"),
            size=10,
            render_own_label=True,
            visible={
                'edit': 'visible',
                'view': 'visible',
                'add': 'edit',
                'header_table': 'visible',
                'sample_registered': {'view': 'visible', 'edit': 'visible', 'add': 'edit'},
                'to_be_sampled': {'view': 'visible', 'edit': 'visible'},
                'scheduled_sampling': {'view': 'visible', 'edit': 'visible'},
                'sampled': {'view': 'visible', 'edit': 'visible'},
                'to_be_preserved': {'view': 'visible', 'edit': 'visible'},
                'sample_due': {'view': 'visible', 'edit': 'visible'},
                'sample_prep': {'view': 'visible', 'edit': 'invisible'},
                'sample_received': {'view': 'visible', 'edit': 'visible'},
                'attachment_due': {'view': 'visible', 'edit': 'visible'},
                'to_be_verified': {'view': 'visible', 'edit': 'visible'},
                'verified': {'view': 'visible', 'edit': 'visible'},
                'published': {'view': 'visible', 'edit': 'invisible'},
                'invalid': {'view': 'visible', 'edit': 'invisible'},
            },
            catalog_name='bika_setup_catalog',
            base_query={'inactive_state': 'active'},
            colModel=[
                {'columnName': 'Title', 'width': '30',
                 'label': _('Title'), 'align': 'left'},
                {'columnName': 'Description', 'width': '70',
                 'label': _('Description'), 'align': 'left'},
                {'columnName': 'sortKey', 'hidden': True},
                {'columnName': 'UID', 'hidden': True},
            ],
            sidx='sortKey',
            sord='asc',
            showOn=True,
        ),
    ),

    # For comments or results interpretation
    # Old one, to be removed because of the incorporation of
    # ResultsInterpretationDepts (due to LIMS-1628)
    TextField(
        'ResultsInterpretation',
        searchable=True,
        mode="rw",
        default_content_type='text/html',
        # Input content type for the textfield
        default_output_type='text/x-html-safe',
        # getResultsInterpretation returns a str with html tags
        # to conserve the txt format in the report.
        read_permission=permissions.View,
        write_permission=permissions.ModifyPortalContent,
        widget=RichWidget(
            description=_("Comments or results interpretation"),
            label=_("Results Interpretation"),
            size=10,
            allow_file_upload=False,
            default_mime_type='text/x-rst',
            output_mime_type='text/x-html',
            rows=3,
            visible=False),
    ),

    RecordsField('ResultsInterpretationDepts',
                 subfields=('uid',
                            'richtext'),
                 subfield_labels={'uid': _('Department'),
                                  'richtext': _('Results Interpreation')},
                 widget=RichWidget(visible=False),
                 ),
    # Custom settings for the assigned analysis services
    # https://jira.bikalabs.com/browse/LIMS-1324
    # Fields:
    #   - uid: Analysis Service UID
    #   - hidden: True/False. Hide/Display in results reports
    RecordsField('AnalysisServicesSettings',
                 required=0,
                 subfields=('uid', 'hidden',),
                 widget=ComputedWidget(visible=False),
                 ),
))
# /SCHEMA DEFINITION


# Some schema rearrangement
schema['title'].required = False
schema['id'].widget.visible = {
    'edit': 'invisible',
    'view': 'invisible',
}
schema['title'].widget.visible = {
    'edit': 'invisible',
    'view': 'invisible',
}
schema.moveField('Client', before='Contact')
schema.moveField('ResultsInterpretation', pos='bottom')
schema.moveField('ResultsInterpretationDepts', pos='bottom')


class AnalysisRequest(BaseFolder):
    implements(IAnalysisRequest, ISamplePrepWorkflow)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True

    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

    def _getCatalogTool(self):
        from bika.lims.catalog import getCatalog
        return getCatalog(self)

    def getRequestID(self):
        """Return the id as RequestID
        """
        return safe_unicode(self.getId()).encode('utf-8')

    def Title(self):
        """Return the Request ID as title
        """
        return self.getRequestID()

    def Description(self):
        """Returns searchable data as Description
        """
        descr = " ".join((self.getRequestID(), self.aq_parent.Title()))
        return safe_unicode(descr).encode('utf-8')

    def getClient(self):
        if self.aq_parent.portal_type == 'Client':
            return self.aq_parent
        if self.aq_parent.portal_type == 'Batch':
            return self.aq_parent.getClient()

    def getClientPath(self):
        return "/".join(self.aq_parent.getPhysicalPath())

    def getClientTitle(self):
        return self.getClient().Title() if self.getClient() else ''

    def getContactTitle(self):
        return self.getContact().Title() if self.getContact() else ''

    def getProfilesTitle(self):
        return [profile.Title() for profile in self.getProfiles()]

    def getTemplateTitle(self):
        return self.getTemplate().Title() if self.getTemplate() else ''

    def setPublicationSpecification(self, value):
        """Never contains a value; this field is here for the UI." \
        """
        return value

    def getAnalysisCategory(self):
        proxies = self.getAnalyses(full_objects=True)
        value = []
        for proxy in proxies:
            val = proxy.getCategoryTitle()
            if val not in value:
                value.append(val)
        return value

    def getAnalysisCategoryIDs(self):
        proxies = self.getAnalyses(full_objects=True)
        value = []
        for proxy in proxies:
            val = proxy.getService().getCategory().id
            if val not in value:
                value.append(val)
        return value

    def getAnalysisService(self):
        proxies = self.getAnalyses(full_objects=True)
        value = []
        for proxy in proxies:
            val = proxy.getServiceTitle()
            if val not in value:
                value.append(val)
        return value

    def getAnalysts(self):
        proxies = self.getAnalyses(full_objects=True)
        value = []
        for proxy in proxies:
            val = proxy.getAnalyst()
            if val not in value:
                value.append(val)
        return value

    def getBatch(self):
        # The parent type may be "Batch" during ar_add.
        # This function fills the hidden field in ar_add.pt
        if self.aq_parent.portal_type == 'Batch':
            return self.aq_parent
        else:
            return self.Schema()['Batch'].get(self)

    def getDefaultMemberDiscount(self):
        """Compute default member discount if it applies
        """
        if hasattr(self, 'getMemberDiscountApplies'):
            if self.getMemberDiscountApplies():
                plone = api.get_portal()
                settings = plone.bika_setup
                return settings.getMemberDiscount()
            else:
                return "0.00"

    def setDefaultPriority(self):
        """Compute default priority
        """
        bsc = getToolByName(self, 'bika_setup_catalog')
        priorities = bsc(
            portal_type='ARPriority',
        )
        for brain in priorities:
            obj = brain.getObject()
            if obj.getIsDefault():
                self.setPriority(obj)
                return

        # priority is not a required field.  No default means...
        logging.info('Priority: no default priority found')
        return

    security.declareProtected(View, 'getResponsible')

    def getAnalysesNum(self):
        """Return the amount of analyses verified/total in the current AR
        """
        verified = 0
        total = 0
        for analysis in self.getAnalyses():
            review_state = analysis.review_state
            if review_state in ['verified', 'published']:
                verified += 1
            if review_state not in 'retracted':
                total += 1
        return verified, total

    def getResponsible(self):
        """Return all manager info of responsible departments
        """
        managers = {}
        departments = []
        for analysis in self.objectValues('Analysis'):
            department = analysis.getService().getDepartment()
            if department is None:
                continue
            department_id = department.getId()
            if department_id in departments:
                continue
            departments.append(department_id)
            manager = department.getManager()
            if manager is None:
                continue
            manager_id = manager.getId()
            if manager_id not in managers:
                managers[manager_id] = {}
                managers[manager_id]['salutation'] = safe_unicode(
                    manager.getSalutation())
                managers[manager_id]['name'] = safe_unicode(
                    manager.getFullname())
                managers[manager_id]['email'] = safe_unicode(
                    manager.getEmailAddress())
                managers[manager_id]['phone'] = safe_unicode(
                    manager.getBusinessPhone())
                managers[manager_id]['job_title'] = safe_unicode(
                    manager.getJobTitle())
                if manager.getSignature():
                    managers[manager_id]['signature'] = \
                        '{}/Signature'.format(manager.absolute_url())
                else:
                    managers[manager_id]['signature'] = False
                managers[manager_id]['departments'] = ''
            mngr_dept = managers[manager_id]['departments']
            if mngr_dept:
                mngr_dept += ', '
            mngr_dept += safe_unicode(department.Title())
            managers[manager_id]['departments'] = mngr_dept
        mngr_keys = managers.keys()
        mngr_info = {'ids': mngr_keys, 'dict': managers}

        return mngr_info

    security.declareProtected(View, 'getResponsible')

    def getManagers(self):
        """Return all managers of responsible departments
        """
        manager_ids = []
        manager_list = []
        departments = []
        for analysis in self.objectValues('Analysis'):
            department = analysis.getService().getDepartment()
            if department is None:
                continue
            department_id = department.getId()
            if department_id in departments:
                continue
            departments.append(department_id)
            manager = department.getManager()
            if manager is None:
                continue
            manager_id = manager.getId()
            if manager_id not in manager_ids:
                manager_ids.append(manager_id)
                manager_list.append(manager)

        return manager_list

    security.declareProtected(View, 'getLate')

    def getLate(self):
        """Return True if any analyses are late
        """
        workflow = getToolByName(self, 'portal_workflow')
        review_state = workflow.getInfoFor(self, 'review_state', '')
        resultdate = 0
        if review_state in ['to_be_sampled', 'to_be_preserved',
                            'sample_due', 'published']:
            return False

        for analysis in self.objectValues('Analysis'):
            review_state = workflow.getInfoFor(analysis, 'review_state', '')
            if review_state == 'published':
                continue
            calculation = analysis.getService().getCalculation()
            if not calculation or (calculation and not calculation.getDependentServices()):
                resultdate = analysis.getResultCaptureDate()
            duedate = analysis.getDueDate()
            # noinspection PyCallingNonCallable
            if (resultdate and resultdate > duedate) \
                    or (not resultdate and DateTime() > duedate):
                return True

        return False

    security.declareProtected(View, 'getBillableItems')

    def getBillableItems(self):
        """The main purpose of this function is to obtain the analysis services
        and profiles from the analysis request
        whose prices are needed to quote the analysis request.
        If an analysis belongs to a profile, this analysis will only be
        included in the analyses list if the profile
        has disabled "Use Analysis Profile Price".

        :returns: a tuple of two lists. The first one only contains analysis
                  services not belonging to a profile with active "Use Analysis
                  Profile Price". The second list contains the profiles with
                  activated "Use Analysis Profile Price".
        """
        workflow = getToolByName(self, 'portal_workflow')
        # REMEMBER: Analysis != Analysis services
        analyses = []
        analysis_profiles = []
        to_be_billed = []
        # Getting all analysis request analyses
        # Getting all analysis request analyses
        ar_analyses = self.getAnalyses(cancellation_state='active',
                                       full_objects=True)
        UNBILLABLE_STATES = ('not_requested', 'retracted', 'sample_received')
        for analysis in ar_analyses:
            review_state = workflow.getInfoFor(analysis, 'review_state', '')
            if review_state not in UNBILLABLE_STATES:
                analyses.append(analysis)
        # Getting analysis request profiles
        for profile in self.getProfiles():
            # Getting the analysis profiles which has "Use Analysis Profile
            # Price" enabled
            if profile.getUseAnalysisProfilePrice():
                analysis_profiles.append(profile)
            else:
                # we only need the analysis service keywords from these profiles
                to_be_billed += [service.getKeyword() for service in
                                 profile.getService()]
        # So far we have three arrays:
        #   - analyses: has all analyses (even if they are included inside a
        # profile or not)
        #   - analysis_profiles: has the profiles with "Use Analysis Profile
        # Price" enabled
        #   - to_be_quoted: has analysis services keywords from analysis
        # profiles with "Use Analysis Profile Price"
        #     disabled
        # If a profile has its own price, we don't need their analises'
        # prices, so we have to quit all
        # analysis belonging to that profile. But if another profile has the
        # same analysis service but has
        # "Use Analysis Profile Price" disabled, the service must be included
        #  as billable.
        for profile in analysis_profiles:
            for analysis_service in profile.getService():
                for analysis in analyses:
                    if analysis_service.getKeyword() == analysis.getService().getKeyword() and \
                       analysis.getService().getKeyword() not in to_be_billed:

                        analyses.remove(analysis)
        return analyses, analysis_profiles

    def getServicesAndProfiles(self):
        """This function gets all analysis services and all profiles and removes
        the services belonging to a profile.

        :returns: a tuple of three lists, where the first list contains the
        analyses and the second list the profiles.
        The third contains the analyses objects used by the profiles.
        """
        # Getting requested analyses
        workflow = getToolByName(self, 'portal_workflow')
        analyses = []
        # profile_analyses contains the profile's analyses (analysis !=
        # service") objects to obtain
        # the correct price later
        profile_analyses = []
        IGNORED_STATES = ('not_requested', 'retracted', 'sample_received')
        for analysis in self.objectValues('Analysis'):
            review_state = workflow.getInfoFor(analysis, 'review_state', '')
            if review_state not in IGNORED_STATES:
                analyses.append(analysis)
        # Getting all profiles
        analysis_profiles = self.getProfiles() if len(
            self.getProfiles()) > 0 else []
        # Cleaning services included in profiles
        for profile in analysis_profiles:
            for analysis_service in profile.getService():
                for analysis in analyses:
                    if analysis_service.getKeyword() == analysis.getService(

                    ).getKeyword():
                        analyses.remove(analysis)
                        profile_analyses.append(analysis)
        return analyses, analysis_profiles, profile_analyses

    security.declareProtected(View, 'getSubtotal')

    def getSubtotal(self):
        """Compute Subtotal (without member discount and without vat)
        """
        analyses, a_profiles = self.getBillableItems()
        return sum(
            [Decimal(obj.getPrice()) for obj in analyses] +
            [Decimal(obj.getAnalysisProfilePrice()) for obj in a_profiles]
        )

    security.declareProtected(View, 'getSubtotalVATAmount')

    def getSubtotalVATAmount(self):
        """Compute VAT amount without member discount
        """
        analyses, a_profiles = self.getBillableItems()
        if len(analyses) > 0 or len(a_profiles) > 0:
            return sum(
                [Decimal(o.getVATAmount()) for o in analyses] +
                [Decimal(o.getVATAmount()) for o in a_profiles]
            )
        return 0

    security.declareProtected(View, 'getSubtotalTotalPrice')

    def getSubtotalTotalPrice(self):
        """Compute the price with VAT but no member discount
        """
        return self.getSubtotal() + self.getSubtotalVATAmount()

    security.declareProtected(View, 'getDiscountAmount')

    def getDiscountAmount(self):
        """It computes and returns the analysis service's discount amount
        without VAT
        """
        has_client_discount = self.aq_parent.getMemberDiscountApplies()
        if has_client_discount:
            discount = Decimal(self.getDefaultMemberDiscount())
            return Decimal(self.getSubtotal() * discount / 100)
        else:
            return 0

    def getVATAmount(self):
        """It computes the VAT amount from (subtotal-discount.)*VAT/100, but
        each analysis has its own VAT!

        :returns: the analysis request VAT amount with the discount
        """
        has_client_discount = self.aq_parent.getMemberDiscountApplies()
        VATAmount = self.getSubtotalVATAmount()
        if has_client_discount:
            discount = Decimal(self.getDefaultMemberDiscount())
            return Decimal((1 - discount / 100) * VATAmount)
        else:
            return VATAmount

    security.declareProtected(View, 'getTotalPrice')

    def getTotalPrice(self):
        """It gets the discounted price from analyses and profiles to obtain the
        total value with the VAT and the discount applied

        :returns: the analysis request's total price including the VATs and discounts
        """
        price = (self.getSubtotal() - self.getDiscountAmount() +
                 self.getVATAmount())
        return price

    getTotal = getTotalPrice

    security.declareProtected(ManageInvoices, 'issueInvoice')

    # noinspection PyUnusedLocal
    def issueInvoice(self, REQUEST=None, RESPONSE=None):
        """Issue invoice
        """
        # check for an adhoc invoice batch for this month
        # noinspection PyCallingNonCallable
        now = DateTime()
        batch_month = now.strftime('%b %Y')
        batch_title = '%s - %s' % (batch_month, 'ad hoc')
        invoice_batch = None
        for b_proxy in self.portal_catalog(portal_type='InvoiceBatch',
                                           Title=batch_title):
            invoice_batch = b_proxy.getObject()
        if not invoice_batch:
            # noinspection PyCallingNonCallable
            first_day = DateTime(now.year(), now.month(), 1)
            start_of_month = first_day.earliestTime()
            last_day = first_day + 31
            # noinspection PyUnresolvedReferences
            while last_day.month() != now.month():
                last_day -= 1
            # noinspection PyUnresolvedReferences
            end_of_month = last_day.latestTime()

            invoices = self.invoices
            batch_id = invoices.generateUniqueId('InvoiceBatch')
            invoice_batch = _createObjectByType("InvoiceBatch", invoices,
                                                batch_id)
            invoice_batch.edit(
                title=batch_title,
                BatchStartDate=start_of_month,
                BatchEndDate=end_of_month,
            )
            invoice_batch.processForm()

        client_uid = self.getClientUID()
        # Get the created invoice
        invoice = invoice_batch.createInvoice(client_uid, [self, ])
        invoice.setAnalysisRequest(self)
        # Set the created invoice in the schema
        self.Schema()['Invoice'].set(self, invoice)

    security.declarePublic('printInvoice')

    # noinspection PyUnusedLocal
    def printInvoice(self, REQUEST=None, RESPONSE=None):
        """Print invoice
        """
        invoice = self.getInvoice()
        invoice_url = invoice.absolute_url()
        RESPONSE.redirect('{}/invoice_print'.format(invoice_url))

    @deprecated(comment="bika.lims.content.analysisrequest.addARAttachment "
                        "is deprecated and will be removed in Bika LIMS 3.3. "
                        "Please use the view 'attachments_view' instead.")
    def addARAttachment(self, REQUEST=None, RESPONSE=None):
        """Add the file as an attachment
        """
        workflow = getToolByName(self, 'portal_workflow')

        this_file = self.REQUEST.form['AttachmentFile_file']
        if 'Analysis' in self.REQUEST.form:
            analysis_uid = self.REQUEST.form['Analysis']
        else:
            analysis_uid = None

        attachmentid = self.generateUniqueId('Attachment')
        attachment = _createObjectByType("Attachment", self.aq_parent,
                                         attachmentid)
        attachment.edit(
            AttachmentFile=this_file,
            AttachmentType=self.REQUEST.form.get('AttachmentType', ''),
            AttachmentKeys=self.REQUEST.form['AttachmentKeys'])
        attachment.processForm()
        attachment.reindexObject()

        if analysis_uid:
            tool = getToolByName(self, REFERENCE_CATALOG)
            analysis = tool.lookupObject(analysis_uid)
            others = analysis.getAttachment()
            attachments = []
            for other in others:
                attachments.append(other.UID())
            attachments.append(attachment.UID())
            analysis.setAttachment(attachments)
            if workflow.getInfoFor(analysis,
                                   'review_state') == 'attachment_due':
                workflow.doActionFor(analysis, 'attach')
        else:
            others = self.getAttachment()
            attachments = []
            for other in others:
                attachments.append(other.UID())
            attachments.append(attachment.UID())

            self.setAttachment(attachments)

        if REQUEST['HTTP_REFERER'].endswith('manage_results'):
            RESPONSE.redirect('{}/manage_results'.format(self.absolute_url()))
        else:
            RESPONSE.redirect(self.absolute_url())

    @deprecated(comment="bika.lims.content.analysisrequest.delARAttachment "
                        "is deprecated and will be removed in Bika LIMS 3.3. "
                        "Please use the view 'attachments_view' instead.")
    def delARAttachment(self, REQUEST=None, RESPONSE=None):
        """Delete the attachment
        """
        tool = getToolByName(self, REFERENCE_CATALOG)
        if 'Attachment' in self.REQUEST.form:
            attachment_uid = self.REQUEST.form['Attachment']
            attachment = tool.lookupObject(attachment_uid)
            parent_r = attachment.getRequest()
            parent_a = attachment.getAnalysis()

            parent = parent_a if parent_a else parent_r
            others = parent.getAttachment()
            attachments = []
            for other in others:
                if not other.UID() == attachment_uid:
                    attachments.append(other.UID())
            parent.setAttachment(attachments)
            client = attachment.aq_parent
            ids = [attachment.getId(), ]
            BaseFolder.manage_delObjects(client, ids, REQUEST)

        RESPONSE.redirect(self.REQUEST.get_header('referer'))

    security.declarePublic('getVerifier')

    def getVerifier(self):
        wtool = getToolByName(self, 'portal_workflow')
        mtool = getToolByName(self, 'portal_membership')

        verifier = None
        # noinspection PyBroadException
        try:
            review_history = wtool.getInfoFor(self, 'review_history')
        except:
            return 'access denied'

        if not review_history:
            return 'no history'
        for items in review_history:
            action = items.get('action')
            if action != 'verify':
                continue
            actor = items.get('actor')
            member = mtool.getMemberById(actor)
            verifier = member.getProperty('fullname')
            if verifier is None or verifier == '':
                verifier = actor
        return verifier

    security.declarePublic('getContactUIDForUser')

    def getContactUIDForUser(self):
        """get the UID of the contact associated with the authenticated user
        """
        user = self.REQUEST.AUTHENTICATED_USER
        user_id = user.getUserName()
        pc = getToolByName(self, 'portal_catalog')
        r = pc(portal_type='Contact',
               getUsername=user_id)
        if len(r) == 1:
            return r[0].UID

    security.declarePublic('current_date')

    def current_date(self):
        """return current date
        """
        # noinspection PyCallingNonCallable
        return DateTime()

    def getQCAnalyses(self, qctype=None, review_state=None):
        """return the QC analyses performed in the worksheet in which, at
        least, one sample of this AR is present.

        Depending on qctype value, returns the analyses of:

            - 'b': all Blank Reference Samples used in related worksheet/s
            - 'c': all Control Reference Samples used in related worksheet/s
            - 'd': duplicates only for samples contained in this AR

        If qctype==None, returns all type of qc analyses mentioned above
        """
        qcanalyses = []
        suids = []
        ans = self.getAnalyses()
        wf = getToolByName(self, 'portal_workflow')
        for an in ans:
            an = an.getObject()
            if an.getServiceUID() not in suids:
                suids.append(an.getServiceUID())

        def valid_dup(wan):
            if wan.portal_type == 'ReferenceAnalysis':
                return False
            an_state = wf.getInfoFor(wan, 'review_state')
            return \
                wan.portal_type == 'DuplicateAnalysis' \
                and wan.getRequestID() == self.id \
                and (review_state is None or an_state in review_state)

        def valid_ref(wan):
            if wan.portal_type != 'ReferenceAnalysis':
                return False
            an_state = wf.getInfoFor(wan, 'review_state')
            an_reftype = wan.getReferenceType()
            return wan.getServiceUID() in suids \
                and wan not in qcanalyses \
                and (qctype is None or an_reftype == qctype) \
                and (review_state is None or an_state in review_state)

        for an in ans:
            an = an.getObject()
            br = an.getBackReferences('WorksheetAnalysis')
            if len(br) > 0:
                ws = br[0]
                was = ws.getAnalyses()
                for wa in was:
                    if valid_dup(wa):
                        qcanalyses.append(wa)
                    elif valid_ref(wa):
                        qcanalyses.append(wa)

        return qcanalyses

    def isInvalid(self):
        """return if the Analysis Request has been invalidated
        """
        workflow = getToolByName(self, 'portal_workflow')
        return workflow.getInfoFor(self, 'review_state') == 'invalid'

    def getLastChild(self):
        """return the last child Request due to invalidation
        """
        child = self.getChildAnalysisRequest()
        while child and child.getChildAnalysisRequest():
            child = child.getChildAnalysisRequest()
        return child

    def getRequestedAnalyses(self):
        """It returns all requested analyses, even if they belong to an
        analysis profile or not.
        """
        #
        # title=Get requested analyses
        #
        result = []
        cats = {}
        workflow = getToolByName(self, 'portal_workflow')
        for analysis in self.getAnalyses(full_objects=True):
            review_state = workflow.getInfoFor(analysis, 'review_state')
            if review_state == 'not_requested':
                continue
            service = analysis.getService()
            category_name = service.getCategoryTitle()
            if category_name not in cats:
                cats[category_name] = {}
            cats[category_name][analysis.Title()] = analysis
        cat_keys = sorted(cats.keys(), key=methodcaller('lower'))
        for cat_key in cat_keys:
            analyses = cats[cat_key]
            analysis_keys = sorted(analyses.keys(),
                                   key=methodcaller('lower'))
            for analysis_key in analysis_keys:
                result.append(analyses[analysis_key])
        return result

    def getSamplingRoundUID(self):
        """Obtains the sampling round UID
        :returns: UID
        """
        if self.getSamplingRound():
            return self.getSamplingRound().UID()
        else:
            return ''

    def setResultsRange(self, value=None):
        """Sets the spec values for this AR.
        1 - Client specs where (spec.Title) matches (ar.SampleType.Title)
        2 - Lab specs where (spec.Title) matches (ar.SampleType.Title)
        3 - Take override values from instance.Specification
        4 - Take override values from the form (passed here as parameter
        'value').

        The underlying field value is a list of dictionaries.

        The value parameter may be a list of dictionaries, or a dictionary (of
        dictionaries).  In the last case, the keys are irrelevant, but in both
        cases the specs must contain, at minimum, the "keyword", "min", "max",
        and "error" fields.

        Value will be stored in ResultsRange field as list of dictionaries
        """
        rr = {}
        sample = self.getSample()
        if not sample:
            # portal_factory
            return []
        stt = self.getSample().getSampleType().Title()
        bsc = getToolByName(self, 'bika_setup_catalog')
        # 1 or 2: rr = Client specs where (spec.Title) matches (
        # ar.SampleType.Title)
        for folder in self.aq_parent, self.bika_setup.bika_analysisspecs:
            proxies = bsc(portal_type='AnalysisSpec',
                          getSampleTypeTitle=stt,
                          ClientUID=folder.UID())
            if proxies:
                rr = dicts_to_dict(proxies[0].getObject().getResultsRange(),
                                   'keyword')
                break
        # 3: rr += override values from instance.Specification
        ar_spec = self.getSpecification()
        if ar_spec:
            ar_spec_rr = ar_spec.getResultsRange()
            rr.update(dicts_to_dict(ar_spec_rr, 'keyword'))
        # 4: rr += override values from the form (value=dict key=service_uid)
        if value:
            if type(value) in (list, tuple):
                value = dicts_to_dict(value, "keyword")
            elif type(value) == dict:
                value = dicts_to_dict(value.values(), "keyword")
            rr.update(value)
        return self.Schema()['ResultsRange'].set(self, rr.values())

    security.declarePublic('getDatePublished')

    def getDatePublished(self):
        return getTransitionDate(self, 'publish')

    def getSamplers(self):
        return getUsers(self, ['LabManager', 'Sampler'])

    def getPreparationWorkflows(self):
        """Return a list of sample preparation workflows.  These are identified
        by scanning all workflow IDs for those beginning with "sampleprep".
        """
        wf = self.portal_workflow
        ids = wf.getWorkflowIds()
        sampleprep_ids = [wid for wid in ids if wid.startswith('sampleprep')]
        prep_workflows = [['', ''], ]
        for workflow_id in sampleprep_ids:
            workflow = wf.getWorkflowById(workflow_id)
            prep_workflows.append([workflow_id, workflow.title])
        return DisplayList(prep_workflows)

    def getDepartments(self):
        """Returns a set with the departments assigned to the Analyses
        from this Analysis Request
        """
        ans = [an.getObject() for an in self.getAnalyses()]
        depts = [an.getService().getDepartment() for an in ans if
                 an.getService().getDepartment()]
        return set(depts)

    def getResultsInterpretationByDepartment(self, department=None):
        """Returns the results interpretation for this Analysis Request
           and department. If department not set, returns the results
           interpretation tagged as 'General'.

        :returns: a dict with the following keys:
            {'uid': <department_uid> or 'general', 'richtext': <text/plain>}
        """
        uid = department.UID() if department else 'general'
        rows = self.Schema()['ResultsInterpretationDepts'].get(self)
        row = [row for row in rows if row.get('uid') == uid]
        if len(row) > 0:
            row = row[0]
        elif uid == 'general' \
                and hasattr(self, 'getResultsInterpretation') \
                and self.getResultsInterpretation():
            row = {'uid': uid, 'richtext': self.getResultsInterpretation()}
        else:
            row = {'uid': uid, 'richtext': ''}
        return row

    def getAnalysisServiceSettings(self, uid):
        """Returns a dictionary with the settings for the analysis service that
        match with the uid provided.

        If there are no settings for the analysis service and
        analysis requests:

        1. looks for settings in AR's ARTemplate. If found, returns the
           settings for the AnalysisService set in the Template
        2. If no settings found, looks in AR's ARProfile. If found, returns the
           settings for the AnalysisService from the AR Profile. Otherwise,
           returns a one entry dictionary with only the key 'uid'
        """
        sets = [s for s in self.getAnalysisServicesSettings()
                if s.get('uid', '') == uid]

        # Created by using an ARTemplate?
        if not sets and self.getTemplate():
            adv = self.getTemplate().getAnalysisServiceSettings(uid)
            sets = [adv] if 'hidden' in adv else []

        # Created by using an AR Profile?
        if not sets and self.getProfiles():
            adv = []
            adv += [profile.getAnalysisServiceSettings(uid) for profile in
                    self.getProfiles()]
            sets = adv if 'hidden' in adv[0] else []

        return sets[0] if sets else {'uid': uid}

    def getPartitions(self):
        """This functions returns the partitions from the analysis request's
        analyses.

        :returns: a list with the full partition objects
        """
        analyses = self.getRequestedAnalyses()
        partitions = []
        for analysis in analyses:
            if analysis.getSamplePartition() not in partitions:
                partitions.append(analysis.getSamplePartition())
        return partitions

    def getContainers(self):
        """This functions returns the containers from the analysis request's
        analyses

        :returns: a list with the full partition objects
        """
        partitions = self.getPartitions()
        containers = []
        for partition in partitions:
            if partition.getContainer():
                containers.append(partition.getContainer())
        return containers

    def isAnalysisServiceHidden(self, uid):
        """Checks if the analysis service that match with the uid provided must
        be hidden in results. If no hidden assignment has been set for the
        analysis in this request, returns the visibility set to the analysis
        itself.

        Raise a TypeError if the uid is empty or None

        Raise a ValueError if there is no hidden assignment in this request or
        no analysis service found for this uid.
        """
        if not uid:
            raise TypeError('None type or empty uid')
        sets = self.getAnalysisServiceSettings(uid)
        if 'hidden' not in sets:
            uc = getToolByName(self, 'uid_catalog')
            serv = uc(UID=uid)
            if serv and len(serv) == 1:
                return serv[0].getObject().getRawHidden()
            else:
                raise ValueError('{} is not valid'.format(uid))
        return sets.get('hidden', False)

    def getRejecter(self):
        """If the Analysis Request has been rejected, returns the user who did the
        rejection. If it was not rejected or the current user has not enough
        privileges to access to this information, returns None.
        """
        wtool = getToolByName(self, 'portal_workflow')
        mtool = getToolByName(self, 'portal_membership')
        # noinspection PyBroadException
        try:
            review_history = wtool.getInfoFor(self, 'review_history')
        except:
            return None
        for items in review_history:
            action = items.get('action')
            if action != 'reject':
                continue
            actor = items.get('actor')
            return mtool.getMemberById(actor)
        return None

    def isVerifiable(self):
        """Checks it the current Analysis Request can be verified. This is, its
        not a cancelled Analysis Request and all the analyses that contains
        are verifiable too. Note that verifying an Analysis Request is in fact,
        the same as verifying all the analyses that contains. Therefore, the
        'verified' state of an Analysis Request shouldn't be a 'real' state,
        rather a kind-of computed state, based on the statuses of the analyses
        it contains. This is why this function checks if the analyses
        contained are verifiable, cause otherwise, the Analysis Request will
        never be able to reach a 'verified' state.
        :return: True or False
        """
        # Check if the analysis request is active
        workflow = getToolByName(self, "portal_workflow")
        objstate = workflow.getInfoFor(self, 'cancellation_state', 'active')
        if objstate == "cancelled":
            return False

        # Check if the analysis request state is to_be_verified
        review_state = workflow.getInfoFor(self, "review_state")
        if review_state == 'to_be_verified':
            # This means that all the analyses from this analysis request have
            # already been transitioned to a 'verified' state, and so the
            # analysis request itself
            return True
        else:
            # Check if the analyses contained in this analysis request are
            # verifiable. Only check those analyses not cancelled and that
            # are not in a kind-of already verified state
            canbeverified = True
            omit = ['published', 'retracted', 'rejected', 'verified']
            for a in self.getAnalyses(full_objects=True):
                st = workflow.getInfoFor(a, 'cancellation_state', 'active')
                if st == 'cancelled':
                    continue
                st = workflow.getInfoFor(a, 'review_state')
                if st in omit:
                    continue
                # Can the analysis be verified?
                if not a.isVerifiable(self):
                    canbeverified = False
                    break
            return canbeverified

    def isUserAllowedToVerify(self, member):
        """Checks if the specified user has enough privileges to verify the
        current AR. Apart from the roles, this function also checks if the
        current user has enough privileges to verify all the analyses contained
        in this Analysis Request. Note that this function only returns if the
        user can verify the analysis request according to his/her privileges
        and the analyses contained (see isVerifiable function)

        :member: user to be tested
        :returns: true or false
        """
        # Check if the user has "Bika: Verify" privileges
        username = member.getUserName()
        allowed = ploneapi.user.has_permission(VerifyPermission, username=username)
        if not allowed:
            return False
        # Check if the user is allowed to verify all the contained analyses
        notallowed = [a for a in self.getAnalyses(full_objects=True)
                      if not a.isUserAllowedToVerify(member)]
        return not notallowed

    def guard_verify_transition(self):
        """Checks if the verify transition can be performed to the current
        Analysis Request by the current user depending on the user roles, as
        well as the statuses of the analyses assigned to this Analysis Request

        :returns: true or false
        """
        mtool = getToolByName(self, "portal_membership")
        # Check if the Analysis Request is in a "verifiable" state
        if self.isVerifiable():
            # Check if the user can verify the Analysis Request
            member = mtool.getAuthenticatedMember()
            return self.isUserAllowedToVerify(member)
        return False

    def guard_unassign_transition(self):
        """Allow or disallow transition depending on our children's states
        """
        if not isBasicTransitionAllowed(self):
            return False
        if self.getAnalyses(worksheetanalysis_review_state='unassigned'):
            return True
        if not self.getAnalyses(worksheetanalysis_review_state='assigned'):
            return True
        return False

    def guard_assign_transition(self):
        """Allow or disallow transition depending on our children's states
        """
        if not isBasicTransitionAllowed(self):
            return False
        if not self.getAnalyses(worksheetanalysis_review_state='assigned'):
            return False
        if self.getAnalyses(worksheetanalysis_review_state='unassigned'):
            return False
        return True

    def guard_receive_transition(self):
        """Prevent the receive transition from being available
        if object is cancelled
        """
        return isBasicTransitionAllowed(self)

    def guard_sample_prep_transition(self):
        sample = self.getSample()
        return sample.guard_sample_prep_transition()

    def guard_sample_prep_complete_transition(self):
        sample = self.getSample()
        return sample.guard_sample_prep_complete_transition()

    def guard_schedule_sampling_transition(self):
        """Prevent the transition if:

        - if the user isn't part of the sampling coordinators group
          and "sampling schedule" checkbox is set in bika_setup
        - if no date and samples have been defined
          and "sampling schedule" checkbox is set in bika_setup
        """
        if self.bika_setup.getScheduleSamplingEnabled() and \
                isBasicTransitionAllowed(self):
            return True
        return False

    def workflow_script_receive(self):
        if skip(self, "receive"):
            return
        workflow = getToolByName(self, 'portal_workflow')
        # noinspection PyCallingNonCallable
        self.setDateReceived(DateTime())
        self.reindexObject(idxs=["review_state", "getDateReceived", ])
        # receive the AR's sample
        sample = self.getSample()
        if not skip(sample, 'receive', peek=True):
            # unless this is a secondary AR
            if workflow.getInfoFor(sample, 'review_state') == 'sample_due':
                workflow.doActionFor(sample, 'receive')
        # receive all analyses in this AR.
        analyses = self.getAnalyses(review_state='sample_due')
        for analysis in analyses:
            if not skip(analysis, 'receive'):
                workflow.doActionFor(analysis.getObject(), 'receive')

    def workflow_script_preserve(self):
        if skip(self, "preserve"):
            return
        workflow = getToolByName(self, 'portal_workflow')
        # transition our sample
        sample = self.getSample()
        if not skip(sample, "preserve", peek=True):
            workflow.doActionFor(sample, "preserve")

    def workflow_script_submit(self):
        if skip(self, "submit"):
            return
        self.reindexObject(idxs=["review_state", ])

    def workflow_script_sampling_workflow(self):
        if skip(self, "sampling_workflow"):
            return
        sample = self.getSample()
        sd = sample.getSamplingDate()
        # noinspection PyCallingNonCallable
        if sd and sd > DateTime():
            sample.future_dated = True

    def workflow_script_no_sampling_workflow(self):
        if skip(self, "no_sampling_workflow"):
            return
        sample = self.getSample()
        sd = sample.getSamplingDate()
        # noinspection PyCallingNonCallable
        if sd and sd > DateTime():
            sample.future_dated = True

    def workflow_script_attach(self):
        if skip(self, "attach"):
            return
        self.reindexObject(idxs=["review_state", ])
        # Don't cascade. Shouldn't be attaching ARs for now (if ever).
        return

    def workflow_script_sample(self):
        # no skip check here: the sampling workflow UI is odd
        # if skip(self, "sample"):
        #     return
        # transition our sample
        workflow = getToolByName(self, 'portal_workflow')
        sample = self.getSample()
        if not skip(sample, "sample", peek=True):
            workflow.doActionFor(sample, "sample")

    # def workflow_script_to_be_preserved(self):
    #     if skip(self, "to_be_preserved"):
    #         return
    #     pass

    # def workflow_script_sample_due(self):
    #     if skip(self, "sample_due"):
    #         return
    #     pass

    # def workflow_script_retract(self):
    #     if skip(self, "retract"):
    #         return
    #     pass

    def workflow_script_verify(self):
        if skip(self, "verify"):
            return
        self.reindexObject(idxs=["review_state", ])
        if "verify all analyses" not in self.REQUEST['workflow_skiplist']:
            # verify all analyses in this AR.
            analyses = self.getAnalyses(review_state='to_be_verified')
            for analysis in analyses:
                if (hasattr(analysis, 'getNumberOfVerifications') and
                        hasattr(analysis, 'getNumberOfRequiredVerifications')):

                    # For the 'verify' transition to (effectively) take place,
                    # we need to check if the required number of verifications
                    # for the analysis is, at least, the number of verifications
                    # performed previously +1
                    success = True
                    revers = analysis.getNumberOfRequiredVerifications()
                    nmvers = analysis.getNumberOfVerifications()
                    username = getToolByName(self, 'portal_membership').getAuthenticatedMember().getUserName()
                    analysis.addVerificator(username)
                    if revers - nmvers <= 1:
                        success, message = doActionFor(analysis, 'verify')
                        if not success:
                            # If failed, delete last verificator
                            analysis.deleteLastVerificator()
                else:
                    doActionFor(analysis, 'verify')

    def workflow_script_publish(self):
        if skip(self, "publish"):
            return
        self.reindexObject(idxs=["review_state", "getDatePublished", ])
        if "publish all analyses" not in self.REQUEST['workflow_skiplist']:
            # publish all analyses in this AR. (except not requested ones)
            analyses = self.getAnalyses(review_state='verified')
            for analysis in analyses:
                doActionFor(analysis.getObject(), "publish")

    def workflow_script_reinstate(self):
        if skip(self, "reinstate"):
            return
        self.reindexObject(idxs=["cancellation_state", ])
        # activate all analyses in this AR.
        analyses = self.getAnalyses(cancellation_state='cancelled')
        for analysis in analyses:
            doActionFor(analysis.getObject(), 'reinstate')

    def workflow_script_cancel(self):
        if skip(self, "cancel"):
            return
        self.reindexObject(idxs=["cancellation_state", ])
        # deactivate all analyses in this AR.
        analyses = self.getAnalyses(cancellation_state='active')
        for analysis in analyses:
            doActionFor(analysis.getObject(), 'cancel')

    def workflow_script_schedule_sampling(self):
        """This function runs all the needed process for that action
        """
        workflow = getToolByName(self, 'portal_workflow')
        sample = self.getSample()
        # We have to set the defined sampling date and sampler and
        # produce a transition in it
        if workflow.getInfoFor(sample, 'review_state') == \
                'to_be_sampled':
            # transact the related sample
            doActionFor(sample, 'schedule_sampling')

    def workflow_script_reject(self):
        workflow = getToolByName(self, 'portal_workflow')
        sample = self.getSample()
        self.reindexObject(idxs=["review_state", ])
        if workflow.getInfoFor(sample, 'review_state') != 'rejected':
            # Setting the rejection reasons in sample
            sample.setRejectionReasons(self.getRejectionReasons())
            workflow.doActionFor(sample, "reject")
        # deactivate all analyses in this AR.
        analyses = self.getAnalyses()
        for analysis in analyses:
            doActionFor(analysis.getObject(), 'reject')
        if self.bika_setup.getNotifyOnRejection():
            # Notify the Client about the Rejection.
            notify_rejection(self)

registerType(AnalysisRequest, PROJECTNAME)
