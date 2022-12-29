"""Provides utility methods for reading a stream of JSON values."""

from typing import Any, Generic, Iterator, TextIO, TypeVar

import ijson
import ijson.common

E = TypeVar("E")


class CountingIterator(Generic[E]):
    """Wraps an iterator to keep track of how many items have been sent."""

    num_sent: int
    wrapped: Iterator[E]

    def __init__(self, wrapped: Iterator[E]):
        """Creates a counting wrapper around the given iterator, starting with a count of 0."""
        self.num_sent = 0
        self.wrapped = wrapped

    def _send(self, item: E) -> E:
        """Returns the argument unchanged.

        Note:
            Side effect: increments the count of items sent
        """
        self.num_sent += 1
        return item

    def __iter__(self) -> Iterator[E]:
        """Returns an iterator that yields the values of our wrapped iterator.

        Note:
            `map` is fully lazy - it will only call `_send` at the moment a consumer of
            this iterator needs a value, so `num_sent` will always equal the actual number
            of items yielded.
        """
        return map(self._send, self.wrapped)


IJSON_PREMATURE_EOF = "parse error: premature EOF"


def get_json_objects(text_stream: TextIO) -> Iterator[Any]:
    """Reads the given text_stream and yields each top-level JSON element."""
    # parse gets us a stream of events
    # ex: [(prefix='', type='start_map'), (prefix='', type='map_key', value='row#'),
    #      (prefix='row#', type='number', value=2), ...]
    # multiple_values tells the parser that more than one element @ prefix='' is okay
    events = CountingIterator(ijson.parse(text_stream, multiple_values=True))
    try:
        # items takes an event stream and prefix, then accumulates the events under
        # that prefix into the Python type it corresponds to
        # (one of dict, list, float, bool, str, None)
        for record in ijson.items(events, ""):
            yield record
    except ijson.IncompleteJSONError as exc:
        if events.num_sent == 0:
            # We don't want to throw an error for an input which is empty or all
            # whitespace. Unfortunately the error class is the same for invalid JSON
            # and unexpected end of stream, so we can only differentiate via the message.
            if len(exc.args) >= 1 and isinstance(exc.args[0], str) and exc.args[0].startswith(IJSON_PREMATURE_EOF):
                return
        raise
