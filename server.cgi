#!/usr/bin/env python3

"""CGI script to generate an experiment ID."""

import json
from os import getenv
import sqlite3
import sys
from http import HTTPStatus

from experimentid import IdentifierGenerator


def response(status: HTTPStatus, content: str = "", content_type: str = "text/plain"):
    """
    Helper function for sending a HTTP response from a CGI script.

    Arguments
    ---------
    status: HTTPStatus
        Response status to send back.
    content: str, optional
        Response body to send back.
    content_type: str, optional
        Media type for the response content. Defaults to text/plain.
    """
    sys.stdout.write(
        # Headers.
        f"Status: {status.value} {status.phrase}\n"
        f"Content-Type: {content_type}\n"
        # Body.
        f"\n{content}"
    )


# Create database and initialise IdentifierGenerator
db = sqlite3.connect("identifiers.db")
id_generator = IdentifierGenerator(database=db)

# Handle request.
match getenv("REQUEST_METHOD"):
    case "GET":
        # Generate and return a new ID with no attached metadata.
        new_id = id_generator.new()
        response(HTTPStatus.OK, new_id)
    case "HEAD":
        # Return equivalent headers to a GET, but don't actually generate an ID.
        response(HTTPStatus.OK)
    case "POST":
        # Generate and return a new ID and associate it with uploaded metadata.
        content_length = int(getenv("CONTENT_LENGTH", 0))
        try:
            # Returns an empty string if content_length is 0.
            content = sys.stdin.buffer.read(content_length).decode()
            # Check input is valid JSON.
            metadata = json.loads(content) if content else {}
            new_id = id_generator.new(metadata)
            response(HTTPStatus.OK, new_id)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            # Metadata is invalid, return an error response.
            response(
                HTTPStatus.BAD_REQUEST,
                "Metadata should be a UTF-8 encoded JSON object.",
            )
    case _:
        # Reject unknown REQUEST_METHODs.
        response(
            HTTPStatus.NOT_IMPLEMENTED,
            "Only GET, HEAD, and POST requests are supported.",
        )
