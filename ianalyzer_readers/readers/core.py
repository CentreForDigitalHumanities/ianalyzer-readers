'''
This module defines the base classes on which all Readers are built.

The module defines two classes, `Field` and `Reader`.
'''

from .. import extract
from typing import List, Iterable, Dict, Any, Union, Tuple, Optional
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
    - What fields each document contains.
    - How to extract said fields from the source files.

    This requires implementing the following attributes/methods:

    - `fields`: a list of `Field` instances that describe the fields that will appear in
        documents, and how to extract their value.
    - `sources`: a method that returns an iterable of sources (e.g. file paths), possibly
        with metadata for each. See the method docstring for details.
    - `data_directory` (optional): a string with the path to the directory containing
        the source data. You can use this in the implementation of `sources`; it's not
        used elsewhere.
    - `data_from_file` and/or `data_from_bytes`: methods that respectively receive a file
        path or a byte sequence, and return a data object. (The type of the data will
        depend on how you implement your reader; this could be a parsed graph, a row
        iterator, etc.). You must implement at least one of these methods to have a
        functioning reader; if a method is not implemented, the reader won't support that
        source type (as a value yielded by `sources`).
    - `iterate_data`: method that takes a data object (the output of
        `data_from_file`/`data_from_bytes`) and a metadata dictionary, and returns an
        iterable of extracted documents.
    - `validate` (optional): a method that will check the reader configuration. This is
        useful for abstract readers like the `XMLReader`, `CSVReader`, etc., so they
        can verify a child class is implementing attributes correctly.

    Alternatively, you could override the `source2dicts` method, instead of implementing
    `data_from_file`, `data_from_bytes`, `iterate_data` and `validate`.
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
            source: the source to extract. (See the Source type description for
                supported types of sources.)
        
        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.
        '''

        self.validate()

        data, metadata = self.data_and_metadata_from_source(source)

        if isinstance(data, AbstractContextManager):
            with data as data:
                for document in self.iterate_data(data, metadata):
                    if self._has_required_fields(document):
                        yield document
        else:
            for document in self.iterate_data(data, metadata):
                if self._has_required_fields(document):
                    yield document


    def data_and_metadata_from_source(self, source: Source) -> Tuple[Any, Dict]:
        '''
        Extract the data and metadata object from a source.

        Parameters:
            source: the source object. (See the Source type description for supported
                types.)

        Returns:
            A tuple of a data object from which the contents of the source can be
                extracted, and a metadata dictionary.
        '''
        if isinstance(source, tuple):
            if len(source) == 2:
                source_data, metadata = source
            else:
                raise ValueError(f'Source is a tuple of unexpected length: {len(source)}')
        else:
            source_data = source
            metadata = {}

        if isinstance(source_data, str):
            if not isfile(source_data):
                raise ValueError(f'Invalid file path: {source_data}')
            data = self.data_from_file(source_data)
        elif isinstance(source, bytes):
            data = self.data_from_bytes(source_data)
        else:
            raise TypeError(f'Unknown source type: {type(source_data)}')

        return data, metadata


    def data_from_file(self, path: str) -> Any:
        '''
        Extract source data from a filename.

        The return type depends on how the reader is implemented, but will usually be some
        kind of object that represents structured file contents, from which documents
        can be extracted. It serves as the input to `self.iterate_data`.

        This method can also return a context manager, for example like this:

            @contextmanager
            def data_from_file(self, path):
                with open(path, 'r') as f:
                    yield f

        This is especially useful to iterate over large files in `iterate_data`, without
        loading the complete file contents in memory.

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
        Extract source data from a bytes object.

        The return type depends on how the reader is implemented, but will usually be some
        kind of object that represents structured file contents. It serves as the input
        to `self.iterate_data`.

        Like `self.data_from_file`, this method may also return a context manager.      

        Parameters:
            bytes: byte contents of the source
        
        Returns:
            A data object. The type depends on the reader implementation.
        
        Raises:
            NotImplementedError: this method may be implemented on child classes, but
                has no default implementation.
        '''
        
        raise NotImplementedError('This reader does not support bytes input')


    def iterate_data(self, data: Any, metadata: Dict) -> Iterable[Document]:
        '''
        Iterate documents from source data

        Parameters:
            data: The data object from a source. The type depends on the reader
                implementation; this is the output of `self.data_from_file` or
                `self.data_from_bytes`.
            metadata: Dictionary containing metadata for the source.
        
        Returns:
            An iterable of documents extracted from the source data.

        Raises:
            NotImplementedError: This method must be implemented on child classes. It
                will raise an error otherwise.
        '''
        raise NotImplementedError('Data iteration is not implemented')


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
