'''
This module defines the JSONReader.

It can parse documents nested in one file, for which it uses the pandas library,
or multiple files with one document each, which use the generic Python json parser.
'''

import json
from os.path import isfile
from typing import Iterable, List, Optional, Union

from pandas import json_normalize
from requests import Response

from .core import Reader, Document, Source
import ianalyzer_readers.extract as extract

class JSONReader(Reader):
    '''
    A base class for Readers of JSON encoded data.

    The reader can either be used on a collection of JSON files (`single_document=True`), in which each file represents a document,
    or for a JSON file containing lists of documents.

    If the attributes `record_path` and `meta` are set, they are used as arguments to [pandas.json_normalize](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.json_normalize.html) to unnest the JSON data

    Attributes:
        single_document: indicates whether the data is organized such that a file represents a single document
        record_path: a keyword or list of keywords by which a list of documents can be extracted from a large JSON file; irrelevant if `single_document = True`
        meta: a list of keywords, or list of lists of keywords, by which metadata for each document can be located; irrelevant if `single_document = True`
    """

    Examples:
        ##### Multiple documents in one file:
        ```python
        example_data = {
            'path': {
                'sketch': 'Hungarian Phrasebook',
                'episode': 25,
                'to': {
                    'records':
                        [
                            {'speech': 'I will not buy this record. It is scratched.', 'character': 'tourist'},
                            {'speech': "No sir. This is a tobacconist's.", 'character': 'tobacconist'}
                        ]
                }
            }
        }

        MyJSONReader(JSONReader):
            record_path = ['path', 'to', 'records']
            meta = [['path', 'sketch'], ['path', 'episode']]

            speech = Field('speech', JSON('speech'))
            character = Field('character', JSON('character'))
            sketch = Field('sketch', JSON('path.sketch')) # field name results from paths in `meta` array, separated by a dot
            episode = Field('episode', JSON('path.episode'))
        ```

        ##### Single document per file:
        ```python
        example_data = {
            'sketch': 'Hungarian Phrasebook',
            'episode': 25,
            'scene': {
                'character': 'tourist',
                'speech': 'I will not buy this record. It is scratched.'
            }
        }

        MyJSONReader(JSONReader):
            single_document = True

            speech = Field('speech', JSON('scene', 'speech'))
            character = Field('character', JSON('scene', 'character))
            sketch = Field('sketch', JSON('sketch'))
            episode = Field('episode', JSON('episode))
        ```

    '''

    single_document: bool = False
    '''
    set to `True` if the data is structured such that one document is encoded in one .json file
    in that case, the reader assumes that there are no lists in such a file
    '''

    record_path: Optional[List[str]] = None
    '''
    a keyword or list of keywords by which a list of documents can be extracted from a large JSON file.
    Only relevant if `single_document=False`.
    '''

    meta: Optional[List[Union[str, List[str]]]] = None
    '''
    a list of keywords, or list of lists of keywords, by which metadata for each document can be located,
    if it is in a different path than `record_path`. Only relevant if `single_document=False`.
    '''

    def source2dicts(self, source: Source, *nargs, **kwargs) -> Iterable[Document]:
        """
        Given a Python dictionary, returns an iterable of extracted documents.

        Parameters:
            source: the input data

        Returns:
            list of documents
        """
        if isinstance(source, tuple):
            metadata = source[1]
            json_data = self._get_json_data(source[0])
        else:
            metadata = None
            json_data = self._get_json_data(source)

        if not self.single_document:
            documents = json_normalize(
                json_data, record_path=self.record_path, meta=self.meta
            ).to_dict('records')
        else:
            documents = [json_data]

        self._reject_extractors(extract.XML, extract.CSV, extract.RDF)

        for doc in documents:
            field_dict = {
                field.name: field.extractor.apply(
                    doc, metadata=metadata, *nargs, **kwargs
                )
                for field in self.fields
            }

            yield field_dict

    def _get_json_data(self, source: Source) -> dict:
        if isfile(source):
            with open(source, "r") as f:
                return json.load(f)
        elif isinstance(source, Response):
            return source.json()
        elif isinstance(source, bytes):
            return json.loads(source)
        else:
            raise Exception("Unexpected source type for JSON Reader")
