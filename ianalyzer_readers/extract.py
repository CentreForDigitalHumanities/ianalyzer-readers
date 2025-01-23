'''
This module contains extractor classes that can be used to obtain values for each field
in a Reader.

Some extractors are intended to work with specific `Reader` classes, while others
are generic.
'''

import re
import logging
import traceback
from typing import Any, Dict, Callable, Union, List, Optional, Iterable
import warnings

import bs4
import html
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection

logger = logging.getLogger()

from ianalyzer_readers.xml_tag import TagSpecification, resolve_tag_specification


class Extractor(object):
    '''
    Base class for extractors.

    An extractor contains a method that can be used to gather data for a field. 

    Parameters:
        applicable: 
            optional argument to check whether the extractor can be used. This should
            be another extractor, which is applied first; the containing extractor
            is only applied if the result is truthy. Any extractor can be used, as long as
            it's supported by the Reader in which it's used. If left as `None`, this 
            extractor is always applicable.
        transform: optional function to transform or postprocess the extracted value.
    '''

    def __init__(self,
                 applicable: Union['Extractor', Callable[[Dict], bool], None] = None,
                 transform: Optional[Callable] = None
                 ):

        if callable(applicable):
            warnings.warn(
                'Using a callable as "applicable" argument is deprecated; provide an '
                'Extractor instead',
                DeprecationWarning,
            )

        self.transform = transform
        self.applicable = applicable


    def apply(self, *nargs, **kwargs):
        '''
        Test if the extractor is applicable to the given arguments and if so,
        try to extract the information.
        '''
        if self._is_applicable(*nargs, **kwargs):
            result = self._apply(*nargs, **kwargs)
            try:
                if self.transform:
                    return self.transform(result)
            except Exception:
                logger.error(traceback.format_exc())
                logger.critical("Value {v} could not be converted."
                                .format(v=result))
                return None
            else:
                return result
        else:
            return None

    def _apply(self, *nargs, **kwargs):
        '''
        Actual extractor method to be implemented in subclasses (assume that
        testing for applicability and post-processing is taken care of).

        Raises:
            NotImplementedError: This method needs to be implemented on child
                classes. It will raise an error by default.
        '''
        raise NotImplementedError()


    def _is_applicable(self, *nargs, **kwargs) -> bool:
        '''
        Checks whether the extractor is applicable, based on the condition passed as the
        `applicable` parameter.
        
        If no condition is provided, this is always true. If the condition is an
        Extractor, this checks whether the result is truthy.

        If the condition is a callable, it will be called with the document metadata as
        an argument. This option is deprecated; you can use the Metadata extractor to
        replace it.

        Raises:
            TypeError: Raised if the applicable parameter is an unsupported type.
        '''
        if self.applicable is None:
            return True
        if isinstance(self.applicable, Extractor):
            return bool(self.applicable.apply(*nargs, **kwargs))
        if callable(self.applicable):
            return self.applicable(kwargs.get('metadata'))
        return TypeError(
            f'Unsupported type for "applicable" parameter: {type(self.applicable)}'
        )

class Choice(Extractor):
    '''
    Use the first applicable extractor from a list of extractors.

    This is a generic extractor that can be used in any `Reader`.

    The Choice extractor will use the `applicable` property of its provided extractors
    to check which applies. 

    Example usage: 
    
        Choice(Constant('foo', applicable=some_condition), Constant('bar'))

    This would extract `'foo'` if `some_condition` is met; otherwise,
    the extracted value will be `'bar'`.

    Note the difference with `Backup`: `Backup` will select the first truthy value from a
    list of extractors, but `Choice` only checks the `applicable` condition. For example:

        Choice(
            CSV('foo', applicable=Metadata('bar')),
            CSV('baz'),
        )

        Backup(
            CSV('foo', applicable=Metadata('bar')),
            CSV('baz'),
        )

    These extractors behave differently if the "bar" condition holds, but the "foo" field
    is empty. `Backup` will try to extract the "baz" field, `Choice` will not.

    Parameters:
        *extractors: extractors to choose from. These should be listed in descending
            order of preference.
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, *extractors: Extractor, **kwargs):
        self.extractors = list(extractors)
        super().__init__(**kwargs)

    def _apply(self, *nargs, **kwargs):
        for extractor in self.extractors:
            if extractor._is_applicable(*nargs, **kwargs):
                return extractor.apply(*nargs, **kwargs)
        return None


class Combined(Extractor):
    '''
    Apply all given extractors and return the results as a tuple.

    This is a generic extractor that can be used in any `Reader`.

    Example usage:

        Combined(Constant('foo'), Constant('bar'))
    
    This would extract `('foo', 'bar')` for each document.

    Parameters:
        *extractors: extractors to combine.
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, *extractors: Extractor, **kwargs):
        self.extractors = list(extractors)
        super().__init__(**kwargs)

    def _apply(self, *nargs, **kwargs):
        return tuple(
            extractor.apply(*nargs, **kwargs) for extractor in self.extractors
        )


class Backup(Extractor):
    '''
    Try all given extractors in order and return the first result that evaluates as true

    This is a generic extractor that can be used in any `Reader`.

    Example usage:

        Backup(Constant(None), Constant('foo'))
    
    Since the first extractor returns `None`, the second extractor will be used, and the 
    extracted value would be `'foo'`.

    Note the difference with `Choice`: `Backup` is based on the _extracted value_,
    `Choice` on the `applicable` parameter of each extractor.

    Parameters:
        *extractors: extractors to use. These should be listed in descending order of
            preference.
        **kwargs: additional options to pass on to `Extractor`.
    '''
    def __init__(self, *extractors: Extractor, **kwargs):
        self.extractors = list(extractors)
        super().__init__(**kwargs)

    def _apply(self, *nargs, **kwargs):
        for extractor in self.extractors:
            result = extractor.apply(*nargs, **kwargs)
            if result:
                return result
        return None


class Constant(Extractor):
    '''
    This extractor 'extracts' the same value every time, regardless of input.

    This is a generic extractor that can be used in any `Reader`.

    It is especially useful in combination with `Backup` or `Choice`.

    Parameters:
        value: the value that should be "extracted".
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, value: Any, *nargs, **kwargs):
        self.value = value
        super().__init__(*nargs, **kwargs)

    def _apply(self, *nargs, **kwargs):
        return self.value


class Metadata(Extractor):
    '''
    This extractor extracts a value from provided metadata.

    This is a generic extractor that can be used in any `Reader`.
    
    Parameters:
        key: the key in the metadata dictionary that should be
            extracted.
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, key: str, *nargs, **kwargs):
        self.key = key
        super().__init__(*nargs, **kwargs)

    def _apply(self, metadata: Dict, *nargs, **kwargs):
        return metadata.get(self.key)

class Pass(Extractor):
    '''
    An extractor that just passes the value of another extractor.

    This is a generic extractor that can be used in any `Reader`.

    This is useful if you want to stack multiple `transform` arguments. For example:

        Pass(Constant('foo  ', transfrom=str.upper), transform=str.strip)

    This will extract `str.strip(str.upper('foo  '))`, i.e. `'FOO'`.
    
    Parameters:
        extractor: the extractor of which the value should be passed
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, extractor: Extractor, *nargs, **kwargs):
        self.extractor = extractor
        super().__init__(**kwargs)

    def _apply(self, *nargs, **kwargs):
        return self.extractor.apply(*nargs, **kwargs)

class Order(Extractor):
    '''
    An extractor that returns the index of the document in its
    source file.

    The index of the document needs to be passed on the by `Reader`, which needs to
    implement some kind of counter in its `source2dicts` method. The `Reader` subclasses
    in this package all implement this, and so `Order` can safely be used in any of them.
    However, custom `Reader` subclasses may not support this extractor.

    Parameters:
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def _apply(self, index: int = None, *nargs, **kwargs):
        return index

class XML(Extractor):
    '''
    Extractor for XML data. Searches through a BeautifulSoup document.

    This extractor should be used in a `Reader` based on `XMLReader`. (Note that this
    includes the `HTMLReader`.)

    The XML extractor has a lot of options. When deciding how to extract a value, it
    usually makes sense to determine them in this order:

    - Choose whether to use the source file (default), or use an external XML file by
        setting `external_file`.
    - Choose where to start searching. The default searching point is the entry tag
        for the document, but you can also start from the top of the document by setting
        `toplevel`.
    - Describe the tag(s) you're looking for as a Tag object. You can also provide multiple
        tags to chain queries. 
    - If you need to return _all_ matching tags, rather than the first match, set
        `multiple=True`.
    - Choose how to extract a value: set `attribute`, `flatten`, or `extract_soup_func`
        if needed.
    - The extracted value is a string, or the output of `extract_soup_func`. To further
        transform it, add a function for `transform`.

    Parameters:
        tags:
            Tags to select. Each of these can be a `Tag` object, or a callable that
            takes the document metadata as input and returns a `Tag`.

            If no tags are provided, the extractor will work form the starting tag.
            
            Tags represent a query to select tags from current tag (e.g. the entry tag of
            the document). If you provide multiple, they are chained: each Tag query is
            applied to the results from the previous one.
        attribute:
            By default, the extractor will extract the text content of the tag. Set this
            property to extract the value of an _attribute_ instead.
        flatten:
            When extracting the text content of a tag, `flatten` determines whether
            the contents of non-text children are flattened. If `False`, only the direct
            text content of the tag is extracted.
            
            This parameter does nothing if `attribute=True` is set.
        toplevel:
            If `True`, the extractor will search from the toplevel tag of the XML
            document, rather than the entry tag for the document.
        multiple:
            If `False`, the extractor will extract the first matching element. If 
            `True`, it will extract a list of all matching elements.
        external_file:
            If `True`, the extractor will look through a secondary XML file (usually one
            containing metadata). It requires that the passed metadata have an
            `'external_file'` key that specifies the path to the file.

            Note: this option is not supported when this extractor is nested in another
            extractor (like `Combined`).
        extract_soup_func: A function to extract a value directly from the soup element,
            instead of using the content string or an attribute.
            `attribute` and `flatten` will do nothing if this property is set.
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self,
                 *tags: TagSpecification,
                 attribute: Optional[str] = None,
                 flatten: bool = False,
                 toplevel: bool = False,
                 multiple: bool = False,
                 external_file: bool = False,
                 extract_soup_func: Optional[Callable] = None,
                 **kwargs
                 ):

        self.tags = tags
        self.attribute = attribute
        self.flatten = flatten
        self.toplevel = toplevel
        self.multiple = multiple
        self.external_file = external_file
        self.extract_soup_func = extract_soup_func
        super().__init__(**kwargs)

    def _select(self, tags: Iterable[TagSpecification], soup: bs4.PageElement, metadata=None):
        '''
        Return the BeautifulSoup element that matches the constraints of this
        extractor.
        '''

        if len(tags) > 1:
            tag = resolve_tag_specification(tags[0], metadata)
            for element in tag.find_in_soup(soup):
                for result in self._select(tags[1:], element, metadata):
                    yield result
        elif len(tags) == 1:
            tag = resolve_tag_specification(tags[0], metadata)
            for result in tag.find_in_soup(soup):
                yield result
        else:
            yield soup


    def _apply(self, soup_top, soup_entry, *nargs, **kwargs):
        results_generator = self._select(
            self.tags,
            soup_top if self.toplevel else soup_entry,
            metadata=kwargs.get('metadata')
        )
        
        if self.multiple:
            results = list(results_generator)
            return list(map(self._extract, results))
        else:
            result = next(results_generator, None)
            return self._extract(result)

    def _extract(self, soup: Optional[bs4.PageElement]):
        if not soup:
            return None

        # Use appropriate extractor
        if self.extract_soup_func:
            return self.extract_soup_func(soup)
        elif self.attribute:
            return self._attr(soup)
        else:
            if self.flatten:
                return self._flatten(soup)
            else:
                return self._string(soup)    

    def _string(self, soup):
        '''
        Output direct text contents of a node.
        '''

        if isinstance(soup, bs4.element.Tag):
            return soup.string
        else:
            return [node.string for node in soup]

    def _flatten(self, soup):
        '''
        Output text content of node and descendant nodes, disregarding
        underlying XML structure.
        '''

        if isinstance(soup, bs4.element.Tag):
            text = soup.get_text()
        else:
            text = '\n\n'.join(node.get_text() for node in soup)

        _softbreak = re.compile('(?<=\S)\n(?=\S)| +')
        _newlines = re.compile('\n+')
        _tabs = re.compile('\t+')

        return html.unescape(
            _newlines.sub(
                '\n',
                _softbreak.sub(' ', _tabs.sub('', text))
            ).strip()
        )

    def _attr(self, soup):
        '''
        Output content of nodes' attribute.
        '''

        if isinstance(soup, bs4.element.Tag):
            if self.attribute == 'name':
                return soup.name
            return soup.attrs.get(self.attribute)
        else:
            if self.attribute == 'name':
                return [ node.name for node in soup]
            return [
                node.attrs.get(self.attribute)
                for node in soup if node.attrs.get(self.attribute) is not None
            ]


class CSV(Extractor):
    '''
    This extractor extracts values from a list of CSV or spreadsheet rows.

    It should be used in readers based on `CSVReader` or `XLSXReader`.

    Parameters:
        column: The name of the column from which to extract the value.
        multiple: If a document spans multiple rows, the extracted value for a
            field with `multiple = True` is a list of the value in each row. If
            `multiple = False` (default), only the value from the first row is extracted.
        convert_to_none: optional, default is `['']`. Listed values are converted to
            `None`. If `None`/`False`, nothing is converted.
        **kwargs: additional options to pass on to `Extractor`.
    '''
    def __init__(self,
            column: str,
            multiple: bool = False,
            convert_to_none: List[str] = [''],
            *nargs, **kwargs):
        self.field = column
        self.multiple = multiple
        self.convert_to_none = convert_to_none or []
        super().__init__(*nargs, **kwargs)

    def _apply(self, rows, *nargs, **kwargs):
        if self.field in rows[0]:
            if self.multiple:
                return [self.format(row[self.field]) for row in rows]
            else:
                row = rows[0]
                return self.format(row[self.field])

    def format(self, value):
        if value and value not in self.convert_to_none:
            return value


class ExternalFile(Extractor):
    '''
    Free for all external file extractor that provides a stream to `stream_handler`
    to do whatever is needed to extract data from an external file. Relies on `associated_file`
    being present in the metadata. Note that the XMLExtractor has a built in trick to extract
    data from external files (i.e. setting `external_file`), so you probably need that if your
    external file is XML.

    Parameters:
        stream_handler: function that will handle the opened file.
        **kwargs: additional options to pass on to `Extractor`.
    '''

    def __init__(self, stream_handler: Callable, *nargs, **kwargs):
        super().__init__(*nargs, **kwargs)
        self.stream_handler = stream_handler

    def _apply(self, metadata, *nargs, **kwargs):
        '''
        Extract `associated_file` from metadata and call `self.stream_handler` with file stream.
        '''
        return self.stream_handler(open(metadata['associated_file'], 'r'))


class JSON(Extractor):
    '''
    An extractor to extract data from JSON.
    This extractor assumes that each source is dictionary without nested lists.
    When working with nested lists, use JSONReader to unnest.

    Parameters:
        keys (Iterable[str]): the keys with which to retrieve a field value from the source
    '''

    def __init__(self, *keys, **kwargs):
        self.keys = list(keys)
        super().__init__(**kwargs)

    def _apply(self, data: Union[str, dict], key_index: int = 0, **kwargs) -> str:
        key = self.keys[key_index]
        data = data.get(key)
        if len(self.keys) > key_index + 1:
            key_index += 1
            return self._apply(data, key_index)
        return data


class RDF(Extractor):
    """An extractor to extract data from RDF triples

    Parameters:
        predicates:
            an iterable of predicates (i.e., the middle part of a RDF triple) with which to query for objects
            when passing no predicate, the current subject will be returned
        multiple:
            if `True`: return a list of all nodes for which the query returns a result,
            if `False`: return the first node matching a query
        is_collection:
            specify whether the data of interest is a collection, i.e., sequential data
            a collection is indicated by the predicates `rdf:first` and `rdf:rest`, see [rdflib documentation](https://rdflib.readthedocs.io/en/stable/_modules/rdflib/collection.html)

    """

    def __init__(
        self,
        *predicates: Iterable[URIRef],
        multiple: bool = False,
        is_collection: bool = False,
        **kwargs,
    ):
        self.predicates = predicates
        self.multiple = multiple
        self.is_collection = is_collection
        super().__init__(**kwargs)

    def _apply(self, graph: Graph = None, subject: BNode = None, *nargs, **kwargs) -> Union[str, List[str]]:
        ''' apply a query to the RDFReader's graph, with one subject resulting from the `document_subjects` function
        
        Parameters:
            graph: a graph in which to query (set on RDFReader)
            subject: the subject with which to query
        
        Returns:
            a string or list of strings
        '''
        if self.is_collection:
            collection = Collection(graph, subject)
            return [self._get_node_value(node) for node in list(collection)]
        nodes = self._select(graph, subject, self.predicates)
        if len(nodes) == 0:
            return None
        if self.multiple:
            return [self._get_node_value(node) for node in nodes]
        return self._get_node_value(nodes[0])

    def _select(self, graph, subject, predicates: Iterable[URIRef]) -> List[Union[Literal, URIRef, BNode]]:
        ''' search in a graph with predicates
            if more than one predicate is passed, this is a recursive query:
            the first search result of the query is used as a subject in the next query
            
            Parameters:
                subject: the subject with which to query
                graph: the graph to search
                predicates: a list of predicates with which to query
            
            Returns:
                a list of nodes matching the query
        '''
        if not predicates:
            return [subject]
        nodes = list(graph.objects(subject, predicates[0]))
        if len(predicates) > 1:
            return self._select(graph, nodes[0], predicates[1:])
        else:
            return nodes

    def _get_node_value(self, node):
        ''' return a string value extracted from the node '''
        try:
            return node.value
        except:
            return node
