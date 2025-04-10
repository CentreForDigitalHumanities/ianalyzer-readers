# CSV reader

This example will define a basic CSV reader. 

Our dataset is contained in a directory `~/data`, which contains a single file, `Hamlet.csv`, that contains the script for *Hamlet* by William Shakespeare. A shortened version of the file looks as follows:

```csv
act,scene,character,line
# ...
"I","V","","SCENE V. A more remote part of the Castle."
"I","V","HAMLET","Whither wilt thou lead me? Speak, I'll go no further."
"I","V","GHOST","Mark me."
"I","V","HAMLET","I will."
"I","V","GHOST","My hour is almost come,"
"I","V","GHOST","When I to sulph'rous and tormenting flames"
"I","V","GHOST","Must render up myself."
"I","V","HAMLET","Alas, poor ghost!"
"I","V","GHOST","Pity me not, but lend thy serious hearing"
"I","V","GHOST","To what I shall unfold."
"I","V","HAMLET","Speak, I am bound to hear."
# ...
```

Since this data is encoded as CSV, we can use the `CSVReader` as a base class for our reader:

```python
from ianalyzer_readers.readers.csv import CSVReader

class HamletReader(CSVReader):
    pass
```

## File discovery

Before we can use the `HamletReader`, some additional attributes must be implemented. First, we need to implement `data_directory` and `sources`.

```python
from ianalyzer_readers.readers.csv import CSVReader
import os

class HamletReader(CSVReader):
    data_directory = '~/data'

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            yield path
```

This states that our data is located in `~/data`. The method `sources()` specifies how we can discover files in the directory. Here, we just return the path for each file.

Note that `sources()` includes some assumptions about the contents of the directory, which is why you need to define it for your dataset. For instance, this implementation assumes that all files in the data directory are actually CSV files that can be parsed by the reader, and returns all files. You could add a check for the file extension if that is not appropriate.

## Defining fields

Next, we need to define the fields that should be extracted for each document. The original CSV provides each line in the play, and lists the act, scene, character and the text of the line. We want to extract all those values. For good measure, we will also include the name of the play as a constant value.

```python
from ianalyzer_readers.readers.csv import CSVReader
from ianalyer_readers.readers.core import Field
from ianalyzer_readers.extract import CSV, Constant
import os

class HamletReader(CSVReader):
    data_directory = '~/data'

    play = Field(
        name='play',
        extractor=Constant('Hamlet')
    )
    act = Field(
        name='act',
        extractor=CSV('act')
    )
    scene = Field(
        name='scene',
        extractor=CSV('scene')
    )
    character = Field(
        name='character',
        extractor=CSV('character')
    )
    line = Field(
        name='line',
        extractor=CSV('line')
    )
    fields = [play, act, scene, character, line]

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            yield path, {}
```

At this point, we should be able to use our reader. We look at the output of `documents()` to see the extracted value:

```python
reader = HamletReader()
docs = list(reader.documents())
print(docs)
```

<details>
<summary>Extracted documents</summary>

The example section would look like this in the output:

```python
[
    # ...
    {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': None,
        'line': 'SCENE V. A more remote part of the Castle.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'HAMLET',
        'line': "Whither wilt thou lead me? Speak, I'll go no further.",
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': 'Mark me.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'HAMLET',
        'line': 'I will.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': 'My hour is almost come,',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': "When I to sulph'rous and tormenting flames",
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': 'Must render up myself.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'HAMLET',
        'line': 'Alas, poor ghost!',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': 'Pity me not, but lend thy serious hearing',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'GHOST',
        'line': 'To what I shall unfold.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'HAMLET',
        'line': 'Speak, I am bound to hear.',
    }
    # ...
]
```

</details>

## Tweaking extraction

We can adjust the CSV extraction.

### Transforming values

The `character` field returns the character's names in uppercase, e.g. `'HAMLET'` (how they appeared in the data). Say that we would prefer `'Hamlet'`; we can add a `transform` argument to the extractor for `character`.

```python
def format_name(name):
    if name:
        return name.title()

character = Field(
    name='character',
    extractor=CSV('character', transform=format_name)
)
```

The check `if name` is needed because the character can also be `None`. If a name is provided, it will be converted to title case.

Now the character names in the output will be `'Hamlet'` and `'Ghost'`.

### Grouping rows

Instead of returning documents of a single line, we would like the reader to group multiple lines spoken by the same character.

This can be done by setting the attribute `field_entry = 'character'` on the `HamletReader` class. This will instruct the reader to group consecutive rows with the same value in the `character` column. (Note that this refers to the name of the _column_ in the CSV, not the field `character` that we defined!)

For grouped rows, the default behaviour for the `CSV` extractor is to extract its value from the first row. This makes sense for `character`, `act`, and `scene`, but not for `line`.

We need to adjust the extractor for `line` so it extracts all lines instead. For clarity, let's rename it to `lines`.

```python
lines = Field(
    name='lines',
    extractor=CSV('line', multiple=True, transform='\n'.join)
)
```

We add `multiple=True` to select all lines, and add a `transform` argument to the lines are formatted into a single string with linebreaks.

At this point, the reader class should look like this:

```python
from ianalyzer_readers.readers.csv import CSVReader
from ianalyer_readers.readers.core import Field
from ianalyzer_readers.extract import CSV, Constant
import os

def format_name(name):
    if name:
        return name.title()

class HamletReader(CSVReader):
    data_directory = '~/data'

    field_entry = 'character'

    play = Field(
        name='play',
        extractor=Constant('Hamlet')
    )
    act = Field(
        name='act',
        extractor=CSV('act')
    )
    scene = Field(
        name='scene',
        extractor=CSV('scene')
    )
    character = Field(
        name='character',
        extractor=CSV('character', transform=format_name)
    )
    lines = Field(
        name='lines',
        extractor=CSV('line', multiple=True, transform='\n'.join)
    )
    fields = [play, act, scene, character, lines]

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            yield path, {}
```

<details>
<summary>Extracted documents</summary>

Its output should look like this:

```python
[
    # ...
    {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': None,
        'line': 'SCENE V. A more remote part of the Castle.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Hamlet',
        'line': "Whither wilt thou lead me? Speak, I'll go no further.",
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Ghost',
        'line': 'Mark me.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Hamlet',
        'line': 'I will.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Ghost',
        'line': "My hour is almost come,\nWhen I to sulph'rous and tormenting flames\nMust render up myself.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Hamlet',
        'line': 'Alas, poor ghost!',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Ghost',
        'line': 'Pity me not, but lend thy serious hearing\nTo what I shall unfold.',
    }, {
        'play': 'Hamlet',
        'act': 'I',
        'scene': 'V',
        'character': 'Hamlet',
        'line': 'Speak, I am bound to hear.',
    }
    # ...
]
```
</details>

## Adding metadata

Our `HamletReader` used a constant to return the name of the play. If we add more plays to our dataset, this won't work anymore.

Let's say we add some more files in `~/data`, named `Othello.csv`, `The Tragedy of King Lear.csv`, etc. Let's turn our `HamletReader` into a `ShakespeareReader` that will assign the correct title of the play, based on the filename.

Our `sources()` function was already written to yield every file in the data directory, which is what we want. However, the way our CSV files are structured, we will need to find the name of the play at this stage, because it won't be available as a column in the CSV.

```python
from ianalyzer_readers.readers.csv import CSVReader
# ...
import os

# ...

class ShakespeareReader(CSVReader):

    # ...

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            name, ext = os.path.splitext(filename)
            yield path, {'title': name}
```

Now we can change the extractor for `play` so it gets the title from the metadata:

```python
from ianalyer_readers.extract import Metadata

play = Field(
    name='play',
    extractor=Metadata('title')
)
```

So we end up with the following reader:

```python
from ianalyzer_readers.readers.csv import CSVReader
from ianalyer_readers.readers.core import Field
from ianalyzer_readers.extract import CSV, Metadata
import os

def format_name(name):
    if name:
        return name.title()

class ShakespeareReader(CSVReader):
    data_directory = '~/data'

    field_entry = 'character'

    play = Field(
        name='play',
        extractor=Metadata('title')
    )
    act = Field(
        name='act',
        extractor=CSV('act')
    )
    scene = Field(
        name='scene',
        extractor=CSV('scene')
    )
    character = Field(
        name='character',
        extractor=CSV('character', transform=format_name)
    )
    lines = Field(
        name='lines',
        extractor=CSV('line', multiple=True, transform='\n'.join)
    )
    fields = [play, act, scene, character, lines]

    def sources(self, **kwargs):
        for filename in os.listdir(self.data_directory):
            path = os.path.join(self.data_directory, filename)
            name, ext = os.path.splitext(filename)
            yield path, {'title': name}
```

For `Hamlet.csv`, the `ShakespeareReader` will extract the same output as `HamletReader`, but it will also return the correct title for other plays.
