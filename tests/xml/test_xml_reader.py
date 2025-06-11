import os

import requests

from ianalyzer_readers.readers.xml import XMLReader
from ianalyzer_readers.readers.core import Field
from ianalyzer_readers.extract import XML
from ianalyzer_readers.xml_tag import Tag, CurrentTag

class HamletXMLReader(XMLReader):
    """
    Example XML reader for testing
    """

    data_directory = os.path.join(os.path.dirname(__file__), 'data')

    tag_toplevel = Tag('document')
    tag_entry = Tag('lines')

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            full_path = os.path.join(self.data_directory, filename)
            yield full_path, {
                'filename': filename
            }

    title = Field(
        'title',
        XML(
            Tag('title'),
            toplevel=True
        )
    )
    character = Field(
        'character',
        XML(CurrentTag(), attribute='character')
    )
    lines = Field(
        'lines',
        XML(
            Tag('l'),
            multiple=True,
            transform='\n'.join
        ),
    )

    fields = [title, character, lines]

url_list = ['mock_path']


class HamletXMLResponseReader(HamletXMLReader):
    def sources(self, **kwargs):
        for document_url in url_list:
            response = requests.get(document_url)
            yield response


target_documents = [
    {
        'title': 'Hamlet',
        'character': 'HAMLET',
        'lines': "Whither wilt thou lead me? Speak, I\'ll go no further."
    },
    {
        'title': 'Hamlet',
        'character': 'GHOST',
        'lines': "Mark me."
    },
    {
        'title': 'Hamlet',
        'character': 'HAMLET',
        'lines': "I will."
    },
    {
        'title': 'Hamlet',
        'character': 'GHOST',
        'lines': 
            "My hour is almost come,\n"
            "When I to sulph\'rous and tormenting flames\n"
            "Must render up myself."
    },
    {
        'title': 'Hamlet',
        'character': 'HAMLET',
        'lines': "Alas, poor ghost!"
    },
    {
        'title': 'Hamlet',
        'character': 'GHOST',
        'lines': 
            "Pity me not, but lend thy serious hearing\n"
            "To what I shall unfold."
    },
    {
        'title': 'Hamlet',
        'character': 'HAMLET',
        'lines': "Speak, I am bound to hear."
    },
]


def test_xml_reader():
    reader = HamletXMLReader()
    docs = reader.documents()

    for doc, target in zip(docs, target_documents):
        assert doc == target


class MockResponse(requests.Response):

    @property
    def content(self):
        test_directory = os.path.dirname(__file__)
        filename = os.path.join(test_directory, 'data', 'hamlet.xml')
        with open(filename, "r") as f:
            return f.read()


def test_xml_response_reader(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda x: MockResponse())
    reader = HamletXMLResponseReader()
    docs = reader.documents()

    for doc, target in zip(docs, target_documents):
        assert doc == target
