# I-analyzer Readers

[![Python package](https://github.com/CentreForDigitalHumanities/ianalyzer-readers/actions/workflows/python-package.yml/badge.svg)](https://github.com/CentreForDigitalHumanities/ianalyzer-readers/actions/workflows/python-package.yml)
[![Documentation Status](https://readthedocs.org/projects/ianalyzer-readers/badge/?version=latest)](https://ianalyzer-readers.readthedocs.io/en/latest/?badge=latest)

`ianalyzer-readers` is a python module to extract data from XML, HTML, CSV, JSON, XLSX or RDF (Linked Data) files.

This module was originally created for [I-analyzer](https://github.com/CentreForDigitalHumanities/I-analyzer), a web application that extracts data from a variety of datasets, indexes them and presents a search interface. To do this, we wanted a way to extract data from source files without having to write a new script "from scratch" for each dataset, and an API that would work the same regardless of the source file type.

The basic usage is that you will use the utilities in this package to create a "reader" class. You specify what your data looks like, and then call the `documents()` method of the reader to get an iterator of documents - where each document is a flat dictionary of key/value pairs.

## Prerequisites

Requires Python 3.9 or later.

## Contents

[ianalyzer_readers](./ianalyzer_readers/) contains the source code for the package. [tests](./tests/) contains unit tests.

## When to use this package

This package is *not* a replacement for more general-purpose libraries like `csv` or Beautiful Soup - it is a high-level interface on top of those libraries.

Our primary use for this package is to pre-process data for I-analyzer, but you may find other uses for it.

Using this package makes sense if you want to extract data in the shape that it is designed for (i.e., a list of flat dictionaries).

What we find especially useful is that all subclasses of `Reader` have the same interface - regardless of whether they are processing CSV, JSON, XML, HTML, RDF or XLSX data. That common interface is crucial in an application that needs to process corpora from different source types, like I-analyzer.

## Usage

Typical usage of this package would be to make a custom Python class for a dataset from which you want to extract a list of documents. We call this a `Reader`. This package provides the base classes to structure readers, and provides extraction utilities for several file types.

For detailed usage documention and examples, visit [ianalyzer-readers.readthedocs.io](https://ianalyzer-readers.readthedocs.io/en/latest/)

If this site is unavailable, you can also generate the documentation site locally; see the [contributing guide](./CONTRIBUTING.md) for insttructions.

## Licence

This code is shared under an MIT licence. See [LICENSE](./LICENSE) for more information.
