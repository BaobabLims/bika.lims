# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from zope.interface import alsoProvides

from Products.CMFCore import permissions
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType

from Products.CMFEditions.Permissions import SaveNewVersion
from Products.CMFEditions.Permissions import ApplyVersionControl
from Products.CMFEditions.Permissions import AccessPreviousVersions

from bika.lims import logger
from bika.lims.utils import tmpID
from bika.lims import bikaMessageFactory as _

# Bika LIMS Constants
from bika.lims.config import VERSIONABLE_TYPES
# Bika LIMS Permissions
from bika.lims.permissions import ManageClients
from bika.lims.permissions import AddAnalysisSpec
from bika.lims.permissions import CancelAndReinstate
from bika.lims.permissions import ManagePricelists
from bika.lims.permissions import ManageARImport
# Bika LIMS Interfaces
from bika.lims.interfaces import IARImportFolder
from bika.lims.interfaces import IHaveNoBreadCrumbs

HAS_CMF_EDITIONS = False
try:
    from Products.CMFEditions.setuphandlers import DEFAULT_POLICIES  # noqa
    # we're on plone < 4.1, configure versionable types manually
    HAS_CMF_EDITIONS = True
except ImportError:
    # repositorytool.xml will be used
    pass


def setupVarious(context):
    """
    Final Bika import steps.
    """
    if context.readDataFile('bika.lims_various.txt') is None:
        return

    site = context.getSite()
    gen = BikaGenerator()
    gen.setupGroups(site)
    gen.setupPortalContent(site)
    gen.setupPermissions(site)
    gen.setupTopLevelFolders(site)
    if HAS_CMF_EDITIONS:
        gen.setupVersioning(site)
    gen.setupCatalogs(site)

    # Plone's jQuery gets clobbered when jsregistry is loaded.
    setup = site.portal_setup
    setup.runImportStepFromProfile(
        'profile-plone.app.jquery:default', 'jsregistry')
    # setup.runImportStepFromProfile('profile-plone.app.jquerytools:default', 'jsregistry')

    create_CAS_IdentifierType(site)


class Empty:
    pass


class BikaGenerator:

    def setupPortalContent(self, portal):
        """ Setup Bika site structure """

        obj = portal._getOb('front-page')
        alsoProvides(obj, IHaveNoBreadCrumbs)
        mp = obj.manage_permission
        mp(permissions.View, ['Anonymous'], 1)

        # remove undesired content objects
        del_ids = []
        for obj_id in ['Members', 'news', 'events']:
            if obj_id in portal.objectIds():
                del_ids.append(obj_id)
        if del_ids:
            portal.manage_delObjects(ids=del_ids)

        # index objects - importing through GenericSetup doesn't
        for obj_id in ('clients',
                       'batches',
                       'invoices',
                       'pricelists',
                       'bika_setup',
                       'methods',
                       'analysisrequests',
                       'referencesamples',
                       'samples',
                       'supplyorders',
                       'worksheets',
                       'reports',
                       'arimports',
                       ):
            try:
                obj = portal._getOb(obj_id)
                obj.unmarkCreationFlag()
                obj.reindexObject()
            except:
                pass

        bika_setup = portal._getOb('bika_setup')
        for obj_id in ('bika_analysiscategories',
                       'bika_analysisservices',
                       'bika_arpriorities',
                       'bika_attachmenttypes',
                       'bika_batchlabels',
                       'bika_calculations',
                       'bika_clienttypes',
                       'bika_containers',
                       'bika_containertypes',
                       'bika_departments',
                       'bika_preservations',
                       'bika_identifiertypes',
                       'bika_instruments',
                       'bika_instrumenttypes',
                       'bika_instrumentlocations',
                       'bika_analysisspecs',
                       'bika_analysisprofiles',
                       'bika_artemplates',
                       'bika_labcontacts',
                       'bika_labproducts',
                       'bika_manufacturers',
                       'bika_sampleconditions',
                       'bika_samplematrices',
                       'bika_samplingdeviations',
                       'bika_samplepoints',
                       'bika_sampletypes',
                       'bika_srtemplates',
                       'bika_storagelocations',
                       'bika_subgroups',
                       'bika_suppliers',
                       'bika_referencedefinitions',
                       'bika_worksheettemplates'):
            try:
                obj = bika_setup._getOb(obj_id)
                obj.unmarkCreationFlag()
                obj.reindexObject()
            except:
                pass

        lab = bika_setup.laboratory
        lab.edit(title=_('Laboratory'))
        lab.unmarkCreationFlag()
        lab.reindexObject()

    def setupGroups(self, portal):
        # Create groups
        portal_groups = portal.portal_groups

        if 'LabManagers' not in portal_groups.listGroupIds():
            try:
                portal_groups.addGroup('LabManagers', title="Lab Managers",
                                       roles=['Member', 'LabManager', 'Site Administrator', ])
            except KeyError:
                portal_groups.addGroup('LabManagers', title="Lab Managers",
                                       roles=['Member', 'LabManager', 'Manager', ])  # Plone < 4.1

        if 'LabClerks' not in portal_groups.listGroupIds():
            portal_groups.addGroup('LabClerks', title="Lab Clerks",
                                   roles=['Member', 'LabClerk'])

        if 'Analysts' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Analysts', title="Lab Technicians",
                                   roles=['Member', 'Analyst'])

        if 'Verifiers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Verifiers', title="Verifiers",
                                   roles=['Verifier'])

        if 'Samplers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Samplers', title="Samplers",
                                   roles=['Sampler'])

        if 'Preservers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Preservers', title="Preservers",
                                   roles=['Preserver'])

        if 'Publishers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Publishers', title="Publishers",
                                   roles=['Publisher'])

        if 'Clients' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Clients', title="Clients",
                                   roles=['Member', 'Client'])

        if 'Suppliers' not in portal_groups.listGroupIds():
            portal_groups.addGroup('Suppliers', title="",
                                   roles=['Member', ])

        if 'RegulatoryInspectors' not in portal_groups.listGroupIds():
            portal_groups.addGroup('RegulatoryInspectors', title="Regulatory Inspectors",
                                   roles=['Member', 'RegulatoryInspector'])

        if 'SamplingCoordinators' not in portal_groups.listGroupIds():
            portal_groups.addGroup('SamplingCoordinators',
                                   title="Sampling Coordinators",
                                   roles=['SamplingCoordinator'])

    def setupPermissions(self, portal):
        """ Set up some suggested role to permission mappings.
        """

        # Bika Setup
        # The `/bika_setup` folder follows the `bika_one_state_workflow`.
        # Please refer to the workflow definition to see the default permissions
        mp = portal.bika_setup.manage_permission
        # We set explicit permissions to access methods to be persistent with the assigned workflow
        mp(permissions.View, ['Authenticated'], 0)
        mp(permissions.ListFolderContents, ['Authenticated'], 0)
        # Front-Page Portlets need to access some information for Anonymous.
        mp(permissions.AccessContentsInformation, ['Anonymous'], 0)

        # Set modify permissions
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager'], 0)
        mp(ApplyVersionControl, ['Authenticated'], 0)
        mp(SaveNewVersion, ['Authenticated'], 0)
        mp(AccessPreviousVersions, ['Authenticated'], 0)

        # Authenticated need to have access to bika_setup objects to create ARs
        for obj in portal.bika_setup.objectValues():
            mp = obj.manage_permission
            mp(permissions.View, ['Authenticated'], 0)
            mp(permissions.AccessContentsInformation, ['Authenticated'], 0)
            mp(permissions.ListFolderContents, ['Authenticated'], 0)

        portal.bika_setup.reindexObject()
        # /Bika Setup

        # Laboratory
        # The `/bika_setup/laboratory` object follows the `bika_one_state_workflow`.
        mp = portal.bika_setup.laboratory.manage_permission
        # We set explicit permissions to access methods to be persistent with the assigned workflow
        mp(permissions.View, ['Anonymous'], 0)
        mp(permissions.ListFolderContents, ['Authenticated'], 0)
        # Front-Page Portlets need to access some information for Anonymous.
        mp(permissions.AccessContentsInformation, ['Anonymous'], 0)
        portal.bika_setup.laboratory.reindexObject()
        # /Laboratory

        # Clients
        # When modifying these defaults, look to subscribers/objectmodified.py
        # Client role (from the Clients Group) must have view permission on /clients, to see the list.
        # This means within a client, perms granted on Client role are available
        # in clients not our own, allowing sideways entry if we're not careful.
        mp = portal.clients.manage_permission

        # Allow authenticated users to see the contents of the client folder
        mp(permissions.View, ['Authenticated'], 0)
        mp(permissions.AccessContentsInformation, ['Authenticated'], 0)
        mp(permissions.ListFolderContents, ['Authenticated'], 0)

        # Set modify permissions
        mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner'], 0)
        mp(ManageClients, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner'], 0)
        mp(AddAnalysisSpec, ['Manager', 'LabManager', 'Owner'], 0)
        portal.clients.reindexObject()

        # We have to manually set the permissions of Contacts according to
        # bika.lims.subscribers.objectmodified, as these types do not contain an own workflow
        contacts = portal.portal_catalog(portal_type="Contact")
        for contact in contacts:
            obj = contact.getObject()
            mp = contact.manage_permission
            mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Owner', 'Analyst', 'Sampler', 'Preserver', 'SamplingCoordinator'], 0)
            mp(permissions.ModifyPortalContent, ['Manager', 'LabManager', 'Owner', 'SamplingCoordinator'], 0)

        # /Clients

        # /worksheets folder permissions
        mp = portal.worksheets.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'Analyst', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'Analyst', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.worksheets.reindexObject()

        # /batches folder permissions
        mp = portal.batches.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Authenticated', 'RegulatoryInspector'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'RegulatoryInspector'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Authenticated', 'RegulatoryInspector'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.batches.reindexObject()

        # /analysisrequests folder permissions
        mp = portal.analysisrequests.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.analysisrequests.reindexObject()

        # /referencesamples folder permissions
        mp = portal.referencesamples.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.referencesamples.reindexObject()

        # /samples folder permissions
        mp = portal.samples.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'SamplingCoordinator'], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'LabClerk', 'Analyst', 'Sampler', 'Preserver', 'RegulatoryInspector', 'SamplingCoordinator'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        portal.samples.reindexObject()

        # /reports folder permissions
        mp = portal.reports.manage_permission
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'Member', 'LabClerk', ], 0)
        mp(permissions.View, ['Manager', 'LabManager', 'LabClerk', 'Member'], 0)
        mp('Access contents information', ['Manager', 'LabManager', 'Member', 'LabClerk', 'Owner'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'LabClerk', 'Owner', 'Member'], 0)

        mp('ATContentTypes: Add Image', ['Manager', 'Labmanager', 'LabClerk', 'Member', ], 0)
        mp('ATContentTypes: Add File', ['Manager', 'Labmanager', 'LabClerk', 'Member', ], 0)
        portal.reports.reindexObject()

        # /invoices folder permissions
        mp = portal.invoices.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(permissions.ListFolderContents, ['Manager', 'LabManager', 'LabClerk', 'Analyst'], 1)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.View, ['Manager', 'LabManager'], 0)
        portal.invoices.reindexObject()

        # /pricelists folder permissions
        mp = portal.pricelists.manage_permission
        mp(CancelAndReinstate, ['Manager', 'LabManager', 'LabClerk'], 0)
        mp(ManagePricelists, ['Manager', 'LabManager', 'Owner'], 1)
        mp(permissions.ListFolderContents, ['Member'], 1)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
        mp(permissions.View, ['Manager', 'LabManager'], 0)
        portal.pricelists.reindexObject()

        # Methods
        # The `/method` folder follows the `bika_one_state_workflow`
        # Please refer to the workflow definition to see the default permissions
        mp = portal.methods.manage_permission
        # We set explicit permissions to access methods to be persistent with the assigned workflow
        mp(permissions.View, ['Authenticated', 'Anonymous'], 0)
        mp(permissions.ListFolderContents, ['Authenticated', 'Anonymous'], 0)
        mp(permissions.AccessContentsInformation, ['Authenticated', 'Anonymous'], 0)
        mp(permissions.AddPortalContent, ['Manager', 'LabManager'], 0)
        mp(CancelAndReinstate, ['Manager', 'LabManager'], 0)
        mp(permissions.DeleteObjects, ['Manager', 'LabManager'], 0)
        portal.methods.reindexObject()

        # /supplyorders folder permissions
        if portal.hasObject("supplyfolders"):
            mp = portal.supplyorders.manage_permission
            mp(CancelAndReinstate, ['Manager', 'LabManager', 'Owner', 'LabClerk'], 0)
            mp(permissions.ListFolderContents, ['LabClerk', ''], 1)
            mp(permissions.AddPortalContent, ['Manager', 'LabManager', 'Owner', 'LabClerk'], 0)
            mp(permissions.DeleteObjects, ['Manager', 'LabManager', 'Owner'], 0)
            mp(permissions.View, ['Manager', 'LabManager', 'LabClerk'], 0)
            portal.supplyorders.reindexObject()

        # Analysis Services
        # Add Analysis Services View permission to Clients
        # (allow Clients to add attachments to Analysis Services from an AR)
        mp = portal.bika_setup.bika_analysisservices.manage_permission
        # We set explicit permissions to access methods to be persistent with the assigned workflow
        mp(permissions.View, ['Authenticated', 'Anonymous'], 0)
        mp(permissions.ListFolderContents, ['Authenticated'], 0)
        mp(permissions.AccessContentsInformation, ['Authenticated', 'Anonymous'], 0)
        portal.bika_setup.bika_analysisservices.reindexObject()
        # /Analysis Services

        # Add Attachment Types View permission to Clients
        # (allow Clients to add attachments to Analysis Services from an AR)
        mp = portal.bika_setup.bika_attachmenttypes.manage_permission
        mp('Access contents information', ['Authenticated', 'Analyst', 'Client'], 1)
        mp(permissions.View, ['Authenticated', 'Analyst', 'Client'], 1)
        portal.bika_setup.bika_attachmenttypes.reindexObject()

        # /arimports folder permissions
        if portal.hasObject("arimports"):
            mp = portal.arimports.manage_permission
            mp(ManageARImport, ['Manager', ], 1)
            mp(permissions.ListFolderContents, ['Manager', 'Member', ], 1)
            mp(permissions.AddPortalContent, ['Manager', ], 0)
            mp(permissions.DeleteObjects, ['Manager'], 0)
            mp(permissions.View, ['Manager', 'Member'], 0)
            portal.arimports.reindexObject()

    def setupVersioning(self, portal):
        portal_repository = getToolByName(portal, 'portal_repository')
        versionable_types = list(portal_repository.getVersionableContentTypes())

        for type_id in VERSIONABLE_TYPES:
            if type_id not in versionable_types:
                versionable_types.append(type_id)
                # Add default versioning policies to the versioned type
                for policy_id in DEFAULT_POLICIES:
                    portal_repository.addPolicyForContentType(type_id, policy_id)
        portal_repository.setVersionableContentTypes(versionable_types)

    def setupCatalogs(self, portal):
        # an item should belong to only one catalog.
        # that way looking it up means first looking up *the* catalog
        # in which it is indexed, as well as making it cheaper to index.

        def addIndex(cat, *args):
            try:
                cat.addIndex(*args)
            except:
                pass

        def addColumn(cat, col):
            try:
                cat.addColumn(col)
            except:
                pass

        # create lexicon
        wordSplitter = Empty()
        wordSplitter.group = 'Word Splitter'
        wordSplitter.name = 'Unicode Whitespace splitter'
        caseNormalizer = Empty()
        caseNormalizer.group = 'Case Normalizer'
        caseNormalizer.name = 'Unicode Case Normalizer'
        stopWords = Empty()
        stopWords.group = 'Stop Words'
        stopWords.name = 'Remove listed and single char words'
        elem = [wordSplitter, caseNormalizer, stopWords]
        zc_extras = Empty()
        zc_extras.index_type = 'Okapi BM25 Rank'
        zc_extras.lexicon_id = 'Lexicon'

        # bika_analysis_catalog

        bac = getToolByName(portal, 'bika_analysis_catalog', None)
        if bac is None:
            logger.warning('Could not find the bika_analysis_catalog tool.')
            return

        try:
            bac.manage_addProduct['ZCTextIndex'].manage_addLexicon('Lexicon', 'Lexicon', elem)
        except:
            logger.warning('Could not add ZCTextIndex to bika_analysis_catalog')
            pass

        at = getToolByName(portal, 'archetype_tool')
        at.setCatalogsByType('Analysis', ['bika_analysis_catalog'])
        at.setCatalogsByType('ReferenceAnalysis', ['bika_analysis_catalog'])
        at.setCatalogsByType('DuplicateAnalysis', ['bika_analysis_catalog'])

        addIndex(bac, 'path', 'ExtendedPathIndex', ('getPhysicalPath'))
        addIndex(bac, 'allowedRolesAndUsers', 'KeywordIndex')
        addIndex(bac, 'UID', 'FieldIndex')
        addIndex(bac, 'Title', 'FieldIndex')
        addIndex(bac, 'Description', 'ZCTextIndex', zc_extras)
        addIndex(bac, 'id', 'FieldIndex')
        addIndex(bac, 'Type', 'FieldIndex')
        addIndex(bac, 'portal_type', 'FieldIndex')
        addIndex(bac, 'created', 'DateIndex')
        addIndex(bac, 'Creator', 'FieldIndex')
        addIndex(bac, 'title', 'FieldIndex', 'Title')
        addIndex(bac, 'sortable_title', 'FieldIndex')
        addIndex(bac, 'description', 'FieldIndex', 'Description')
        addIndex(bac, 'review_state', 'FieldIndex')
        addIndex(bac, 'worksheetanalysis_review_state', 'FieldIndex')
        addIndex(bac, 'cancellation_state', 'FieldIndex')
        addIndex(bac, 'getDepartmentUID', 'KeywordIndex')

        addIndex(bac, 'getDueDate', 'DateIndex')
        addIndex(bac, 'getDateSampled', 'DateIndex')
        addIndex(bac, 'getDateReceived', 'DateIndex')
        addIndex(bac, 'getResultCaptureDate', 'DateIndex')
        addIndex(bac, 'getDateAnalysisPublished', 'DateIndex')

        addIndex(bac, 'getClientUID', 'FieldIndex')
        addIndex(bac, 'getAnalyst', 'FieldIndex')
        addIndex(bac, 'getClientTitle', 'FieldIndex')
        addIndex(bac, 'getRequestID', 'FieldIndex')
        addIndex(bac, 'getClientOrderNumber', 'FieldIndex')
        addIndex(bac, 'getKeyword', 'FieldIndex')
        addIndex(bac, 'getServiceTitle', 'FieldIndex')
        addIndex(bac, 'getServiceUID', 'FieldIndex')
        addIndex(bac, 'getCategoryUID', 'FieldIndex')
        addIndex(bac, 'getCategoryTitle', 'FieldIndex')
        addIndex(bac, 'getPointOfCapture', 'FieldIndex')
        addIndex(bac, 'getDateReceived', 'DateIndex')
        addIndex(bac, 'getResultCaptureDate', 'DateIndex')
        addIndex(bac, 'getSampleTypeUID', 'FieldIndex')
        addIndex(bac, 'getSamplePointUID', 'FieldIndex')
        addIndex(bac, 'getRawSamplePoints', 'KeywordsIndex')
        addIndex(bac, 'getRawSampleTypes', 'KeywordIndex')
        addIndex(bac, 'getRetested', 'FieldIndex')
        addIndex(bac, 'getReferenceAnalysesGroupID', 'FieldIndex')

        addColumn(bac, 'path')
        addColumn(bac, 'UID')
        addColumn(bac, 'id')
        addColumn(bac, 'Type')
        addColumn(bac, 'portal_type')
        addColumn(bac, 'getObjPositionInParent')
        addColumn(bac, 'Title')
        addColumn(bac, 'Description')
        addColumn(bac, 'title')
        addColumn(bac, 'sortable_title')
        addColumn(bac, 'description')
        addColumn(bac, 'review_state')
        addColumn(bac, 'cancellation_state')
        addColumn(bac, 'getRequestID')
        addColumn(bac, 'getReferenceAnalysesGroupID')
        addColumn(bac, 'getResultCaptureDate')
        addColumn(bac, 'Priority')

        # bika_catalog

        bc = getToolByName(portal, 'bika_catalog', None)
        if bc is None:
            logger.warning('Could not find the bika_catalog tool.')
            return

        try:
            bc.manage_addProduct['ZCTextIndex'].manage_addLexicon('Lexicon', 'Lexicon', elem)
        except:
            logger.warning('Could not add ZCTextIndex to bika_catalog')
            pass

        at = getToolByName(portal, 'archetype_tool')
        at.setCatalogsByType('Batch', ['bika_catalog', 'portal_catalog'])
        at.setCatalogsByType('AnalysisRequest', ['bika_catalog', 'portal_catalog'])
        at.setCatalogsByType('Sample', ['bika_catalog', 'portal_catalog'])
        at.setCatalogsByType('SamplePartition', ['bika_catalog', 'portal_catalog'])
        at.setCatalogsByType('ReferenceSample', ['bika_catalog', 'portal_catalog'])
        at.setCatalogsByType('Report', ['bika_catalog', ])
        at.setCatalogsByType('Worksheet', ['bika_catalog', 'portal_catalog'])

        addIndex(bc, 'path', 'ExtendedPathIndex', ('getPhysicalPath'))
        addIndex(bc, 'allowedRolesAndUsers', 'KeywordIndex')
        addIndex(bc, 'UID', 'FieldIndex')
        addIndex(bc, 'SearchableText', 'ZCTextIndex', zc_extras)
        addIndex(bc, 'Title', 'ZCTextIndex', zc_extras)
        addIndex(bc, 'Description', 'ZCTextIndex', zc_extras)
        addIndex(bc, 'id', 'FieldIndex')
        addIndex(bc, 'getId', 'FieldIndex')
        addIndex(bc, 'Type', 'FieldIndex')
        addIndex(bc, 'portal_type', 'FieldIndex')
        addIndex(bc, 'created', 'DateIndex')
        addIndex(bc, 'Creator', 'FieldIndex')
        addIndex(bc, 'getObjPositionInParent', 'GopipIndex')
        addIndex(bc, 'title', 'FieldIndex', 'Title')
        addIndex(bc, 'sortable_title', 'FieldIndex')
        addIndex(bc, 'description', 'FieldIndex', 'Description')
        addIndex(bc, 'review_state', 'FieldIndex')
        addIndex(bc, 'inactive_state', 'FieldIndex')
        addIndex(bc, 'worksheetanalysis_review_state', 'FieldIndex')
        addIndex(bc, 'cancellation_state', 'FieldIndex')
        addIndex(bc, 'Identifiers', 'KeywordIndex')

        addIndex(bc, 'getDepartmentUIDs', 'KeywordIndex')
        addIndex(bc, 'getAnalysisCategory', 'KeywordIndex')
        addIndex(bc, 'getAnalysisService', 'KeywordIndex')
        addIndex(bc, 'getAnalyst', 'FieldIndex')
        addIndex(bc, 'getAnalysts', 'KeywordIndex')
        addIndex(bc, 'BatchDate', 'DateIndex')
        addIndex(bc, 'getClientOrderNumber', 'FieldIndex')
        addIndex(bc, 'getClientReference', 'FieldIndex')
        addIndex(bc, 'getClientSampleID', 'FieldIndex')
        addIndex(bc, 'getClientTitle', 'FieldIndex')
        addIndex(bc, 'getClientUID', 'FieldIndex')
        addIndex(bc, 'getContactTitle', 'FieldIndex')
        addIndex(bc, 'getDateDisposed', 'DateIndex')
        addIndex(bc, 'getDateExpired', 'DateIndex')
        addIndex(bc, 'getDateOpened', 'DateIndex')
        addIndex(bc, 'getDatePublished', 'DateIndex')
        addIndex(bc, 'getDateReceived', 'DateIndex')
        addIndex(bc, 'getDateSampled', 'DateIndex')
        addIndex(bc, 'getDisposalDate', 'DateIndex')
        addIndex(bc, 'getDueDate', 'DateIndex')
        addIndex(bc, 'getExpiryDate', 'DateIndex')
        addIndex(bc, 'getInvoiced', 'FieldIndex')
        addIndex(bc, 'getPreserver', 'FieldIndex')
        addIndex(bc, 'getProfilesTitle', 'FieldIndex')
        addIndex(bc, 'getReferenceDefinitionUID', 'FieldIndex')
        addIndex(bc, 'getRequestID', 'FieldIndex')
        addIndex(bc, 'getSampleID', 'FieldIndex')
        addIndex(bc, 'getSamplePointTitle', 'FieldIndex')
        addIndex(bc, 'getSamplePointUID', 'FieldIndex')
        addIndex(bc, 'getSampler', 'FieldIndex')
        addIndex(bc, 'getScheduledSamplingSampler', 'FieldIndex')
        addIndex(bc, 'getSampleTypeTitle', 'FieldIndex')
        addIndex(bc, 'getSampleTypeUID', 'FieldIndex')
        addIndex(bc, 'getSampleUID', 'FieldIndex')
        addIndex(bc, 'getSamplingDate', 'DateIndex')
        addIndex(bc, 'getServiceTitle', 'FieldIndex')
        addIndex(bc, 'getWorksheetTemplateTitle', 'FieldIndex')
        addIndex(bc, 'Priority', 'FieldIndex')
        addIndex(bc, 'BatchUID', 'FieldIndex')
        addColumn(bc, 'path')
        addColumn(bc, 'UID')
        addColumn(bc, 'id')
        addColumn(bc, 'Type')
        addColumn(bc, 'portal_type')
        addColumn(bc, 'creator')
        addColumn(bc, 'Created')
        addColumn(bc, 'Title')
        addColumn(bc, 'Description')
        addColumn(bc, 'sortable_title')
        addColumn(bc, 'review_state')
        addColumn(bc, 'inactive_state')
        addColumn(bc, 'cancellation_state')
        addColumn(bc, 'getAnalysts')
        addColumn(bc, 'getSampleID')
        addColumn(bc, 'getRequestID')
        addColumn(bc, 'getClientOrderNumber')
        addColumn(bc, 'getClientReference')
        addColumn(bc, 'getClientSampleID')
        addColumn(bc, 'getContactTitle')
        addColumn(bc, 'getClientTitle')
        addColumn(bc, 'getProfilesTitle')
        addColumn(bc, 'getSamplePointTitle')
        addColumn(bc, 'getSampleTypeTitle')
        addColumn(bc, 'getAnalysisCategory')
        addColumn(bc, 'getAnalysisService')
        addColumn(bc, 'getDatePublished')
        addColumn(bc, 'getDateReceived')
        addColumn(bc, 'getDateSampled')
        addColumn(bc, 'review_state')

        # bika_setup_catalog

        bsc = getToolByName(portal, 'bika_setup_catalog', None)
        if bsc is None:
            logger.warning('Could not find the setup catalog tool.')
            return

        try:
            bsc.manage_addProduct['ZCTextIndex'].manage_addLexicon('Lexicon', 'Lexicon', elem)
        except:
            logger.warning('Could not add ZCTextIndex to bika_setup_catalog')
            pass

        at = getToolByName(portal, 'archetype_tool')
        at.setCatalogsByType('Department', ['bika_setup_catalog', "portal_catalog", ])
        at.setCatalogsByType('Container', ['bika_setup_catalog', ])
        at.setCatalogsByType('ContainerType', ['bika_setup_catalog', ])
        at.setCatalogsByType('AnalysisCategory', ['bika_setup_catalog', ])
        at.setCatalogsByType('AnalysisService', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('AnalysisSpec', ['bika_setup_catalog', ])
        at.setCatalogsByType('SampleCondition', ['bika_setup_catalog'])
        at.setCatalogsByType('SampleMatrix', ['bika_setup_catalog', ])
        at.setCatalogsByType('SampleType', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('SamplePoint', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('StorageLocation', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('SamplingDeviation', ['bika_setup_catalog', ])
        at.setCatalogsByType('IdentifierType', ['bika_setup_catalog', ])
        at.setCatalogsByType('Instrument', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('InstrumentType', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('InstrumentLocation', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('Method', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('Multifile', ['bika_setup_catalog'])
        at.setCatalogsByType('AttachmentType', ['bika_setup_catalog', ])
        at.setCatalogsByType('Calculation', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('AnalysisProfile', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('ARTemplate', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('LabProduct', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('LabContact', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('Manufacturer', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('Preservation', ['bika_setup_catalog', ])
        at.setCatalogsByType('ReferenceDefinition', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('SRTemplate', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('SubGroup', ['bika_setup_catalog', ])
        at.setCatalogsByType('Supplier', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('Unit', ['bika_setup_catalog', ])
        at.setCatalogsByType('WorksheetTemplate', ['bika_setup_catalog', 'portal_catalog'])
        at.setCatalogsByType('BatchLabel', ['bika_setup_catalog', ])
        at.setCatalogsByType('ARPriority', ['bika_setup_catalog', ])

        addIndex(bsc, 'path', 'ExtendedPathIndex', ('getPhysicalPath'))
        addIndex(bsc, 'allowedRolesAndUsers', 'KeywordIndex')
        addIndex(bsc, 'UID', 'FieldIndex')
        addIndex(bsc, 'SearchableText', 'ZCTextIndex', zc_extras)
        addIndex(bsc, 'Title', 'ZCTextIndex', zc_extras)
        addIndex(bsc, 'Description', 'ZCTextIndex', zc_extras)
        addIndex(bsc, 'id', 'FieldIndex')
        addIndex(bsc, 'getId', 'FieldIndex')
        addIndex(bsc, 'Type', 'FieldIndex')
        addIndex(bsc, 'portal_type', 'FieldIndex')
        addIndex(bsc, 'created', 'DateIndex')
        addIndex(bsc, 'Creator', 'FieldIndex')
        addIndex(bsc, 'getObjPositionInParent', 'GopipIndex')
        addIndex(bc, 'Identifiers', 'KeywordIndex')

        addIndex(bsc, 'title', 'FieldIndex', 'Title')
        addIndex(bsc, 'sortable_title', 'FieldIndex')
        addIndex(bsc, 'description', 'FieldIndex', 'Description')

        addIndex(bsc, 'review_state', 'FieldIndex')
        addIndex(bsc, 'inactive_state', 'FieldIndex')
        addIndex(bsc, 'cancellation_state', 'FieldIndex')

        addIndex(bsc, 'getAccredited', 'FieldIndex')
        addIndex(bsc, 'getAnalyst', 'FieldIndex')
        addIndex(bsc, 'getInstrumentType', 'FieldIndex')
        addIndex(bsc, 'getInstrumentTypeName', 'FieldIndex')
        addIndex(bsc, 'getInstrumentLocationName', 'FieldIndex')
        addIndex(bsc, 'getBlank', 'FieldIndex')
        addIndex(bsc, 'getCalculationTitle', 'FieldIndex')
        addIndex(bsc, 'getCalculationUID', 'FieldIndex')
        addIndex(bsc, 'getCalibrationExpiryDate', 'FieldIndex')
        addIndex(bsc, 'getCategoryTitle', 'FieldIndex')
        addIndex(bsc, 'getCategoryUID', 'FieldIndex')
        addIndex(bsc, 'getClientUID', 'FieldIndex')
        addIndex(bsc, 'getDepartmentTitle', 'FieldIndex')
        addIndex(bsc, 'getDuplicateVariation', 'FieldIndex')
        addIndex(bsc, 'getFormula', 'FieldIndex')
        addIndex(bsc, 'getFullname', 'FieldIndex')
        addIndex(bsc, 'getHazardous', 'FieldIndex')
        addIndex(bsc, 'getInstrumentTitle', 'FieldIndex')
        addIndex(bsc, 'getKeyword', 'FieldIndex')
        addIndex(bsc, 'getManagerName', 'FieldIndex')
        addIndex(bsc, 'getManagerPhone', 'FieldIndex')
        addIndex(bsc, 'getManagerEmail', 'FieldIndex')
        addIndex(bsc, 'getMaxTimeAllowed', 'FieldIndex')
        addIndex(bsc, 'getModel', 'FieldIndex')
        addIndex(bsc, 'getName', 'FieldIndex')
        addIndex(bsc, 'getPointOfCapture', 'FieldIndex')
        addIndex(bsc, 'getPrice', 'FieldIndex')
        addIndex(bsc, 'getSamplePointTitle', 'KeywordIndex')
        addIndex(bsc, 'getSamplePointUID', 'FieldIndex')
        addIndex(bsc, 'getSampleTypeTitle', 'KeywordIndex')
        addIndex(bsc, 'getSampleTypeUID', 'FieldIndex')
        addIndex(bsc, 'getServiceTitle', 'FieldIndex')
        addIndex(bsc, 'getServiceUID', 'FieldIndex')
        addIndex(bsc, 'getTotalPrice', 'FieldIndex')
        addIndex(bsc, 'getUnit', 'FieldIndex')
        addIndex(bsc, 'getVATAmount', 'FieldIndex')
        addIndex(bsc, 'getVolume', 'FieldIndex')
        addIndex(bsc, 'sortKey', 'FieldIndex')
        addIndex(bsc, 'getMethodID', 'FieldIndex')
        addIndex(bsc, 'getDocumentID', 'FieldIndex')
        addIndex(bsc, 'getMethodUIDs', 'KeywordIndex')

        addColumn(bsc, 'path')
        addColumn(bsc, 'UID')
        addColumn(bsc, 'id')
        addColumn(bsc, 'getId')
        addColumn(bsc, 'Type')
        addColumn(bsc, 'portal_type')
        addColumn(bsc, 'getObjPositionInParent')

        addColumn(bsc, 'Title')
        addColumn(bsc, 'Description')
        addColumn(bsc, 'title')
        addColumn(bsc, 'sortable_title')
        addColumn(bsc, 'description')

        addColumn(bsc, 'review_state')
        addColumn(bsc, 'inactive_state')
        addColumn(bsc, 'cancellation_state')

        addColumn(bsc, 'getAccredited')
        addColumn(bsc, 'getInstrumentType')
        addColumn(bsc, 'getInstrumentTypeName')
        addColumn(bsc, 'getInstrumentLocationName')
        addColumn(bsc, 'getBlank')
        addColumn(bsc, 'getCalculationTitle')
        addColumn(bsc, 'getCalculationUID')
        addColumn(bsc, 'getCalibrationExpiryDate')
        addColumn(bsc, 'getCategoryTitle')
        addColumn(bsc, 'getCategoryUID')
        addColumn(bsc, 'getClientUID')
        addColumn(bsc, 'getDepartmentTitle')
        addColumn(bsc, 'getDuplicateVariation')
        addColumn(bsc, 'getFormula')
        addColumn(bsc, 'getFullname')
        addColumn(bsc, 'getHazardous')
        addColumn(bsc, 'getInstrumentTitle')
        addColumn(bsc, 'getKeyword')
        addColumn(bsc, 'getManagerName')
        addColumn(bsc, 'getManagerPhone')
        addColumn(bsc, 'getManagerEmail')
        addColumn(bsc, 'getMaxTimeAllowed')
        addColumn(bsc, 'getModel')
        addColumn(bsc, 'getName')
        addColumn(bsc, 'getPointOfCapture')
        addColumn(bsc, 'getPrice')
        addColumn(bsc, 'getSamplePointTitle')
        addColumn(bsc, 'getSamplePointUID')
        addColumn(bsc, 'getSampleTypeTitle')
        addColumn(bsc, 'getSampleTypeUID')
        addColumn(bsc, 'getServiceTitle')
        addColumn(bsc, 'getServiceUID')
        addColumn(bsc, 'getTotalPrice')
        addColumn(bsc, 'getUnit')
        addColumn(bsc, 'getVATAmount')
        addColumn(bsc, 'getVolume')

    def setupTopLevelFolders(self, context):
        workflow = getToolByName(context, "portal_workflow")
        obj_id = 'arimports'
        if obj_id in context.objectIds():
            obj = context._getOb(obj_id)
            try:
                workflow.doActionFor(obj, "hide")
            except:
                pass
            obj.setLayout('@@arimports')
            alsoProvides(obj, IARImportFolder)
            alsoProvides(obj, IHaveNoBreadCrumbs)


def create_CAS_IdentifierType(portal):
    """LIMS-1391 The CAS Nr IdentifierType is normally created by
    setuphandlers during site initialisation.
    """
    bsc = getToolByName(portal, 'bika_catalog', None)
    idtypes = bsc(portal_type='IdentifierType', title='CAS Nr')
    if not idtypes:
        folder = portal.bika_setup.bika_identifiertypes
        idtype = _createObjectByType('IdentifierType', folder, tmpID())
        idtype.processForm()
        idtype.edit(title='CAS Nr',
                    description='Chemical Abstracts Registry number',
                    portal_types=['Analysis Service'])
