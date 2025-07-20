# experimentid

**experimentid** is a library for generating unique experiment identifiers. Each
identifier encodes the current year and a counter in a custom Base30 alphabet,
allowing for millions of unique IDs per year in a short, human-friendly format.

## Features

- Generates sequential IDs in the format `YY.COUNTER`, e.g. `25.2Q0PW`.
- Custom Base30 encoding for compact, human-friendly identifiers.
- Supports odd/even parity for resilient distributed generation.
- Stores IDs and associated metadata in a SQLite database.

## Requirements

Just python 3.11 or greater.

Development uses `ruff` for code formatting and linting and `pytest` for unit
tests.

## Installation

Copy [`experimentid.py`](experimentid.py) into your project.

## Usage

Basic usage:

```python
import sqlite3
from experimentid import IdentifierGenerator, Parity

db = sqlite3.connect(":memory:")
id_gen = IdentifierGenerator(db)
print(id_gen.new())  # e.g. "25.00000"
```

With parity (for independent distributed generation):

```python
even_db = sqlite3.connect(":memory:")
odd_db = sqlite3.connect(":memory:")
id_gen_even = IdentifierGenerator(even_db, Parity.EVEN)
id_gen_odd = IdentifierGenerator(odd_db, Parity.ODD)
print(id_gen_even.new())  # Even counter
print(id_gen_odd.new())   # Odd counter
```

With metadata:

```python
metadata = {
    "owner": "alice",
    "timestamp": 1750000000,
}
print(id_gen.new(metadata))  # Metadata is stored in the database.
```

## Running as a Server

The example CGI and WSGI servers implemented a basic HTTP API:

- `GET` returns a new ID.
- `POST` accepts JSON metadata in the request body and returns a new ID.

## Testing

Run the unit tests with pytest:

```sh
pytest
```

## Licence

Licenced under the [BSD 3-Clause License](LICENCE).
