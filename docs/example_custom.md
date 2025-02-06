# Custom reader

`ianalyzer_readers` includes several subclasses of `Reader` to handle common data formats, such as the `XMLReader` and `CSVReader`. If you need to handle a new or unique data format, it may be useful to create a new `Reader` subclass.

Creating a custom reader class will require more work than using a class like `CSVReader`, and will require more understanding of how this package works. You may find that, for your specific use case, creating a reader requires more work than writing a complete script from scratch. The main reason to use the `Reader` framework is to make something compatible with other reader types.

This example will demonstrate how you could implement a custom reader.

Our dataset is a file `library.txt`, which contains bibliographical data for a collection of books. It looks like this:

```txt
Title: Pride and Prejudice
Author: Jane Austen
Year: 1813

Title: Frankenstein, or, the Modern Prometheus
Author: Mary Shelley
Year: 1818

Title: Moby Dick
Author: Herman Melville
Year: 1851

Title: Alice in Wonderland
Author: Lewis Carroll
Year: 1865
```

This data doesn't use a standardised format, but it's consistently structured, so we can write a script to extract the data. We can start by creating a reader class:

```python
from ianalyzer_readers.readers.core import Reader

class BibliographyReader(Reader):
    pass
```

## File discovery

File discovery is normally implemented when you create the Reader class for a specific dataset. If you're creating an abstract class for a data format, like the `CSVReader` or `XMLReader`, you can skip this step, and leave it to the reader for each dataset.

In this case, our reader is meant to handle a single dataset, so we should describe how to find the data file by implementing `sources()`. This just needs to yield a single file.

```python
from ianalyzer_readers.readers.core import Reader

class BibliographyReader(Reader):
    data_directory = '.'

    def sources(self, **kwargs):
        yield self.data_directory + '/library.txt'
```

There are several options for the output type of sources; in this case, we're providing a file path.

## Extracting file contents

To extract documents from a source, a reader must implement two steps:

- extract a data object from a source
- iterate over the data object and return the available data per document

The format of the data object is up to how you implement the reader; it will depend on how the source data is structured what format makes sense here. It could be a graph, an iterator, a dataframe, or something else entirely.

You will then need a method that iterates over this data format to get a set of documents. Per document it should return the data that will be made available to field extractors.

This is quite an abstract description, so let's see how it works in practice.

First, we need to extract a data object from a source. There are several methods you can implement here (`data_from_file`, `data_from_bytes`, `data_from_response`), depending on what source types you wish to support. In this case, we know the output of `sources` is a file path, so we need to implement `data_from_file`, and we can leave the others as-is.

The output of `data_from_file` should be some intermediate data format; we will just return the string contents of the file.

```python
class BibliographyReader(Reader):
    # ...

    def data_from_file(self, path: str) -> str:
        f = open(path, 'r')
        content = f.read()
        f.close()
        return content
```

## Iterating over file contents

We now need a method to iterate over the source data; in this case, a string of the file contents. The `iterate_data` method must be implemented to split this string into documents.

As input, it will receive the data object (the string content), and the metadata for the file. It should iterate over the documents we want to extract (in this case, over each book). Per document, it should return whatever data we want to provide to field extractors.

This data can be of any format you want. Non-universal extractors like `CSV`, `XML`, etc., have specific arguments they expect, so you can tailor your output data to be compatible with a specific extractor class.

In this case, it doesn't really make sense to use one of the existing extractors, so we will make our own extractor class below. At this step, we can choose what information we will provide to our extractor.

In this case, our data provides a few properties for each book: the title, author, and year. So we can parse the lines of text into a mapping of properties to values.

```python
from typing import Iterable, Dict, List
from ianalyzer_readers.core import Document

class BibliographyReader(Reader):
    # ...

    def iterate_data(self, data: str, metadata: Dict) -> Iterable[Document]:
        sections = data.split('\n\n')
        for section in sections:
            mapping = self._mapping_from_section(section)
            yield {'mapping': mapping}

    def _mapping_from_section(self, section: str):
        lines = section.split('\n')
        keys_values = (line.split(': ') for line in lines if len(line))
        return { key: value for key, value in keys_values }
```

## Create custom extractor

```python
from typing import Dict
from ianalyzer_readers.extract import Extractor

class BibliographyExtractor(Extractor):
    def __init__(self, key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.key = key

    def _apply(self, mapping: Dict, **kwargs):
        return mapping.get(self.key, None)
```

## Define fields

The last thing that is required for a functioning reader is a list of fields. Abstract readers like `CSVReader` typically don't implement fields, but a reader won't function without them.

```python
from ianalyzer_readers.core import Field
from ianalyzer_readers.extract import Order, Constant

    fields = [
        Field(
            name='title',
            extractor=BibliographyExtractor('Title'),
        ),
        Field(
            name='author',
            extractor=BibliographyExtractor('Author'),
        ),
        Field(
            name='year',
            extractor=BibliographyExtractor('Year', transform=int),
        ),
        Field(
            name='index',
            extractor=Order(),
        ),
        Field(
            name='file',
            extractor=Constant('library.txt'),
        ),
    ]
```

## Complete example

```python
from typing import Iterable, Dict
import os

from ianalyzer_readers.extract import Extractor
from ianalyzer_readers.readers.core import Reader, Document, Field
from ianalyzer_readers.extract import Order, Constant


class BibliographyExtractor(Extractor):
    def __init__(self, key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.key = key

    def _apply(self, mapping: Dict, **kwargs):
        return mapping.get(self.key, None)


class BibliographyReader(Reader):
    data_directory = os.path.dirname(__file__)

    def sources(self, **kwargs):
        yield self.data_directory + '/library.txt'

    def data_from_file(self, path: str) -> str:
        f = open(path, 'r')
        content = f.read()
        f.close()
        return content

    def iterate_data(self, data: str, metadata: Dict) -> Iterable[Document]:
        sections = data.split('\n\n')
        for section in sections:
            mapping = self._mapping_from_section(section)
            yield {'mapping': mapping}

    def _mapping_from_section(self, section: str):
        lines = section.split('\n')
        keys_values = (line.split(': ') for line in lines if len(line))
        return { key: value for key, value in keys_values }

    fields = [
        Field(
            name='title',
            extractor=BibliographyExtractor('Title'),
        ),
        Field(
            name='author',
            extractor=BibliographyExtractor('Author'),
        ),
        Field(
            name='year',
            extractor=BibliographyExtractor('Year', transform=int),
        ),
        Field(
            name='index',
            extractor=Order(),
        ),
        Field(
            name='file',
            extractor=Constant('library.txt'),
        ),
    ]
```

The `documents()` method of our reader will now return the following output:

```python
[
    {
        'title': 'Pride and Prejudice',
        'author': 'Jane Austen',
        'year': 1813,
        'index': 0,
        'file': 'library.txt',
    },
        {
        'title': 'Frankenstein, or, the Modern Prometheus',
        'author': 'Mary Shelley',
        'year': 1818,
        'index': 1,
        'file': 'library.txt',
    },
        {
        'title': 'Moby Dick',
        'author': 'Herman Melville',
        'year': 1851,
        'index': 2,
        'file': 'library.txt',
    },
        {
        'title': 'Alice in Wonderland',
        'author': 'Lewis Carroll',
        'year': 1865,
        'index': 3,
        'file': 'library.txt',
    },
]
```