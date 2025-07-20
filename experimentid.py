# Copyright (c) 2025, James Frost.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Generate unique experiment identifiers."""

import enum
import json
import sqlite3
import time
from typing import Any

__all__ = ["Parity", "IdentifierGenerator"]


class Parity(enum.Flag):
    """Enum indicating odd or even. They can be ORed together to make any."""

    ODD = enum.auto()
    EVEN = enum.auto()
    ANY = ODD | EVEN


class IdentifierGenerator:
    """
    Generate unique sequential experiment identifiers.

    Identifiers take the following form: "25.2Q0PW"

    An identifier is made by concatenating the two digit current year with a dot
    and a sequential counter encoded in a custom Base30 alphabet. This allows up
    to 24,300,000 identifiers to be generated per year while maintaining a short
    constant length.

    For resilience you should run two independent generation servers with
    different parities. This prevent collisions by issuing odd identifiers from
    one server and even identifiers from the other.

    Parameters
    ----------
    database: sqlite3.Connection
        Connection to the SQLite database for storing IDs and their metadata.
    parity: Parity, optional
        The parity of this instance. This prevents collisions when running a
        pair of servers for resilience. Defaults to any parity.

    Notes
    -----
    The encoding alphabet we use is based on the Base25 alphabet used for Omega
    Catalogue Identifiers by The National Archive.[1]_ It is based on arabic
    numerals and the English alphabet, with visually ambiguous characters and
    vowels removed. Only upper case letters are used to allow unambiguous verbal
    communication. Vowels are removed to avoid forming any meaningful words.

    An area or department code was considered in the identifier, but as it could
    not be determined automatically, it has been omitted.

    References
    ----------

    .. [1] Retter, A., 2020. Archival Catalogue Record Identifiers. Down the
        Code Mine [Online]. Available from:
        https://blog.adamretter.org.uk/archival-catalog-identifiers/ [Accessed
        20 July 2025].

    Examples
    --------
    >>> import sqlite3
    >>> from experimentid import IdentifierGenerator, Parity
    >>> db = sqlite3.connect(":memory:")
    >>> id_gen = IdentifierGenerator(db, Parity.ODD)
    >>> id_gen.new()
    "25.00001"
    """

    alphabet = "0123456789CDFGHJKLMNPQRSTVWXYZ"
    database: sqlite3.Connection
    parity: Parity
    year: str
    counter: int

    def __init__(self, database: sqlite3.Connection, parity: Parity = Parity.ANY):
        # Initialise constant properties.
        self.database = database
        self.parity = parity

        # Ensure we have our database table.
        sql_create_table = """
            CREATE TABLE IF NOT EXISTS experiment_ids (
                id TEXT PRIMARY KEY NOT NULL,
                metadata TEXT NOT NULL
            )
        """
        self.database.execute(sql_create_table)
        self.database.commit()

        # Load last ID from database, with a fallback if there is no last ID.
        sql_select_id = "SELECT id FROM experiment_ids ORDER BY id DESC LIMIT 1"
        stored_id = self.database.execute(sql_select_id).fetchone()
        last_id: str = stored_id[0] if stored_id is not None else "00.00000"

        # Parse the ID into its constituent parts.
        year, raw_counter = last_id.split(".")
        counter = self._decode(raw_counter)

        # Store the year and counter from the last ID. Storing an old value is
        # not a problem, as they will be updated when the next ID is generated.
        self.year = year
        self.counter = counter

    def new(self, metadata: dict[str, Any] = dict()) -> str:
        """
        Generate a new experiment ID.

        Parameters
        ----------
        metadata: dict, optional
            Metadata to associate with the new ID. Must be JSON serialisable.

        Returns
        -------
        id: str
            A unique experiment identifier.

        Raises
        ------
        TypeError
            If the metadata cannot be serialised as JSON.
        ValueError
            If the year has gone backwards, most likely due to the clock having
            been changed, or this code still being in use after 2100.
        """
        # Reject JSON arrays and atoms.
        if not isinstance(metadata, dict):
            raise TypeError("Metadata is not a mapping.")
        # Serialise metadata, ensuring it is normalised.
        metadata_json = json.dumps(metadata, sort_keys=True)
        # Generate a new ID.
        new_id = self._next_id()
        # Insert ID and metadata into database.
        sql_insert_id = "INSERT INTO experiment_ids VALUES (?, ?)"
        self.database.execute(sql_insert_id, (new_id, metadata_json))
        self.database.commit()
        return new_id

    def _next_id(self) -> str:
        """
        Update the year and counter, returning the next identifier.

        Returns
        -------
        next_id: str
            The next ID.

        Raises
        ------
        ValueError
            If the year has gone backwards, most likely due to the clock having
            been changed, or this code still being in use after 2100.
        """
        # Get current 2 digit UTC year.
        year = time.strftime("%y", time.gmtime())
        # Whether the year has changed determines how we update the counter.
        if year == self.year:
            # Year is unchanged. Increase the counter.
            is_even = self.counter % 2 == 0
            if (self.parity == Parity.EVEN and is_even) or (
                self.parity == Parity.ODD and not is_even
            ):
                # Increase by two to maintain the parity of the counter.
                self.counter = self.counter + 2
            else:
                # Increase by one when parity doesn't matter or the parity of
                # the counter is different to the target parity.
                self.counter = self.counter + 1
        elif year > self.year:
            # Year has increased. Update self.year and reset the counter.
            self.year = year
            # Enforce parity when resetting the counter.
            self.counter = 0 if self.parity != Parity.ODD else 1
        else:
            raise ValueError("Year has gone backwards! Check your clock.")
        # Encode and zero pad counter value.
        encoded_counter = self._encode(self.counter).zfill(5)
        # Construct ID from year and encoded counter.
        new_id = f"{year}.{encoded_counter}"
        return new_id

    def _encode(self, n: int) -> str:
        """
        Encode an integer in the custom Base30 alphabet.

        Parameters
        ----------
        n: int
            Positive integer to encode.

        Returns
        -------
        encoded: str
            String representation of encoded integer.

        Raises
        ------
        ValueError
            If n is not a positive integer.
        """
        # Reject invalid values.
        if n < 0:
            raise ValueError("Only positive integers can be encoded.")
        base = len(self.alphabet)
        # Special case to handle encoding 0.
        result = self.alphabet[0] if n == 0 else ""
        # Build up the result string from the least significant digit.
        while n > 0:
            n, remainder = divmod(n, base)
            # Prepend character onto result string. This technically makes this
            # encoding O(n^2) due to repeated string concatenations, but we are
            # not dealing with large enough integers for it to be problematic.
            result = self.alphabet[remainder] + result
        return result

    def _decode(self, s: str) -> int:
        """
        Decode an integer from the custom Base30 alphabet.

        Parameters
        ----------
        s: str
            Encoded integer to decode.

        Returns
        -------
        decoded: int
            Native int representation of decoded integer

        Raises
        ------
        ValueError
            If s contains characters outside of the allowed alphabet.
        """
        base = len(self.alphabet)
        accumulator = 0
        for order, character in enumerate(reversed(s)):
            index = self.alphabet.index(character)
            accumulator += index * base**order
        return accumulator
