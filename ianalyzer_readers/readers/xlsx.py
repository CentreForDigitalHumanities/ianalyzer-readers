import logging
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from typing import Iterable, Dict

from .core import Reader, Document, Source
from .. import extract

logger = logging.getLogger()


class XLSXReader(Reader):
    '''
    A base class for Readers that extract data from .xlsx spreadsheets

    The XLSXReader is quite rudimentary, and is designed to extract data from
    spreadsheets that are formatted like a CSV table, with a clear column layout. The
    sheet should have a header row.

    The data should be structured in one of the following ways:
    
    - one document per row (this is the default)
    - each document spans a number of consecutive rows. In this case, there should be a
        column that indicates the identity of the document.

    The XLSXReader will only look at the _first_ sheet in each file.

    In addition to generic extractor classes, this reader supports the `CSV` extractor.
    '''

    field_entry = None
    '''
    If applicable, the name of column that identifies entries. Subsequent rows with the
    same value for this column are treated as a single document. If left blank, each row
    is treated as a document.
    '''

    required_field = None
    '''
    Specifies the name of a required column, for example the main content. Rows with
    an empty value for `required_field` will be skipped.
    '''

    skip_lines = 0
    '''
    Number of lines in the sheet to skip before reading the header. Can be used when files
    use a fixed "preamble", e.g. to describe metadata or provenance.
    '''


    def validate(self):
        self._reject_extractors(extract.XML)


    def data_from_file(self, path) -> Workbook:
        logger.info('Reading XLSX file {}...'.format(path))
        return openpyxl.load_workbook(path)


    def iterate_data(self, data: Workbook, metadata: Dict):
        sheets = data.sheetnames
        sheet = data[sheets[0]]
        return self._sheet2dicts(sheet, metadata)


    def _sheet2dicts(self, sheet: Worksheet, metadata):
        '''
        Extract documents from a single worksheet
        '''
        
        data = (row for row in sheet.values)

        for _ in range(self.skip_lines):
            next(data)

        header = list(next(data))

        document_id = None
        rows = []

        for row in data:
            values = {
                col: value
                for col, value in zip(header, row)
            }

            # skip row if required_field is empty
            if self.required_field and not values.get(self.required_field):
                continue

            identifier = values.get(self.field_entry, None)
            is_new_document = identifier == None or identifier != document_id
            document_id = identifier

            if is_new_document and rows:
                yield {'rows': rows}
                rows = [values]
            else:
                rows.append(values)

        if rows:
            yield {'rows': rows}
