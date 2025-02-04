# Getting started

`ianalyzer-readers` is a python module to extract data from XML, HTML, CSV or XLSX files.

This module was originally created for [I-analyzer](https://github.com/CentreForDigitalHumanities/I-analyzer), a web application that extracts data from a variety of datasets, indexes them and presents a search interface. To do this, we wanted a way to extract data from source files without having to write a new script "from scratch" for each dataset, and an API that would work the same regardless of the source file type.

The basic usage is that you will use the utilities in this package to create a `Reader` class tailored to a dataset. You specify what your data looks like, and then call the `documents()` method of the reader to get an iterator of documents - where each document is a flat dictionary of key/value pairs.

## Installation

Requires [Python](https://python.org) 3.8 or later. This package can be installed via pip:

```sh
pip install ianalyzer_readers
```

Consult the [PyPI documentation](https://packaging.python.org/en/latest/tutorials/installing-packages/) if you are unsure how to install packages in Python.