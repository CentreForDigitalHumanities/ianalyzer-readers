'''
This module tests the code in the "custom reader" example in the documentation.
'''

from typing import Iterable, Dict, Optional
import os

from ianalyzer_readers.extract import Extractor
from ianalyzer_readers.readers.core import Reader, Document, Field
from ianalyzer_readers.extract import Order, Constant


class BibliographyExtractor(Extractor):
    def __init__(self, key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.key = key

    def _apply(self, mapping: Optional[Dict] = None, **kwargs):
        return mapping.get(self.key, None)


class BibliographyReader(Reader):
    data_directory = os.path.dirname(__file__)

    def sources(self, **kwargs):
        yield self.data_directory + '/library.txt'

    def data_from_file(self, path: str) -> str:
        f = open(path, 'r')
        content = f.read()
        f.close()
        return content

    def iterate_data(self, data: str, metadata: Dict) -> Iterable[Document]:
        sections = data.split('\n\n')
        for section in sections:
            mapping = self._mapping_from_section(section)
            yield {'mapping': mapping}

    def _mapping_from_section(self, section: str):
        lines = section.split('\n')
        keys_values = (line.split(': ') for line in lines if len(line))
        return { key: value for key, value in keys_values }

    fields = [
        Field(
            name='title',
            extractor=BibliographyExtractor('Title'),
        ),
        Field(
            name='author',
            extractor=BibliographyExtractor('Author'),
        ),
        Field(
            name='year',
            extractor=BibliographyExtractor('Year', transform=int),
        ),
        Field(
            name='index',
            extractor=Order(),
        ),
        Field(
            name='file',
            extractor=Constant('library.txt'),
        ),
    ]


expected_docs = [
    {
        'title': 'Pride and Prejudice',
        'author': 'Jane Austen',
        'year': 1813,
        'index': 0,
        'file': 'library.txt',
    },
        {
        'title': 'Frankenstein, or, the Modern Prometheus',
        'author': 'Mary Shelley',
        'year': 1818,
        'index': 1,
        'file': 'library.txt',
    },
        {
        'title': 'Moby Dick',
        'author': 'Herman Melville',
        'year': 1851,
        'index': 2,
        'file': 'library.txt',
    },
        {
        'title': 'Alice in Wonderland',
        'author': 'Lewis Carroll',
        'year': 1865,
        'index': 3,
        'file': 'library.txt',
    },
]

def test_custom_example():
    reader = BibliographyReader()
    docs = list(reader.documents())

    assert docs == expected_docs
