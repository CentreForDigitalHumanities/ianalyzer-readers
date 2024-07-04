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

File discovery is normally implemented when you create the Reader class for a specific dataset. Base reader classes, like `XMLReader` and `CSVReader`, don't implement it. If you're creating a base class for a data format, you can skip this step, and leave to to the reader for each dataset.

In this case, we are writing the reader to handle a specific dataset, so we should describe how to find the data file by implementing `sources()`.

```python
from ianalyzer_readers.readers.core import Reader

class BibliographyReader(Reader):
    data_directory = '.'

    def sources(self, **kwargs):
        yield self.data_directory + '/library.txt'
```

## Extracting documents from source files

All readers must implement a method `source2dicts(self, source)`. This method takes a source as input (from the output of `sources()`), and returns an iterable of the documents it contains.

The built-in reader classes all implement this method. This is usually something like:

- open the file and parse it
- iterate over the file contents to extract each document
- to extract a document, use the reader's `fields` and apply the `extractor` from each field.

This means each reader provides a similar interface with fields, extractors, etc. Technically, however, you are not required to use the `fields` interface. If you want to write a script to return dictionaries directly, you can.

This example will use the reader's `fields` property. We'll use the general structure described above.

### Reading source files

The input to `source2dicts` is a `Source` object. This can be a string with the path, a tuple with a path and a metadata dictionary, or a binary stream with the file contents. In a generic reader class (like `XMLReader`), the implementation of `sources` is left to the subclass, and so the base class should handle these different output types.

In this case, we created our own implementation of `sources`, so we know that it always returns a string with the path. We don't need to implement other source types.

We can start by adding a method that takes a source object and returns the file contents:

```python
from ianalyzer_readers.core import Source

class BibliographyReader(Reader):
    # ...

    def _read_source(self, source: Source) -> str:
        if not isinstance(source, str):
            raise NotImplementedError()

        with open(source) as f:
            return f.read()
```

### Iterate over file contents



```python
# ...
from typing import Iterable

class BibliographyReader(Reader):
    # ...

    def _items_in_source_content(self, content: str) -> Iterable[str]:
        return content.split('\n\n')
```

### Apply field extractors

```python
# ...
from typing import Dict

class BibliographyReader(Reader):
    # ...

    def _document_from_item(self, item: str) -> Dict:
        lines = item.split('\n')
        return {
            field.name: field.extractor.apply(lines=lines)
            for field in self.fields
        }
```

Note that this applies a named argument `lines` to the extractor. Note that from our content, `lines` will contain a list like:

```python
['Title: Pride and Prejudice', 'Author: Jane Austen', 'Year: 1813']
```

We still need an extractor designed to handle this kind of data. Extractors are always written to accept any named arguments, and ignore what they don't use.

For example, in order to use the `Metadata` extractor, the reader must pass on a `metadata` argument.

Extractors for a particular data format, like `CSV` or `XML`, all work like this. They expect the reader to pass on specific arguments which they use to extract data.

In this case, we will create a custom extrator that can make sense of the `lines` we provide.

### Implement source2dicts

We can now put together these methods to implement `source2dicts`:

```python
# ...

class BibliographyReader(Reader):
    # ...

    def source2dicts(self, source: Source) -> Iterable[Dict]:
        content = self._read_source(source)
        items = self._items_in_source_content(content)
        for item in items:
            yield self._document_from_item(item)
```

## Create custom extractor

The `_document_from_item`
