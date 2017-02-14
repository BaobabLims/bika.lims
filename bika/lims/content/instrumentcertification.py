# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

import math

from DateTime import DateTime
from AccessControl import ClassSecurityInfo

from Products.Archetypes.atapi import BaseFolder
from Products.Archetypes.atapi import DisplayList
from Products.Archetypes.atapi import registerType

from zope.interface import implements
from plone import api as ploneapi

# Schema and Fields
from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import ReferenceField
from Products.Archetypes.atapi import ComputedField
from Products.Archetypes.atapi import DateTimeField
from Products.Archetypes.atapi import StringField
from Products.Archetypes.atapi import TextField
from Products.Archetypes.atapi import FileField
from Products.Archetypes.atapi import BooleanField

# Widgets
from Products.Archetypes.atapi import ComputedWidget
from Products.Archetypes.atapi import StringWidget
from Products.Archetypes.atapi import TextAreaWidget
from Products.Archetypes.atapi import FileWidget
from Products.Archetypes.atapi import BooleanWidget
from bika.lims.browser.widgets import DateTimeWidget
from bika.lims.browser.widgets import ReferenceWidget

# bika.lims imports
from bika.lims.config import PROJECTNAME
from bika.lims import bikaMessageFactory as _
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.interfaces import IInstrumentCertification


schema = BikaSchema.copy() + Schema((

    StringField(
        'TaskID',
        widget=StringWidget(
            label=_("Task ID"),
            description=_("The instrument's ID in the lab's asset register"),
        )
    ),

    ReferenceField(
        'Instrument',
        allowed_types=('Instrument',),
        relationship='InstrumentCertificationInstrument',
        widget=StringWidget(
            visible=False,
        )
    ),

    ComputedField(
        'InstrumentUID',
        expression='context.getInstrument() and context.getInstrument().UID() or None',
        widget=ComputedWidget(
            visible=False,
        ),
    ),

    # Set the Certificate as Internal
    # When selected, the 'Agency' field is hidden
    BooleanField(
        'Internal',
        default=False,
        widget=BooleanWidget(
            label=_("Internal Certificate"),
            description=_("Select if is an in-house calibration certificate")
        )
    ),

    StringField(
        'Agency',
        widget=StringWidget(
            label=_("Agency"),
            description=_("Organization responsible of granting the calibration certificate")
        ),
    ),

    DateTimeField(
        'Date',
        widget=DateTimeWidget(
            label=_("Date"),
            description=_("Date when the calibration certificate was granted"),
        ),
    ),

    DateTimeField(
        'ValidFrom',
        with_time=1,
        with_date=1,
        required=1,
        widget=DateTimeWidget(
            label=_("From"),
            description=_("Date from which the calibration certificate is valid"),
        ),
    ),

    DateTimeField(
        'ValidTo',
        with_time=1,
        with_date=1,
        required=1,
        widget=DateTimeWidget(
            label=_("To"),
            description=_("Date until the certificate is valid"),
        ),
    ),

    ReferenceField(
        'Preparator',
        vocabulary='getLabContacts',
        allowed_types=('LabContact',),
        relationship='LabContactInstrumentCertificatePreparator',
        widget=ReferenceWidget(
            checkbox_bound=0,
            label=_("Prepared by"),
            description=_("The person at the supplier who prepared the certificate"),
            size=30,
            base_query={'inactive_state': 'active'},
            showOn=True,
            colModel=[
                {'columnName': 'UID', 'hidden': True},
                {'columnName': 'JobTitle', 'width': '20', 'label': _('Job Title')},
                {'columnName': 'Title', 'width': '80', 'label': _('Name')}
            ],
        ),
    ),

    ReferenceField(
        'Validator',
        vocabulary='getLabContacts',
        allowed_types=('LabContact',),
        relationship='LabContactInstrumentCertificateValidator',
        widget=ReferenceWidget(
            checkbox_bound=0,
            label=_("Approved by"),
            description=_("The person at the supplier who approved the certificate"),
            size=30,
            base_query={'inactive_state': 'active'},
            showOn=True,
            colModel=[
                {'columnName': 'UID', 'hidden': True},
                {'columnName': 'JobTitle', 'width': '20', 'label': _('Job Title')},
                {'columnName': 'Title', 'width': '80', 'label': _('Name')}
            ],
        ),
    ),

    FileField(
        'Document',
        widget=FileWidget(
            label=_("Report upload"),
            description=_("Load the certificate document here"),
        )
    ),

    TextField(
        'Remarks',
        searchable=True,
        default_content_type='text/x-web-intelligent',
        allowable_content_types=('text/plain', ),
        default_output_type="text/plain",
        mode="rw",
        widget=TextAreaWidget(
            macro="bika_widgets/remarks",
            label=_("Remarks"),
            append_only=True,
        ),
    ),

))

schema['title'].widget.label = _("Certificate Code")


class InstrumentCertification(BaseFolder):
    implements(IInstrumentCertification)
    security = ClassSecurityInfo()
    schema = schema
    displayContentsTab = False
    _at_rename_after_creation = True

    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

    def getLabContacts(self):
        bsc = ploneapi.portal.get_tool(self, 'bika_setup_catalog')
        # fallback - all Lab Contacts
        pairs = []
        for contact in bsc(portal_type='LabContact',
                           inactive_state='active',
                           sort_on='sortable_title'):
            pairs.append((contact.UID, contact.Title))
        return DisplayList(pairs)

    def isValid(self):
        """Returns if the current certificate is in a valid date range
        """

        today = DateTime()
        valid_from = self.getValidFrom()
        valid_to = self.getValidTo()

        return valid_from <= today <= valid_to

    def getDaysToExpire(self):
        """Returns the days until this certificate expires

        :returns: Days until the certificate expires
        :rtype: int
        """

        # invalid certificates are already expired
        if not self.isValid():
            return 0

        today = DateTime()
        valid_to = self.getValidTo()

        delta = valid_to - today
        return int(math.ceil(delta))

    def getWeeksToExpire(self):
        """Returns the number weeks until this certificate expires

        :returns: Weeks until the certificate expires
        :rtype: float
        """

        days = self.getDaysToExpire()
        return days / 7


registerType(InstrumentCertification, PROJECTNAME)
