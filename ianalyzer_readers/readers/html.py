'''
This module defines the XML Reader.

The HTML reader is implemented as a subclas of the XML reader, and uses
BeautifulSoup to parse files.
'''

from .. import extract
from .core import Document
from .xml import XMLReader
import bs4
import logging
from typing import Iterable, Dict

logger = logging.getLogger()


class HTMLReader(XMLReader):
    '''
    An HTML reader extracts data from HTML sources.

    It is based on the XMLReader and supports the same options (`tag_toplevel` and
    `tag_entry`).

    In addition to generic extractor classes, this reader supports the `XML` extractor.
    '''

    def validate(self):
        self._reject_extractors(extract.CSV)


    def data_from_file(self, filename: str) -> bs4.BeautifulSoup:
        logger.info('Reading HTML file {} ...'.format(filename))
        with open(filename, 'rb') as f:
            data = f.read()
        # Parsing HTML
        soup = bs4.BeautifulSoup(data, 'html.parser')
        logger.info('Loaded {} into memory ...'.format(filename))
        return soup
    

    def iterate_data(self, data: bs4.BeautifulSoup, metadata: Dict) -> Iterable[Document]:
        # Extract fields from soup
        tag0 = self.tag_toplevel
        tag = self.tag_entry

        bowl = tag0.find_next_in_soup(data) if tag0 else data

        # if there is a entry level tag; with html this is not always the case
        if bowl and tag:
            for spoon in tag.find_in_soup(data):
                # yield
                yield {'soup_top': bowl, 'soup_entry': spoon}
        else:
            # yield all page content
            yield {'soup_entry': data}