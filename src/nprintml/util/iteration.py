import functools
import itertools


class PrimedIterator:

    class Sentinel:
        pass

    Empty = Sentinel()
    Missing = Sentinel()

    @classmethod
    def prime(cls, iterator, default=Missing):
        """Retrieve the first item from the given iterator and return a new
        iterator over *all* elements.

        No elements from the original iterator are missed by the returned
        iterator.

        Rather, the iterator is thereby initiated, and tested for emptiness.

        This can be a useful helper in emptiness checks (which must then
        construct this secondary iterator wrapper over the first, retrieved
        element and the remainder).

        Much the same, this is useful to operations interested in the
        first element of an iterator, (but which must also iterate over
        its entirety).

        This may also be useful in initializing complex generator functions
        (e.g. those with buffers), without retrieving more than one item
        from its stream, and maintaining its full contents.

        If a second argument, the default, is given, and the iterator is
        already empty/exhausted, then this default is returned instead of
        raising StopIteration (as with `next`).

        """
        try:
            first = next(iterator)
        except StopIteration:
            if default is not cls.Missing:
                return default

            raise

        return cls(first, iterator)

    def __init__(self, first, iterator):
        self.first = first
        self.iterator = iterator
        self.__chain__ = itertools.chain((first,), iterator)

    def __iter__(self):
        yield from self.__chain__

    def __repr__(self):
        return f'({self.__class__.__name__}: {self.iterator!r})'


prime_iterator = PrimedIterator.prime


class ResultsIterator:

    @classmethod
    def storeresults(cls, generator):
        @functools.wraps(generator)
        def wrapped(*args, **kwargs):
            iterator = generator(*args, **kwargs)
            return cls(iterator)

        return wrapped

    def __init__(self, iterator):
        self.iterator = iterator
        self.result = None

    def __iter__(self):
        self.result = yield from self.iterator


storeresults = ResultsIterator.storeresults
