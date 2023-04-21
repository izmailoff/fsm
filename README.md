# FSM
Simple to use persistent Finite State Machine (FSM) for Python projects


## Prerequisites

Postgres database or MongoDB for storing state.

    sudo apt install postgresql postgresql-contrib

Python3.10

## Dev Setup

    python3.10 -m venv env
    . ./env/bin/activate
    pip install -r requirements.txt

Install test requirements:

    pip install -r test-requirements.txt

Run tests:

    cd <project_dir>
    nose2

Run type checks:

    ./run_typechecker.sh

## Building Package

    python setup.py install

or

    python setup.py build

TODO: replace requirements and build with poetry

`pip install fsm==<ver>`
