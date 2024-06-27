# XML reader

This example will demonstrate how to use the `XMLReader`.

This example is similar to the [CSV example](./example_csv.md). We have a dataset saved in `~/data`, which contains a single file, `Hamlet.xml`. This file contains the script for *Hamlet* by William Shakespeare. A shortened version of the file looks as follows:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<document>
    <meta>
        <title>Hamlet</title>
        <author>William Shakespeare</author>
    </meta>
    <content>
        <act n="I">
            <scene n="V">
                <lines character="HAMLET">
                    <l>Whither wilt thou lead me? Speak, I'll go no further.</l>
                </lines>
                <lines character="GHOST">
                    <l>Mark me.</l>
                </lines>
                <lines character="HAMLET">
                    <l>I will.</l>
                </lines>
                <lines character="GHOST">
                    <l>My hour is almost come,</l>
                    <l>When I to sulph'rous and tormenting flames</l>
                    <l>Must render up myself.</l>
                </lines>
                <lines character="HAMLET">
                    <l>Alas, poor ghost!</l>
                </lines>
                <lines character="GHOST">
                    <l>Pity me not, but lend thy serious hearing</l>
                    <l>To what I shall unfold.</l>
                </lines>
                <lines character="HAMLET">
                    <l>Speak, I am bound to hear.</l>
                </lines>
            </scene>
        </act>
    </content>
</document>
```

We can start building a reader based on the `XMLReader`.

Our reader includes an implementation of `data_directory` and `sources`, which state that the reader must extract all files in `~/data`. This is identical to the [file discovery in the CSV example](./example_csv.md#file-discovery).

```python
from ianalyzer_readers.readers.xml import XMLReader
import os

class HamletReader(XMLReader):
    data_directory = '~/data'

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            yield path, {}
```

## Defining entries

In some datasets, we want to extract a single document from each file. In other datasets, each file consists of multiple documents, and we need to identify multiple _entries_ in the tree. In this case, we want to extract each group of lines as an element. These are the `<lines>` tags in the document.

We'll set the `tag_entry` to describe the tags that make up individual entries.

```python
class HamletReader(XMLReader):
    # ...

    tag_entry = Tag('lines')

    # ...
```

The value is a `Tag` object, which is the way that we describe a tag to look for. We'll see more of this when we extract values for fields below.

## Defining fields

The `XML` extractor can be used to read data from an XML tree. Conceptually, an XML extractor defines:

1. a starting point to search the tree. This is usually the entry tag, i.e. the `<lines>` element we're currently extracting.
2. a description of how to move from the starting tag to the one you're interested in. This boils down a list of instructions like "select a child tag `<a>`, then select its parent, then select a sibling `<b>` of that tag". You can search for everything matching this description, or select the first match.
3. instructions to get a _value_ from the the tag(s) you have finally selected.

To make this more concrete, here are some examples of fields and how they can be described in this format.

**Lines spoken by the character:**

1. Start from the document entry (the `<lines>` element).
2. Select all `<l>` children.
3. Extract the string content of each element.

**The character's name:**

1. Start from the document entry.
2. Stay on this element.
3. Extract the `character` attribute.

**The name of the play:**

1. Start at the top of the XML tree
2. Select a child tag `<meta>`; then select its child tag `<title>`.
3. Extract the string content of the element.

We can implement this as follows.

```python
class HamletReader(XMLReader):
    # ...

    lines = Field(
        'lines',
        XML(
            Tag('l'),
            multiple=True,
        ),
    )
    character = Field(
        'character',
        XML(
            attribute='character'
        )
    )
    title = Field(
        'title',
        XML(
            Tag('meta'),
            Tag('title'),
            toplevel=True
        )
    )


    fields = [lines, character, title]
```

Notes:

- The extractor will start from the entry tag of the document by default. In the `title` field, we set `toplevel` to start from the top of the XML tree instead.
- Each extractor gives a number of `Tag` objects. These describe the steps to select the tag(s) you're interested in. In the `character` field, we do not provide any `Tag`s, because we don't need to traverse the tree.
- The `Tag` pattern may return multiple matches. For example, the `lines` field looks for `<l>` child tags, of which there are often multiple. By default, the extractor will select the first match. In `lines`, we set `multiple=True`, to get a list of all matches.
- The default method to extract a value from a tag is to take its string content. In the `character` field, the `attribute` argument states that we want to take the `character` attribute instead.

Our reader will now return the following output:

```python
[
    {
        'lines': [
            "Whither wilt thou lead me? Speak, I'll go no further.",
        ],
        'character': 'HAMLET',
        'title': 'Hamlet',
    },
    {
        'lines': [
            'Mark me.',
        ],
        'character': 'GHOST',
        'title': 'Hamlet',
    },
    {
        'lines': [
            'I will.',
        ],
        'character': 'HAMLET',
        'title': 'Hamlet',
    },
    {
        'lines': [
            'My hour is almost come,',
            "When I to sulph'rous and tormenting flames",
            'Must render up myself.',
        ],
        'character': 'GHOST',
        'title': 'Hamlet',
    },
    {
        'lines': [
            'Alas, poor ghost!',
        ],
        'character': 'HAMLET',
        'title': 'Hamlet',
    },
        {
        'lines': [
            'Pity me not, but lend thy serious hearing',
            'To what I shall unfold.',
        ],
        'character': 'GHOST',
        'title': 'Hamlet',
    },
    {
        'lines': [
            'Speak, I am bound to hear.',
        ],
        'character': 'HAMLET',
        'title': 'Hamlet',
    },
]
```
