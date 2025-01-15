'''
This module defines a Resource Description Framework (RDF) reader.

Extraction is based on the [rdflib library](https://rdflib.readthedocs.io/en/stable/index.html).
'''

import logging
from typing import Iterable, Union, Dict

from rdflib import BNode, Graph, Literal, URIRef

from .core import Reader, Document
import ianalyzer_readers.extract as extract

logger = logging.getLogger('ianalyzer-readers')


class RDFReader(Reader):
    '''
    A base class for Readers of Resource Description Framework files.
    These could be in Turtle, JSON-LD, RDFXML or other formats,
    see [rdflib parsers](https://rdflib.readthedocs.io/en/stable/plugin_parsers.html).
    '''

    def validate(self):
        self._reject_extractors(extract.CSV, extract.XML)


    def data_from_file(self, path) -> Graph:
        ''' Read a RDF file as indicated by source, return a graph 
        Override this function to parse multiple source files into one graph

        Parameters:
            path: the name of the file to be parsed
        
        Returns:
            rdflib Graph object
        '''
        logger.info(f"parsing {path}")
        g = Graph()
        g.parse(path)
        return g


    def iterate_data(self, data: Graph, metadata: Dict) -> Iterable[Document]:
        document_subjects = self.document_subjects(data)
        for subject in document_subjects:
            yield self._document_from_subject(data, subject, metadata)


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
