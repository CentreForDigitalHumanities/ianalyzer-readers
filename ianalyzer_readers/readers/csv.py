'''
This module defines the CSV reader.

Extraction is based on python's `csv` library.
'''

from .. import extract
from typing import List, Dict, Iterable
from .core import Reader, Document
import csv
import sys
from contextlib import contextmanager

import logging

logger = logging.getLogger()


class CSVReader(Reader):
    '''
    A base class for Readers of .csv (comma separated value) files.

    The CSVReader is designed for .csv or .tsv files that have a header row, and where
    each file may list multiple documents.

    The data should be structured in one of the following ways:
    
    - one document per row (this is the default)
    - each document spans a number of consecutive rows. In this case, there should be a
        column that indicates the identity of the document.

    In addition to generic extractor classes, this reader supports the `CSV` extractor.
    '''

    field_entry = None
    '''
    If applicable, the name of the column that identifies entries. Subsequent rows with the
    same value for this column are treated as a single document. If left blank, each row
    is treated as a document.
    '''

    required_field = None
    '''
    Specifies the name of a required column in the CSV data, for example the main content.
    Rows with an empty value for `required_field` will be skipped.
    '''

    delimiter = ','
    '''
    The column delimiter used in the CSV data
    '''

    skip_lines = 0
    '''
    Number of lines in the file to skip before reading the header. Can be used when files
    use a fixed "preamble", e.g. to describe metadata or provenance.
    '''


    def validate(self):
        # make sure the field size is as big as the system permits
        csv.field_size_limit(sys.maxsize)
        self._reject_extractors(extract.XML)


    @contextmanager
    def data_from_file(self, path: str):
        with open(path, 'r') as f:
            logger.info('Reading CSV file {}...'.format(path))

            # skip first n lines
            for _ in range(self.skip_lines):
                next(f)

            reader = csv.DictReader(f, delimiter=self.delimiter)
            yield reader


    def iterate_data(self, data: csv.DictReader, metadata) -> Iterable[Document]:
        document_id = None
        rows = []
        index = 0
        for row in data:
            is_new_document = True

            if self.required_field and not row.get(self.required_field):  # skip row if required_field is empty
                continue

            if self.field_entry:
                identifier = row[self.field_entry]
                if identifier == document_id:
                    is_new_document = False
                else:
                    document_id = identifier

            if is_new_document and rows:
                yield {'rows': rows, 'metadata': metadata, 'index': index}
                rows = [row]
                index += 1
            else:
                rows.append(row)

        yield {'rows': rows, 'index': index, 'metadata': metadata}
