#!/usr/bin/env python3

import time
from typing import Literal


class exeID:
    """
    TODO: Write docstring.

    IDs take the following format:

        25.2Q0PW

    The first part is the last two decimal digits of the year of creation,
    followed by a sequential ID encoded in a custom Base30 alphabet. This allows
    up to 24,300,000 IDs to be generated per year while maintaining a constant
    length.

    I considered adding an area or department section to the ID, but I can't see
    how it would be determined automatically.

    For resilience you should be able to run two independent servers. To prevent
    collisions, one server will issue odd ids, while the other will issue even
    ids.

    Arguments
    ---------
    last_id
        The last ID known to have been produced. The sequence will be restarted
        after this ID.

    parity
        The parity of this instance. This should be set when running a pair of
        servers for resilience, as it prevents collisions.
    """

    # The encoding alphabet we use is based on the Base25 alphabet used for
    # Omega Catalogue Identifiers by The National Archive. We are able to
    # include a few additional characters that they exclude for reasons that
    # don't affect us, to bring it up to a Base30 alphabet.
    # https://blog.adamretter.org.uk/archival-catalog-identifiers/
    # By avoiding vowels, there are essentially no words that can be made.
    # (Confirmed by `grep -iv '[aeiou]' /usr/share/dict/words`)
    alphabet = "0123456789CDFGHJKLMNPQRSTVWXYZ"
    counter: int
    year: str
    parity: Literal["even", "odd"] | None

    def __init__(
        self, last_id: str = "00.00000", parity: Literal["even", "odd"] | None = None
    ) -> None:
        self.parity = parity
        self.year = time.strftime("%y")
        # Reset the counter if the year is old, otherwise set the counter to
        # just beyond its last value.
        if last_id[:2] < self.year:
            self.reset_counter()
        elif last_id[:2] == self.year:
            # Parse last_id for counter value.
            counter = self.decode(last_id[3:])
            # Increase counter so it is greater than the last counter value,
            # maintaining parity.
            is_even = counter % 2 == 0
            if (self.parity == "even" and is_even) or (
                self.parity == "odd" and not is_even
            ):
                self.counter = counter + 2
            else:
                self.counter = counter + 1
        else:
            raise ValueError("Last ID was in the future! Check your clock.")

    def new(self) -> str:
        """Generate a new experiment ID."""
        year = time.strftime("%y")
        # Reset counter on year change.
        if year != self.year:
            self.year = year
            self.reset_counter()
        counter = f"{self.encode(self.counter):0>5}"
        self.increment_counter()
        return f"{year}.{counter}"

    def increment_counter(self):
        """Increment the counter, maintaining parity."""
        if self.parity is None:
            self.counter += 1
        else:
            # Increase by two to maintain parity.
            # E.g. 1 -> 3, or 2 -> 4.
            self.counter += 2

    def reset_counter(self):
        """Reset the counter, maintaining parity."""
        if self.parity == "odd":
            self.counter = 1
        else:
            self.counter = 0

    @staticmethod
    def encode(n: int) -> str:
        """Encode an integer in the custom Base30 alphabet."""
        # Reject invalid values.
        if n < 0:
            raise ValueError("Only positive integers can be encoded.")
        base = len(exeID.alphabet)
        # Build up the result string from the least significant digit.
        result = ""
        while n > 0:
            n, remainder = divmod(n, base)
            # Prepend character onto result string.
            result = exeID.alphabet[remainder] + result
        return result

    @staticmethod
    def decode(s: str) -> int:
        """Decode an integer from the custom Base30 alphabet."""
        base = len(exeID.alphabet)
        accumulator = 0
        for order, character in enumerate(reversed(s)):
            idx = exeID.alphabet.index(character)
            accumulator += idx * base**order
        return accumulator


if __name__ == "__main__":
    import sys

    try:
        count = int(sys.argv[1])
    except (ValueError, IndexError):
        count = 1
    id_generator = exeID(last_id="25.12345")
    for _ in range(count):
        print(id_generator.new())
