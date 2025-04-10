from ianalyzer_readers.readers.csv import CSVReader
from ianalyzer_readers.readers.core import Field
from ianalyzer_readers.extract import CSV, Metadata
import os

def format_name(name):
    if name:
        return name.title()

class ShakespeareReader(CSVReader):
    data_directory = os.path.dirname(__file__) + '/data'

    field_entry = 'character'

    play = Field(
        name='play',
        extractor=Metadata('title')
    )
    act = Field(
        name='act',
        extractor=CSV('act')
    )
    scene = Field(
        name='scene',
        extractor=CSV('scene')
    )
    character = Field(
        name='character',
        extractor=CSV('character', transform=format_name)
    )
    lines = Field(
        name='lines',
        extractor=CSV('line', multiple=True, transform='\n'.join)
    )
    fields = [play, act, scene, character, lines]

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            name, ext = os.path.splitext(filename)
            yield path, {'title': name}

def test_csv_example_reader():
    reader = ShakespeareReader()
    docs = list(reader.documents())
    assert len(docs) == 26
    plays = {'Hamlet', 'Macbeth', 'Much Ado About Nothing'}
    assert set(doc['play'] for doc in docs) == plays

    hamlet_lines = list(filter(lambda doc: doc['play'] == 'Hamlet', docs))
    assert hamlet_lines[1] == {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Hamlet',
        'lines': 'Whither wilt thou lead me? Speak, I\'ll go no further.'
    }
    assert hamlet_lines[4] == {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Ghost',
        'lines': 'My hour is almost come,\n'
            'When I to sulph\'rous and tormenting flames\n'
            'Must render up myself.'
    }

def test_skip_field():
    reader = ShakespeareReader()
    reader.fields[0].skip = True

    docs = reader.documents()
    for doc in docs:
        assert 'play' not in doc
