"""Unit tests for experimentid.py."""

import json
import sqlite3
import time

import pytest

import experimentid as eid

# struct_time constants.
NOV_2023 = time.gmtime(1700000000)
JUL_2025 = time.gmtime(1750000000)
JAN_2026 = time.gmtime(1768000000)


# Mocking functions.
def mock_old_gmtime(seconds=None):
    return NOV_2023


def mock_gmtime(seconds=None):
    return JUL_2025


def mock_new_year_gmtime(seconds=None):
    return JAN_2026


# Fixtures.
@pytest.fixture()
def db() -> sqlite3.Connection:
    """A fresh in-memory SQLite database."""
    return sqlite3.connect(":memory:")


@pytest.fixture()
def id_gen(db) -> eid.IdentifierGenerator:
    return eid.IdentifierGenerator(db)


# Tests.
def test_combining_parity():
    assert eid.Parity.ODD | eid.Parity.EVEN == eid.Parity.ANY


def test_encode(id_gen):
    """Check integers are correctly encoded in base30."""
    assert id_gen._encode(0) == "0"
    assert id_gen._encode(29) == "Z"
    assert id_gen._encode(30) == "10"
    assert id_gen._encode(2426) == "2PW"
    assert id_gen._encode(2187626) == "2Q0PW"
    assert id_gen._encode(24299999) == "ZZZZZ"


def test_encode_invalid_input(id_gen):
    """Test rejection of inputs containing negative integers."""
    with pytest.raises(ValueError, match="Only positive integers can be encoded."):
        id_gen._encode(-1)


def test_decode(id_gen):
    """Check integers are correctly decoded from base30."""
    assert id_gen._decode("0") == 0
    assert id_gen._decode("Z") == 29
    assert id_gen._decode("10") == 30
    assert id_gen._decode("002PW") == 2426
    assert id_gen._decode("2Q0PW") == 2187626
    assert id_gen._decode("ZZZZZ") == 24299999


def test_decode_invalid_input(id_gen):
    """Test rejection of inputs containing non-alphabet characters."""
    with pytest.raises(ValueError):
        id_gen._decode("Hello, World!")


def test_gen_id_any_parity(db):
    """Check an IdentifierGenerator defaults to ANY parity."""
    unspecified_parity = eid.IdentifierGenerator(db)
    any_parity = eid.IdentifierGenerator(db, parity=eid.Parity.ANY)
    assert unspecified_parity.parity == any_parity.parity


def test_gen_id(id_gen, monkeypatch):
    """Basic test for generating sequential identifiers."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    assert id_gen.new() == "25.00000"
    assert id_gen.new() == "25.00001"
    assert id_gen.new() == "25.00002"


def test_gen_id_even_parity(db, monkeypatch):
    """Basic test for generating sequential identifiers with EVEN parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    id_gen = eid.IdentifierGenerator(db, eid.Parity.EVEN)
    assert id_gen.new() == "25.00000"
    assert id_gen.new() == "25.00002"
    assert id_gen.new() == "25.00004"


def test_gen_id_odd_parity(db, monkeypatch):
    """Basic test for generating sequential identifiers with ODD parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    id_gen = eid.IdentifierGenerator(db, eid.Parity.ODD)
    assert id_gen.new() == "25.00001"
    assert id_gen.new() == "25.00003"
    assert id_gen.new() == "25.00005"


def test_gen_id_resumption(db, monkeypatch):
    """Test resumption from a pre-existing ID."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    # Create the database table.
    eid.IdentifierGenerator(db)
    # Insert large ID into table.
    db.execute('INSERT INTO experiment_ids VALUES ("25.2Q0PW", "{}")')
    db.commit()
    id_gen = eid.IdentifierGenerator(db)
    assert id_gen.new() == "25.2Q0PX"


def test_gen_id_resumption_from_even_even_parity(db, monkeypatch):
    """Test resumption from a pre-existing ID with EVEN parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    # Create the database table.
    eid.IdentifierGenerator(db)
    # Insert large ID into table.
    db.execute('INSERT INTO experiment_ids VALUES ("25.2Q0PW", "{}")')
    db.commit()
    id_gen = eid.IdentifierGenerator(db, eid.Parity.EVEN)
    assert id_gen.new() == "25.2Q0PY"


def test_gen_id_resumption_from_even_odd_parity(db, monkeypatch):
    """Test resumption from a pre-existing ID with ODD parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    # Create the database table.
    eid.IdentifierGenerator(db)
    # Insert large ID into table.
    db.execute('INSERT INTO experiment_ids VALUES ("25.2Q0PW", "{}")')
    db.commit()
    id_gen = eid.IdentifierGenerator(db, eid.Parity.ODD)
    assert id_gen.new() == "25.2Q0PX"


def test_gen_id_resumption_from_odd_even_parity(db, monkeypatch):
    """Test resumption from a pre-existing ID with EVEN parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    # Create the database table.
    eid.IdentifierGenerator(db)
    # Insert large ID into table.
    db.execute('INSERT INTO experiment_ids VALUES ("25.2Q0PX", "{}")')
    db.commit()
    id_gen = eid.IdentifierGenerator(db, eid.Parity.EVEN)
    assert id_gen.new() == "25.2Q0PY"


def test_gen_id_resumption_from_odd_odd_parity(db, monkeypatch):
    """Test resumption from a pre-existing ID with ODD parity."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    # Create the database table.
    eid.IdentifierGenerator(db)
    # Insert large ID into table.
    db.execute('INSERT INTO experiment_ids VALUES ("25.2Q0PX", "{}")')
    db.commit()
    id_gen = eid.IdentifierGenerator(db, eid.Parity.ODD)
    assert id_gen.new() == "25.2Q0PZ"


def test_gen_id_new_year(id_gen, monkeypatch):
    """Test handling of a new year."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    assert id_gen.new() == "25.00000"
    assert id_gen.new() == "25.00001"
    assert id_gen.new() == "25.00002"
    monkeypatch.setattr(time, "gmtime", mock_new_year_gmtime)
    assert id_gen.new() == "26.00000"
    assert id_gen.new() == "26.00001"
    assert id_gen.new() == "26.00002"


def test_gen_id_new_year_even_parity(db, monkeypatch):
    """Test handling of a new year with EVEN parity."""
    id_gen = eid.IdentifierGenerator(db, eid.Parity.EVEN)
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    assert id_gen.new() == "25.00000"
    assert id_gen.new() == "25.00002"
    assert id_gen.new() == "25.00004"
    monkeypatch.setattr(time, "gmtime", mock_new_year_gmtime)
    assert id_gen.new() == "26.00000"
    assert id_gen.new() == "26.00002"
    assert id_gen.new() == "26.00004"


def test_gen_id_new_year_odd_parity(db, monkeypatch):
    """Test handling of a new year with ODD parity."""
    id_gen = eid.IdentifierGenerator(db, eid.Parity.ODD)
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    assert id_gen.new() == "25.00001"
    assert id_gen.new() == "25.00003"
    assert id_gen.new() == "25.00005"
    monkeypatch.setattr(time, "gmtime", mock_new_year_gmtime)
    assert id_gen.new() == "26.00001"
    assert id_gen.new() == "26.00003"
    assert id_gen.new() == "26.00005"


def test_error_time_travel(id_gen, monkeypatch):
    """Test rejection of an old year."""
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    assert id_gen.new() == "25.00000"
    monkeypatch.setattr(time, "gmtime", mock_old_gmtime)
    with pytest.raises(ValueError, match="Year has gone backwards! Check your clock."):
        id_gen.new()


def test_gen_id_metadata(db, monkeypatch):
    """Test inserting metadata when generating the ID."""
    id_gen = eid.IdentifierGenerator(db)
    monkeypatch.setattr(time, "gmtime", mock_gmtime)
    metadata = {
        "repository_url": "https://github.com/Fraetor/experiment-id",
        "owner": "james",
        "creation_timestamp": 1750000000,
    }
    assert id_gen.new(metadata) == "25.00000"
    # Check metadata has been inserted into the database.
    row = db.execute("SELECT metadata FROM experiment_ids").fetchone()
    assert json.loads(row[0]) == metadata


def test_gen_id_invalid_metadata_not_an_object(id_gen):
    """Test rejection of invalid metadata that isn't a dictionary."""
    metadata = [1, 2, 3]
    with pytest.raises(TypeError, match="Metadata is not a mapping."):
        id_gen.new(metadata)
    metadata = "A string"
    with pytest.raises(TypeError, match="Metadata is not a mapping."):
        id_gen.new(metadata)
    metadata = 42
    with pytest.raises(TypeError, match="Metadata is not a mapping."):
        id_gen.new(metadata)


def test_gen_id_invalid_metadata_unserialisable(id_gen):
    """Test rejection of invalid metadata that can't be serialised to JSON."""
    metadata = {"bytes": b"\x00\xff\x00\xff"}
    with pytest.raises(TypeError):
        id_gen.new(metadata)
