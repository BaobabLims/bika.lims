# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from Products.CMFCore.utils import getToolByName
from bika.lims.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims.utils import formatDateQuery, formatDateParms, formatDuration
from plone.app.layout.globals.interfaces import IViewView
from zope.interface import implements
from Products.ATContentTypes.utils import DT2dt, dt2DT
import DateTime

class Report(BrowserView):
    implements(IViewView)
    template = ViewPageTemplateFile("templates/report_out.pt")

    def __init__(self, context, request, report=None):
        self.report = report
        BrowserView.__init__(self, context, request)

    def __call__(self):
        # get all the data into datalines

        bc = getToolByName(self.context, 'bika_analysis_catalog')
        rc = getToolByName(self.context, 'reference_catalog')
        self.report_content = {}
        parms = []
        headings = {}
        headings['header'] = _("Analysis turnaround times over time")
        headings['subheader'] = \
            _("The turnaround time of analyses plotted over time")

        query = {'portal_type': 'Analysis'}

        if 'ServiceUID' in self.request.form:
            service_uid = self.request.form['ServiceUID']
            query['getServiceUID'] = service_uid
            service = rc.lookupObject(service_uid)
            service_title = service.Title()
            parms.append(
                {'title': _('Analysis Service'),
                 'value': service_title,
                 'type': 'text'})

        if 'Analyst' in self.request.form:
            analyst = self.request.form['Analyst']
            query['getAnalyst'] = analyst
            analyst_title = self.user_fullname(analyst)
            parms.append(
                {'title': _('Analyst'),
                 'value': analyst_title,
                 'type': 'text'})

        if 'getInstrumentUID' in self.request.form:
            instrument_uid = self.request.form['getInstrumentUID']
            query['getInstrument'] = instrument_uid
            instrument = rc.lookupObject(instrument_uid)
            instrument_title = instrument.Title()
            parms.append(
                {'title': _('Instrument'),
                 'value': instrument_title,
                 'type': 'text'})

        if 'Period' in self.request.form:
            period = self.request.form['Period']
        else:
            period = 'Day'

        date_query = formatDateQuery(self.context, 'tats_DateReceived')
        if date_query:
            query['created'] = date_query
            received = formatDateParms(self.context, 'tats_DateReceived')
            parms.append(
                {'title': _('Received'),
                 'value': received,
                 'type': 'text'})

        query['review_state'] = 'published'

        # query all the analyses and increment the counts

        analysis_list = []
        analyses = bc(query)

        import datetime
        for a in analyses:
            analysis = a.getObject()
            analysis_list.append(
                {'analysis_id': analysis.id,
                 'duration': str(datetime.timedelta(seconds=analysis.getDuration())),
                 'overtime': self.formatOvertime(int(round((DT2dt(DateTime.DateTime(analysis.getDueDate())) - \
                       DT2dt(DateTime.DateTime(analysis.getDateAnalysisPublished()))) \
                      .total_seconds())))
                 }
            )

        # and now lets do the actual report lines
        formats = {'columns': 3,
                   'col_heads': [_('Analysis'),
                                 _('Duration'),
                                 _('Overtime'),
                                 ],
                   'class': ''}

        datalines = []

        for al in analysis_list:
            dataline = [{'value': al['analysis_id'],
                        'class': ''}]
            dataline.append({'value': al['duration'],
                             'class': 'number'})
            dataline.append({'value': al['overtime'],
                             'class': 'number'})
            datalines.append(dataline)


        # footer data
        footlines = []
        footline = []
        footline = [{'value': _('Total number of analysis'),
                     'class': 'total'}, ]

        footline.append({'value': len(analysis_list),
                         'colspan': 2,
                         'class': 'total number'})
        footlines.append(footline)


        self.report_content = {
            'headings': headings,
            'parms': parms,
            'formats': formats,
            'datalines': datalines,
            'footings': footlines}

        if self.request.get('output_format', '') == 'CSV':
            import csv
            import StringIO
            import datetime

            fieldnames = [
                'Analysis',
                'Duration',
                'Overtime',
            ]
            output = StringIO.StringIO()
            dw = csv.DictWriter(output, extrasaction='ignore',
                                fieldnames=fieldnames)
            dw.writerow(dict((fn, fn) for fn in fieldnames))
            for row in datalines:
                dw.writerow({
                    'Analysis': row[0]['value'],
                    'Duration': row[1]['value'],
                    'Overtime': row[2]['value'],
                })
            report_data = output.getvalue()
            output.close()
            date = datetime.datetime.now().strftime("%Y%m%d%H%M")
            setheader = self.request.RESPONSE.setHeader
            setheader('Content-Type', 'text/csv')
            setheader("Content-Disposition",
                      "attachment;filename=\"analysestats_%s.csv\"" % date)
            self.request.RESPONSE.write(report_data)
        else:
            return {'report_title': t(headings['header']),
                    'report_data': self.template()}

    def formatOvertime(self, overtime):
        import datetime

        if overtime > 0:
            return "-" + str(datetime.timedelta(seconds=overtime))
        else:
            return str(datetime.timedelta(seconds=abs(overtime)))

