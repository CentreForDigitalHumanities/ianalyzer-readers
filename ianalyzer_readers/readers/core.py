'''
This module defines the base classes on which all Readers are built.

The module defines two classes, `Field` and `Reader`.
'''

from .. import extract
from typing import List, Iterable, Dict, Any, Union, Tuple, Optional
import logging
import csv
from os.path import isfile
from contextlib import AbstractContextManager, nullcontext

from requests import Response

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('ianalyzer-readers').setLevel(logging.DEBUG)

SourceData = Union[str, Response, bytes]
'''Type definition of the data types a Reader method can handle.'''

Source = Union[SourceData, Tuple[SourceData, Dict]]
'''
Type definition for the source input to some Reader methods.

Sources are either:

- a string with the path to a filename
- binary data with the file contents. This is not supported on all Reader subclasses
- a requests.Response
- a tuple of one of the above, and a dictionary with metadata

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
            document is the value for this Field is `None`.
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

class Reader:
    '''
    A base class for readers. Readers are objects that can generate documents
    from a source dataset.

    Subclasses of `Reader` can be created to read specific data formats. 
    In practice, you will probably work with a subclass of `Reader` like `XMLReader`,
    `CSVReader`, etc., that provides the core functionality for a file type, and create
    a subclass for a specific dataset.
    
    Some methods of this class need to be implemented in child classes, and will raise
    `NotImplementedError` if you try to use `Reader` directly.

    A fully implemented `Reader` subclass will define how to read a dataset by
    describing:

    - How to obtain its source files.
    - How to parse and iterate over source files.
    - What fields each document contains, and how to extract them from the source data.

    This requires implementing the following attributes/methods:

    - `fields`: a list of `Field` instances that describe the fields that will appear in
        documents, and how to extract their value.
    - `sources`: a method that returns an iterable of sources (e.g. file paths), possibly
        with metadata for each.
    - `data_directory` (optional): a string with the path to the directory containing
        the source data. You can use this in the implementation of `sources`; it's not
        used elsewhere.
    - `data_from_file` `data_from_bytes`, `data_from_response`: methods that respectively
        receive a file path, a byte sequence, or an HTTP response, and return a data
        object. (The type of the data will depend on how you implement your reader; this
        could be a parsed graph, a row iterator, etc.). You must implement at least one of
        these methods to have a functioning reader.
    - `iterate_data`: method that takes a data object (the output of
        `data_from_file`/`data_from_bytes`/`data_from_response`) and a metadata dictionary,
        iterates over the source data, and returns the data that should be passed on to
        extractors for each document.
    - `validate` (optional): a method that will check the reader configuration. This is
        useful for abstract readers like the `XMLReader`, `CSVReader`, etc., so they
        can verify a child class is implementing attributes correctly.

    Abstract reader types like `CSVReader` usually leave `fields` and `sources`
    unimplemented.
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


    @property
    def _required_field_names(self) -> List[str]:
        '''
        A list of the names of all required fields
        '''
        return [field.name for field in self.fields if field.required]


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
            source: Source to extract.
        
        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.
        '''

        self.validate()

        data, metadata = self.data_and_metadata_from_source(source)

        if isinstance(data, AbstractContextManager):
            context_manager = data
        else:
            context_manager = nullcontext(data)
        
        with context_manager as data:
            for index, extracted_data in enumerate(self.iterate_data(data, metadata)):
                base_data = {'metadata': metadata, 'index': index}
                document_data = base_data | extracted_data
                document = self.extract_document(**document_data)
                if self._has_required_fields(document):
                    yield document


    def data_and_metadata_from_source(self, source: Source) -> Tuple[Any, Dict]:
        '''
        Extract the data and metadata object from a source.

        Parameters:
            source: Source to extract.

        Returns:
            A tuple with the parsed source data, and the metadata (empty if none was
                provided).
        '''
        if isinstance(source, tuple) and len(source) == 2:
            source_data, metadata = source
        else:
            source_data = source
            metadata = {}

        if isinstance(source_data, str):
            if not isfile(source_data):
                raise FileNotFoundError(f'Invalid file path: {source_data}')
            data = self.data_from_file(source_data)
        elif isinstance(source_data, bytes):
            data = self.data_from_bytes(source_data)
        elif isinstance(source_data, Response):
            data = self.data_from_response(source_data)
        else:
            raise TypeError(f'Unknown source type: {type(source_data)}')

        return data, metadata


    def data_from_file(self, path: str) -> Any:
        '''
        Extract source data from a filename.

        The return type depends on how the reader is implemented, but should be some kind
        of data structure from which documents can be extracted. It serves as the input
        to `self.iterate_data`.

        This method can also return a context manager. This is especially useful to
        iterate over large files in `iterate_data`, without loading the complete file
        contents in memory.

        Tip: if you have implemented `self.data_from_bytes`, this method can probably just
        read the binary contents of the file and call that method.

        Parameters:
            path: The path to a file.
        
        Returns:
            A data object. The type depends on the reader implementation.
        
        Raises:
            NotImplementedError: this method may be implemented on child classes, but
                has no default implementation.
        '''
        
        raise NotImplementedError('This reader does not support filename input')


    def data_from_bytes(self, bytes: bytes) -> Any:
        '''
        Extract source data from a bytes object. Like `data_from_file`, but with bytes
        input.

        Parameters:
            bytes: byte contents of the source
        
        Returns:
            A data object. The type depends on the reader implementation. This may also
                be a context manager.
        
        Raises:
            NotImplementedError: this method may be implemented on child classes, but
                has no default implementation.
        '''
        
        raise NotImplementedError('This reader does not support bytes input')


    def data_from_response(self, response: Response) -> Any:
        '''
        Extract data from an HTTP response. Like `data_from_file`, but with `Response`
        input.

        Parameters:
            response: HTTP response object
        
        Returns:
            A data object. The type depends on the reader implementation. This may also
                be a context manager.
        
        Raises:
            NotImplementedError: this method may be implemented on child classes, but has
                no default implementation.
        '''
        raise NotImplementedError('This reader does not support Response input')


    def iterate_data(self, data: Any, metadata: Dict) -> Iterable[Document]:
        '''
        Iterate parsed source data, return data for each document.

        This should return the arguments that are passed on to field extractors per
        document. These usually cater to a specific extractor type. For example, the
        `CSVReader` returns an argument `rows`, which is used by the `CSV` extractor.

        The core `source2dicts` method will also provide `metadata` and `index` arguments
        to extractors, which you may override by providing them here.

        Parameters:
            data: The data object from a source. The type depends on the reader
                implementation; this is the output of `self.data_from_file` or
                `self.data_from_bytes`.
            metadata: Dictionary containing metadata for the source.
        
        Returns:
            An iterable of dictionaries. Each iteration will be extracted as a single
            document. The items in the dictionary are given as arguments to field
            extractors.

        Raises:
            NotImplementedError: This method must be implemented on child classes. It
                will raise an error otherwise.
        '''
        raise NotImplementedError('Data iteration is not implemented')


    def extract_document(
            self,
            **kwargs
        ) -> Document:
        '''
        Extract each field of a document, based on the raw data for the document
        '''
        return {
            field.name: field.extractor.apply(**kwargs)
            for field in self.fields
            if not field.skip
        }

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


    def validate(self):
        '''
        Validate that the reader is configured properly.

        This is a good place to check parameters that are overridden in a child class. A
        common use case is use self._reject_extractors to raise an error if any fields use
        unsupported extractor types.
        '''
        pass

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

    def _has_required_fields(self, document: Document) -> Iterable[Document]:
        '''
        Check whether a document has a value for all fields marked as required.
        '''

        has_field = lambda field_name: document.get(field_name, None) is not None
        return all(
            has_field(field_name) for field_name in self._required_field_names
        )
