# Custom reader

`ianalyzer_readers` includes several subclasses of `Reader` to handle common data formats, such as the `XMLReader` and `CSVReader`. If you need to handle a new or unique data format, it may be useful to create a new `Reader` subclass. This example demonstrates how you could implement a custom reader.

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

This data doesn't use a standardised format, but it's consistently structured. We start by creating a reader class:

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
- iterate over the data object and yield extractor input for each document

The format of the source data object is up to you; what format makes sense here will depend on how the source data is structured. It could be a graph, an iterator, a dataframe, or something else entirely.

The second step is a method that iterates over this data format and identifies the entry point for each document. Per document, it should return the data that will be made available to field extractors.

This is quite an abstract description, so let's see how it works in practice.

First, we need to extract a data object from a source. There are several methods you can implement here (`data_from_file`, `data_from_bytes`, `data_from_response`), depending on what source types you wish to support. In this case, we know the output of `sources` is a file path, so we need to implement `data_from_file`; we can leave the others unimplemented.

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

We now need a method to iterate over the source data, i.e. the output of `data_from_file`. In our case, this data object is the file contents as a string. The `iterate_data` method must be implemented to split this into documents.

As input, it will receive the data object (the string content), and the metadata for the file. (Our reader does not provide metadata, so the metadata will be empty.) It should iterate over the documents we want to extract (in this case, over each book). Per document, it should return whatever data we want to provide to field extractors.

The data for field extractors can be of any format you want. Non-universal extractors like `CSV`, `XML`, etc., have specific arguments they expect, so you could tailor your output data to be compatible with a specific extractor class.

In this case, it doesn't really make sense to use one of the existing extractors, so we will make our own extractor class later on. At this step, we can choose what information we will provide to our extractor.

In this case, our data provides a few properties for each book: the title, author, and year. So we can parse the lines of text into a mapping of properties to values.

```python
from typing import Iterable, Dict, List
from ianalyzer_readers.core import Document

class BibliographyReader(Reader):
    # ...

    def iterate_data(self, data: str, metadata: Dict) -> Iterable[Document]:
        # split into entries
        sections = data.split('\n\n')
        for section in sections:
            # get property mapping from each entry
            mapping = self._mapping_from_section(section)
            yield {'mapping': mapping}

    def _mapping_from_section(self, section: str):
        lines = section.split('\n')
        keys_values = (line.split(': ') for line in lines if len(line))
        return { key: value for key, value in keys_values }
```

## Create custom extractor

Our reader provides a `mapping` for each document. We need to create an extractor class that can extract values from the mapping.

Our custom extractor is a subclass of `Extractor`. The base extractor class supports a few parameters on initialisation, such as `transform`. We will add one parameter of our own, `key`, which specifies the property to extract. Note that the initialiser must call `super().__init__()` to make sure inherited parameters are stored.

Our extractor also needs to implement a method `_apply()` which specifies how to extract a value from a document. Here, we expect the reader to provide a `mapping`, and extract the property matching the `key`.

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

The last thing that is required for a functioning reader is a list of fields.

*Note: if you are creating an abstract reader class like `CSVReader`, you should not implement a list of fields.*

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

Note that we can use our custom-made `BibliographyExtractor`, but universal extractors like `Order` and `Constant` are also supported.


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

<details>
<summary>Extracted documents</summary>

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
</details>