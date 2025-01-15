'''
This module defines the CSV reader.

Extraction is based on python's `csv` library.
'''

from .. import extract
from typing import List, Dict, Iterable
from .core import Reader, Document, Source
import csv
import sys
from contextlib import contextmanager, AbstractContextManager

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

    def source2dicts(self, source: Source) -> Iterable[Document]:
        '''
        Given a CSV source file, returns an iterable of extracted documents.

        Parameters:
            source: the source file to extract. This can be a string with the path to
                the file, or a tuple with a path and a dictionary containing metadata.
        
        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.
        '''

        # make sure the field size is as big as the system permits
        csv.field_size_limit(sys.maxsize)
        self._reject_extractors(extract.XML)

        return super().source2dicts(source)

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
                yield self._document_from_rows(rows, metadata, index)
                rows = [row]
                index += 1
            else:
                rows.append(row)

        yield self._document_from_rows(rows, metadata, index)


    def _document_from_rows(self, rows: List[Dict], metadata: Dict, doc_index: int) -> Document:
        '''
        Extract a single document from a list of rows

        Parameters:
            rows: a list of row data. Since the CSVReader uses `csv.DictReader`, each row
                is expected to be a dictionary.
            metadata: a dictionary with file metadata. 
            doc_index: the index of this document in the source file. The first document
                extracted from a file should have index 0, the second should have index 1,
                and so forth.
        '''

        doc = {
            field.name: field.extractor.apply(
                # The extractor is put to work by simply throwing at it
                # any and all information it might need
                rows=rows, metadata = metadata, index=doc_index
            )
            for field in self.fields if not field.skip
        }

        return doc
