"""
WSGI app to generate an experiment ID.

Usage
-----
Run via a WSGI server like Gunicorn. Control via environment variables:

PARITY
    Set to "odd" or "even" to specify generator's parity. Defaults to "any".
DATABASE_PATH
    Path to SQLite database file for storing IDs. Defaults to "identifiers.db".
"""

import json
import sqlite3
from http import HTTPStatus
from experimentid import IdentifierGenerator, Parity
from os import getenv


# Set the parity from an environment variable to support multiple servers.
match getenv("PARITY", "").lower():
    case "odd":
        parity = Parity.ODD
    case "even":
        parity = Parity.EVEN
    case _:
        parity = Parity.ANY

# Create database and initialise IdentifierGenerator
database_path = getenv("DATABASE_PATH", "identifiers.db")
db = sqlite3.connect(database_path)
id_generator = IdentifierGenerator(database=db, parity=parity)


def app(environ, start_response):
    def response(
        status: HTTPStatus, content: str = "", content_type: str = "text/plain"
    ) -> list[bytes]:
        """
        Helper function for sending a HTTP response from a WSGI script.

        Arguments
        ---------
        status: HTTPStatus
            Response status to send back.
        content: str, optional
            Response body to send back.
        content_type: str, optional
            Media type for the response content. Defaults to text/plain.
        """
        start_response(
            f"{status.value} {status.phrase}", [("Content-Type", content_type)]
        )
        return [content.encode()]

    # Handle request.
    match environ["REQUEST_METHOD"]:
        case "GET":
            # Generate and return a new ID with no attached metadata.
            new_id = id_generator.new()
            return response(HTTPStatus.OK, new_id)
        case "HEAD":
            # Return equivalent headers to a GET, but don't actually generate an ID.
            return response(HTTPStatus.OK)
        case "POST":
            # Generate and return a new ID and associate it with uploaded metadata.
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            try:
                # Returns an empty string if content_length is 0.
                content = environ["wsgi.input"].read(content_length).decode()
                # Check input is valid JSON.
                metadata = json.loads(content) if content else {}
                new_id = id_generator.new(metadata)
                return response(HTTPStatus.OK, new_id)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                # Metadata is invalid, return an error response.
                return response(
                    HTTPStatus.BAD_REQUEST,
                    "Metadata should be a UTF-8 encoded JSON object.",
                )
        case _:
            # Reject unknown REQUEST_METHODs.
            return response(
                HTTPStatus.NOT_IMPLEMENTED,
                "Only GET, HEAD, and POST requests are supported.",
            )
