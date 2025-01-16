# Custom reader

`ianalyzer_readers` includes several subclasses of `Reader` to handle common data formats, such as the `XMLReader` and `CSVReader`. If you need to handle a new or unique data format, it may be useful to create a new `Reader` subclass.

Note that the `Reader` class provides very little functionality by itself, so creating a custom `Reader` will save little work compared to writing a script from scratch. However, the `Reader` class is used to define a shared interface between different readers, so you can use it to create something compatible with other readers.

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

In this case, our reader is meant to handle a single dataset, so we should describe how to find the data file by implementing `sources()`.

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
- extracts documents from the data object

The format of the data object is up to how you implement the reader; it will depend on how the source data is structures what format makes sense here.

We will start with extracting a data object from a source. There are several methods you can implement here (`data_from_file`, `data_from_bytes`), depending on what source types you which to support. In this case, we know the output of `sources` is a file path, so we need to implement `data_from_file`, which will be called if the source is a file path.

As our intermediate data format, we will just read the string contents of the file:

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

We now need a method to iterate over the source data; in this case, a string of the file contents. The `iterate_data` method must be implemented to take this data as input, together with a metadata dictionary, and return an iterable of documents.

```python
from typing import Iterable, Dict, List
from ianalyzer_readers.core import Document

class BibliographyReader(Reader):
    # ...

    def iterate_data(self, data: str, metadata: Dict) -> Iterable[Document]:
        sections = data.split('\n\n')
        for index, section in enumerate(sections):
            mapping = self._mapping_from_section(section)
            yield {
                field.name: field.extractor.apply(mapping=mapping, metadata=metadata, index=index)
                for field in self.fields
            }

    def _mapping_from_section(self, section: str):
        lines = section.split('\n')
        keys_values = (line.split(': ') for line in lines if len(line))
        return { key: value for key, value in keys_values }
```

For each field, the reader will create the value by calling `field.extractor.apply`. Note that we provide three named arguments to the extractor, which contain the data that extractors can access. `metadata` and `index` are standardised arguments, which are required to support the `Metadata` and `Order` extractors, respectively. (We can also leave these out, if we don't care about supporting these extractor types.)

We also provide the argument `mapping` which contains the data found in the file, in a structure that makes sense for our data. The `mapping` argument isn't used by any of the extractors provided by this package, but we can write a custom extractor that will use it.

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
        for index, section in enumerate(sections):
            mapping = self._mapping_from_section(section)
            yield {
                field.name: field.extractor.apply(mapping=mapping, metadata=metadata, index=index)
                for field in self.fields
            }

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