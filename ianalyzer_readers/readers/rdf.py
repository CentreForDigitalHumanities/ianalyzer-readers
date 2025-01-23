'''
This module defines a Resource Description Framework (RDF) reader.

Extraction is based on the [rdflib library](https://rdflib.readthedocs.io/en/stable/index.html).
'''

import logging
from typing import Iterable, Union

from rdflib import BNode, Graph, Literal, URIRef

from .core import Reader, Document, Source
import ianalyzer_readers.extract as extract

logger = logging.getLogger('ianalyzer-readers')


class RDFReader(Reader):
    '''
    A base class for Readers of Resource Description Framework files.
    These could be in Turtle, JSON-LD, RDFXML or other formats,
    see [rdflib parsers](https://rdflib.readthedocs.io/en/stable/plugin_parsers.html).
    '''

    def source2dicts(self, source: Source) -> Iterable[Document]:
        '''
        Given a RDF source file, returns an iterable of extracted documents.

        Parameters:
            source: the source file to extract. This can be a string of the file path, or a tuple of the file path and metadata.

        Returns:
            an iterable of document dictionaries. Each of these is a dictionary,
                where the keys are names of this Reader's `fields`, and the values
                are based on the extractor of each field.
        '''
        self._reject_extractors(extract.CSV, extract.XML)

        if isinstance(source, bytes):
            raise Exception('The current reader cannot handle sources of bytes type, provide a file path as string instead')
        try:
            (filename, metadata) = source
        except ValueError:
            filename = source
            metadata = None

        logger.info(f"parsing {filename}")
        g = self.parse_graph_from_filename(
            filename
        )  # TODO: we could also allow Response as source data here, but that would mean the response would also need to include information of the data format, see [this example](https://github.com/RDFLib/rdflib/blob/4.1.2/rdflib/graph.py#L209)

        document_subjects = self.document_subjects(g)
        for subject in document_subjects:
            yield self._document_from_subject(g, subject, metadata)

    def parse_graph_from_filename(self, filename: str) -> Graph:
        ''' Read a RDF file as indicated by source, return a graph 
        Override this function to parse multiple source files into one graph

        Parameters:
            filename: the name of the file to be parsed
        
        Returns:
            rdflib Graph object
        '''
        g = Graph()
        g.parse(filename)
        return g

    def document_subjects(self, graph: Graph) -> Iterable[Union[BNode, Literal, URIRef]]:
        ''' Override this function to return all subjects (i.e., first part of RDF triple) 
        with which to search for data in the RDF graph.
        Typically, such subjects are identifiers or urls.
        
        Parameters:
            graph: the graph to parse
        
        Returns:
            generator or list of nodes
        '''
        return graph.subjects()

    def _document_from_subject(self, graph: Graph, subject: Union[BNode, Literal, URIRef], metadata: dict) -> dict:
        return {field.name: field.extractor.apply(graph=graph, subject=subject, metadata=metadata) for field in self.fields}


def get_uri_value(node: URIRef) -> str:
    """a utility function to extract the last part of a uri
    For instance, if the input is URIRef('https://purl.org/mynamespace/ernie'),
    or URIRef('https://purl.org/mynamespace#ernie')
    the function will return 'ernie'

    Parameters:
        node: an URIRef input node

    Returns:
        a string with the last element of the uri
    """
    return node.fragment or node.defrag().split("/")[-1]
