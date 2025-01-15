'''
This module defines the base classes on which all Readers are built.

It implements very little functionality of its own, but defines the interface
that Readers implement.

The module defines two classes, `Field` and `Reader`.
'''

from .. import extract
from typing import List, Iterable, Dict, Any, Union, Tuple, Optional, Generator
import logging
import csv
from os.path import isfile
from contextlib import AbstractContextManager

logging.basicConfig(level=logging.WARNING)
logging.getLogger('ianalyzer-readers').setLevel(logging.DEBUG)

Source = Union[str, Tuple[Union[str, bytes], Dict], bytes]
'''
Type definition for the source input to some Reader methods.

Sources are either:

- a string with the path to a filename
- a tuple containing a path to a filename, and a dictionary with metadata
- binary data with the file contents. This is not supported on all Reader subclasses.
'''

Document = Dict[str, Any]
'''
Type definition for documents, defined for convenience.

Each document extracted by a Reader is a dictionary, where the keys are names of
the Reader's `fields`, and the values are based on the extractor of each field.
'''

class Field(object):
    '''
    Fields are the elements of information that you wish to extract from each document.

    Parameters:
        name:  a short hand name (name), which will be used as its key in the document
        extractor: an Extractor object that defines how this field's data can be
            extracted from source documents.
        required: whether this field is required. The `Reader` class should skip the
            document is the value for this Field is `None`, though this is not supported
            for all readers.
        skip: if `True`, this field will not be included in the results.
    '''

    def __init__(self,
                 name: str,
                 extractor: extract.Extractor = extract.Constant(None),
                 required: bool = False,
                 skip: bool = False,
                 **kwargs
                 ):

        self.name = name
        self.extractor = extractor
        self.required = required
        self.skip = skip


class Reader(object):
    '''
    A base class for readers. Readers are objects that can generate documents
    from a source dataset.

    Subclasses of `Reader` can be created to read particular data formats or even
    particular datasets.
    
    The `Reader` class is not intended to be used directly. Some methods need to
    be implemented in child components, and will raise `NotImplementedError` if
    you try to use `Reader` directly.

    A fully implemented `Reader` subclass will define how to read a dataset by
    describing:

    - How to obtain its source files.
    - What fields each document contains.
    - How to extract said fields from the source files.
    '''

    @property
    def data_directory(self) -> str:
        '''
        Path to source data directory.

        Raises:
            NotImplementedError: This method needs to be implementd on child
                classes. It will raise an error by default.
        '''
        raise NotImplementedError('Reader missing data_directory')


    @property
    def fields(self) -> List[Field]:
        '''
        The list of fields that are extracted from documents.

        These should be instances of the `Field` class (or implement the same API).

        Raises:
            NotImplementedError: This method needs to be implementd on child
                classes. It will raise an error by default.
        '''
        raise NotImplementedError('Reader missing fields implementation')

    @property
    def fieldnames(self) -> List[str]:
        '''
        A list containing the name of each field of this Reader
        '''
        return [field.name for field in self.fields]

    def sources(self, **kwargs) -> Iterable[Source]:
        '''
        Obtain source files for the Reader.

        Returns:
            an iterable of tuples that each contain a string path, and a dictionary
                with associated metadata. The metadata can contain any data that was
                extracted before reading the file itself, such as data based on the
                file path, or on a metadata file.

        Raises:
            NotImplementedError: This method needs to be implementd on child
                classes. It will raise an error by default.
        '''
        raise NotImplementedError('Reader missing sources implementation')

    def source2dicts(self, source: Source) -> Iterable[Document]:
        '''
        Given a source file, returns an iterable of extracted documents.

        Parameters:
            source: the source file to extract. This can be a string with the path to
                the file, or a tuple with a path and a dictionary containing metadata.
                Some reader subclasses may also support bytes as input.
        
        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.

        Raises:
            NotImplementedError: This method needs to be implemented on child
                classes. It will raise an error by default.
        '''

        data, metadata = self.data_and_metadata_from_source(source)

        if isinstance(data, AbstractContextManager):
            with data as data:
                for document in self.iterate_data(data, metadata):
                    yield document
        else:
            for doc in self.iterate_data(data, metadata):
                yield doc


    def data_and_metadata_from_source(self, source: Source) -> Tuple[Generator[Any, None, None], Dict]:
        if isinstance(source, tuple) and len(source) == 2:
            source_data, metadata = source
        else:
            source_data = source
            metadata = {}

        if isinstance(source_data, str):
            data = self.data_from_file(source_data)
        elif isinstance(source, bytes):
            data = self.data_from_bytes(source_data)
        else:
            raise TypeError(f'unknown source type: {type(source_data)}')

        return data, metadata


    def data_from_file(self, path: str) -> Any:
        raise NotImplemented('This reader does not support filename input')


    def data_from_bytes(self, bytes: bytes) -> Any:
        raise NotImplemented('This reader does not support bytes input')


    def iterate_data(self, data: Any, metadata: Dict) -> Iterable[Document]:
        raise NotImplemented('Data iteration is not implemented')


    def documents(self, sources:Iterable[Source] = None) -> Iterable[Document]:
        '''
        Returns an iterable of extracted documents from source files.

        Parameters:
            sources: an iterable of paths to source files. If omitted, the reader
                class will use the value of `self.sources()` instead.

        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.
        '''
        sources = sources or self.sources()
        return (document
                for source in sources
                for document in self.source2dicts(
                    source
                )
                )

    def export_csv(self, path: str, sources: Optional[Iterable[Source]] = None) -> None:
        '''
        Extracts documents from sources and saves them in a CSV file.

        This will write a CSV file in the provided `path`. This method has no return
        value.

        Parameters:
            path: the path where the CSV file should be saved.
            sources: an iterable of paths to source files. If omitted, the reader class
                will use the value of `self.sources()` instead.
        '''
        documents = self.documents(sources)

        with open(path, 'w') as outfile:
            writer = csv.DictWriter(outfile, self.fieldnames)
            writer.writeheader()
            for doc in documents:
                writer.writerow(doc)


    def _reject_extractors(self, *inapplicable_extractors: extract.Extractor):
        '''
        Raise errors if any fields use any of the given extractors.

        This can be used to check that fields use extractors that match
        the Reader subclass.

        Raises:
            RuntimeError: raised when a field uses an extractor that is provided
                in the input.
        '''
        for field in self.fields:
            if isinstance(field.extractor, inapplicable_extractors):
                raise RuntimeError(
                    "Specified extractor method cannot be used with this type of data")
