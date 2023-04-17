#!/bin/bash

# Install mypy with pip install: https://github.com/python/mypy

# If all checks pass there should be nothing printed to output,
# otherwise you'll see corresponding errors.

mypy --ignore-missing-imports --strict . 
