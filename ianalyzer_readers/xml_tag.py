'''
This module defines the `Tag` class (and various subclasses).

This class is used in the `XML` extractor to read XML/HTML documents.

Each `Tag` describes a query for one or more XML tags based on their
characteristics. It implements a method `find_in_soup` that takes an
element as input and iterates over matching tags.
'''

from typing import Iterable, Optional, Callable, Union, Dict, Any
import bs4



class Tag:
    '''
    Describes a query for a tag in an XML tree.

    This should be used as the base class for all other tags, which can override
    the `__init__()` and `find_in_soup()` methods.

    `Tag` is the most straightforward case: all arguments passed in the constructor
    are passed on as-is to the `find_all()` method of the BeautifulSoup element, searching
    descendants of the input tag.

    See https://www.crummy.com/software/BeautifulSoup/bs4/doc/#kinds-of-filters for
    different ways of searching. This includes searching by:
    - a tag name (possibly as a regular expression)
    - attributes of the tag
    - the string content of the tag
    - a function
    
    Parameters:
        *args: positional arguments to pass on to `soup.find_all()`
        **kwargs: named arguments to pass on to `soup.find_all()`
    '''
    
    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs
    
    def find_next_in_soup(self, soup: bs4.PageElement) -> Optional[bs4.PageElement]:
        '''
        Find the first match for the tag, if any.

        Parameters:
            soup: The element to search from.

        Returns:
            The first matching tag. Returns `None` if there is no match.
        '''
        return next((tag for tag in self.find_in_soup(soup)), None)

    def find_in_soup(self, soup: bs4.PageElement) -> Iterable[bs4.PageElement]:
        '''
        Find all results for this tag.

        Parameters:
            soup: The element to search from.

        Returns:
            An iterable of matching tags. Note that is is not guaranteed that the iterable
                contains any elements.
        
        When subclassing Tag, you will usually want to replace this method. The result
        must be an iterable. (If only one result makes sense, it's an iterable with one
        element.) If the tag may find multiple matches, it's recommended that this method
        returns a generator or a `bs4.ResultSet` rather than collecting all results up
        front.
        '''
        return soup.find_all(*self.args, **self.kwargs)


class CurrentTag(Tag):
    '''
    A Tag query that will return the current tag.

    Primarily useful as a default option.
    '''

    def __init__(self):
        pass

    def find_in_soup(self, soup: bs4.PageElement) -> Iterable[bs4.PageElement]:
        return [soup]


class ParentTag(Tag):
    '''
    A Tag that will select a parent tag based on a fixed level.

    For example, `ParentTag(2)` will always go up two steps in the tree
    and return that tag.

    Parameters:
        level: the number of steps to move up the tree.
    '''

    def __init__(self, level: int = 1):
        self.level = level

    def find_in_soup(self, soup: bs4.PageElement):
        count = 0
        while count < self.level:
            soup = soup.parent if soup else None
            count += 1
        return [soup]


class FindParentTag(Tag):
    '''
    A Tag that will find a parent tag based on query arguments.

    Unlike ParentTag, this searches for a tag with a query.

    For example, `ParentTag('foo')` will search for a `<foo>` ancestor
    of the current tag.

    Parameters:
        *args: positional arguments to pass on to `soup.find_parents()`
        **kwargs: named arguments to pass on to `soup.find_parents()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        return soup.find_parents(*self.args, **self.kwargs)
    

class SiblingTag(Tag):
    '''
    A Tag that will look in an element's siblings.

    Parameters:
        *args: positional arguments to pass on to `soup.find_previous_siblings()`
            and `soup.find_next_siblings()`
        **kwargs: named arguments to pass on to `soup.find_previous_siblings()`
            and `soup.find_next_siblings()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        for tag in soup.find_next_siblings(*self.args, **self.kwargs):
            yield tag
        
        for tag in soup.find_previous_siblings(*self.args, **self.kwargs):
            yield tag

class PreviousSiblingTag(Tag):
    '''
    A Tag that will look in an element's previous siblings.

    Parameters:
        *args: positional arguments to pass on to `soup.find_previous_siblings()`
        **kwargs: named arguments to pass on to `soup.find_previous_siblings()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        return soup.find_previous_siblings(*self.args, **self.kwargs)

class NextSiblingTag(Tag):
    '''
    A Tag that will look in an element's next siblings.

    Parameters:
        *args: positional arguments to pass on to `soup.find_next_siblings()`
        **kwargs: named arguments to pass on to `soup.find_next_siblings()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        return soup.find_next_siblings(*self.args, **self.kwargs)
    
class PreviousTag(Tag):
    '''
    A Tag that will look through tags previous to the current element.

    Parameters:
        *args: positional arguments to pass on to `soup.find_all_previous()`
        **kwargs: named arguments to pass on to `soup.find_all_previous()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        return soup.find_all_previous(*self.args, **self.kwargs)
    
class NextTag(Tag):
    '''
    A Tag that will look through tags following the current element.

    Parameters:
        *args: positional arguments to pass on to `soup.find_all_next()`
        **kwargs: named arguments to pass on to `soup.find_all_next()`
    '''

    def find_in_soup(self, soup: bs4.PageElement):
        return soup.find_all_next(*self.args, **self.kwargs)


class TransformTag(Tag):
    '''
    A Tag that will perform a transformation function.

    This Tag allows you to run arbitrary code to move to anywhere in the XML tree.

    Parameters:
        transform: a function that takes an XML element as input and returns an
            iterable of XML elements. (Note that you can return an iterable of
            one, or an empty iterable, if you don't have multiple results.)
    '''

    def __init__(
            self,
            transform: Callable[[bs4.PageElement], Iterable[bs4.PageElement]],
        ):
        self.transform = transform
    
    def find_in_soup(self, soup: bs4.PageElement) -> Iterable[bs4.PageElement]:
        return self.transform(soup)


TagSpecification = Union[Tag, Callable[[Dict], Tag]]

def resolve_tag_specification(tag: TagSpecification, metadata: Dict) -> Tag:
    if callable(tag):
        return tag(metadata)
    else:
        return tag