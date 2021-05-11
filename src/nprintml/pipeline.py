"""nprintML pipeline framework

The nprintML pipeline consists of concrete subclasses of `Step`,
serially executed by a `Pipeline`.

Steps may customize the CLI's `ArgumentParser` to ensure they receive
their required execution inputs. This is performed during construction
within the step's `__init__(parser)`.

Steps must define their executable actions, via definition of their
method `__call__(args, results)__`.

Steps may control their execution order, by specifying attribute names
of the `results` object, the values of which they require preceding
steps to determine. Required values are specified as a sequence of
attribute names at the step's class level attribute
`__requires__ = ('name0', 'name1', ...)`.

Steps may indicate the `results` attributes they will provide via class
level attribute `__provides__`, the value of which may be either a
sequence of attribute names OR a supported result class -- either a
class of type `namedtuple` or `dataclass`.

Steps may report their execution results by returning their own results
object from their `__call__`. (Generic objects and named tuples are
supported. Also consider the `dataclasses` decorator package.)

The pipeline is responsible for instantiating its steps (during its own
instantiation). Upon invocation, the pipeline returns a generator, which
invokes steps as their requirements are satisfied and merges their
results into the shared results object. Each iteration of this generator
yields a tuple consisting of the last executed step and its results (if
any).

The pipeline is itself a `set` of step instances as yet unexecuted.
Steps are removed from this set as they are invoked. The composite
results object is available as the pipeline instance attribute `results`
upon pipeline invocation.

A simple pipeline example follows:

    import argparse
    import pathlib
    import tempfile
    import typing
    import urllib.request
    from xml.etree import ElementTree as ET


    class GetDataResult(typing.NamedTuple):

        data_path: pathlib.Path


    class GetData(Step):

        __provides__ = GetDataResult

        def __init__(self, parser):
            parser.add_argument(
                '-u', '--url',
                default='https://www.lycos.com/',
                help="where's the data?",
            )

        def __call__(self, args, results):
            tempdir = tempfile.TemporaryDirectory(prefix=f'{__name__}.')
            data_path = pathlib.Path(tempdir) / 'data.html'
            urllib.request.urlretrieve(args.url, data_path)
            return GetDataResult(data_path)


    class UseDataResult(typing.NamedTuple):

        img_tags: list[ET.Element]


    class UseData(Step):

        __provides__ = UseDataResult
        __requires__ = ('data_path',)

        def __init__(self, parser):
            parser.add_argument(
                '-t', '--tag',
                default='img',
                help="tag type to extract",
            )

        def __call__(self, args, results):
            root = ET.parse(results.data_path)
            imgs = root.findall('.//img')
            return UseDataResult(imgs)


    if __name__ == '__main__':
        parser = argparse.ArgumentParser(description="scrape a web site")

        # pass base parser to Pipeline construction
        # (and thereby to Step constructors):
        pipeline = Pipeline(parser)

        args = parser.parse_args()

        # can exhaust pipeline iterator however --
        # e.g., gather step results into list or handle loop:
        for (step, result) in pipeline(args):
            print(step, result)

        # results collected on pipeline.results:
        print(pipeline.results)

In the above example, steps were automatically placed into a process-
global registry, from which the pipeline built itself by default.

In fact, any `set` may serve as a step registry, and a step may be added
to any number of registries. A step may be manually added to a registry
via `register`:

    registry = set()

    GetData.register(registry)

Alternatively, a step may be added to a custom registry upon
declaration:

    class SayHello(Step, registry=registry):

        def __call__(self, args, results):
            print('Hello')

And the pipeline may be contructed from any registry of steps:

    pipeline = Pipeline(parser, registry)

(The Step and Pipeline default registries may be overridden at the class/
metaclass level, via `__default_registry__`.)

"""
import abc
import collections
import itertools
import time
import types

from descriptors import classproperty


#: Package default registry of concrete Steps
__step_registry__ = set()


class StepMeta(abc.ABCMeta):
    """Metaclass for `Step`."""
    #
    # Note that this metaclass doesn't do much of anything that *couldn't* be
    # handled on Step, (thanks to the modern hook __init_subclass__).
    #
    # However, abc entails a custom metaclass, either implicitly or explicitly;
    # and, this allows for cleaner encapsulation of class-specific
    # functionality, and a cleaner interface (as the metaclass interface is made
    # available to the class but *not* to the instance).
    #

    #: Registry to which concrete Steps will be added by default
    __default_registry__ = __step_registry__

    def register(cls, registry):
        """Add the Step to the given registry."""
        registry.add(cls)


class Step(metaclass=StepMeta):
    """Step of a Pipeline, specifying its command-line interface,
    executive functionality, and requirements from preceding Step(s).

    Steps are added to their `__default_registry__` by default upon
    declaration. A Step may be added to an alternate registry via
    declaration argument `registry`, e.g.:

        registry = set()

        class StepOne(Step, registry=registry):

            ...

    """
    #: Sequence of data keys to be set on the results object or returned
    #: for merging into the results object OR a supported Step results
    #: class from which these may be determined.
    #: Allows Pipeline to ensure that other Steps' __requires__ are met.
    #: Sequences of keys, namedtuples and dataclasses are supported.
    __provides__ = ()

    __pre_provides__ = ()

    #: Sequence of data keys on the results object -- gathered from the
    #: execution of preceding steps -- required for this step to execute
    __requires__ = ()

    @classproperty
    def provides(cls):
        try:
            return cls.__provides__._fields
        except AttributeError:
            pass

        try:
            return cls.__provides__.__dataclass_fields__
        except AttributeError:
            pass

        return cls.__provides__

    @classmethod
    def __init_subclass__(cls, *, registry=None, **kwargs):
        """Register concrete Step upon declaration."""
        super().__init_subclass__(**kwargs)

        if getattr(cls, '__abstractmethods__', None):
            if registry is not None:
                raise TypeError(
                    f"Can't register abstract class {cls.__name__}. "
                    "To customize inherited default, override class attribute "
                    f"__default_registry__ (preferably on the metaclass {StepMeta.__name__}"
                )
        else:
            cls.register(cls.__default_registry__ if registry is None else registry)

    def __init__(self, parser):
        """Initialize Step & extend given `ArgumentParser` with Step's
        command-line interface.

        """

    def __pre__(self, parser, args, results):
        """Execute preparatory actions.

        Invoked before pipeline is run and Steps' main functionality
        (`__call__`) is invoked.

        """

    @abc.abstractmethod
    def __call__(self, args, results):
        """Step's executive functionality.

        Args:
            args: parsed argument `Namespace`
            results: pipeline execution's composite results object
                (including results collected from all preceding steps)

        Return a structured data object to report the results of Step
        execution and to share these with subsequent Steps.

        """

    def __repr__(self):
        return 'step:' + self.__class__.__name__

    @property
    def __name__(self):
        return self.__class__.__name__.lower()


class Pipeline(list):
    """Pipeline of executable Steps, instantiated from and extending an
    `ArgumentParser`, and executed upon iterative invocation.

    A `Pipeline` may instantiate any iterable of Steps. By default,
    those Steps registered under the pipeline's `__default_registry__`
    are used.

    The pipeline is itself a `list` of instantiated steps to be
    executed. Step execution order is determined upon instantiation,
    according to `Step.__provides__` and `Step.__requires__`. If step
    requirements cannot be met by a given pipeline,
    `StepRequirementError` is raised.

    Steps are removed from the pipeline collection as they are executed.

    Result objects returned by steps are merged with a composite
    pipeline result object, accessible at instance attribute `results`.

    A pipeline is executed by iterating over the result of its
    invocation -- either looping over this iterator or collecting it
    into a sequence.

    For example:

        parser = argparse.ArgumentParser(description="pipeline demo")
        pipeline = Pipeline(parser)
        args = parser.parse_args()

        # can exhaust pipeline iterator however --
        # e.g., gather step results into list or handle loop:
        for (step, result) in pipeline(args):
            print(step, result)

        # results collected on pipeline.results:
        print(pipeline.results)

    If neither iterative inspection nor collection of step results is
    desired, instance method `Pipeline.exhaust(args, results=None)`
    may be invoked rather than invoking the pipeline itself.

    For example, altering the above:

        pipeline.exhaust(args)

        print(pipeline.results)

    """
    #: Registry of Steps from which Pipeline will be constructed by default
    __default_registry__ = __step_registry__

    #: Default constructor for composite results object
    results_class = types.SimpleNamespace

    @staticmethod
    def resolve(registry):
        """Generate Steps from the given `registry` in their requisite
        order.

        Step dependencies are determined from Steps' `__provides__` and
        `__requires__`.

        """
        # input registry may be any iterable
        steps = set(registry)
        results = set(itertools.chain.from_iterable(step.__pre_provides__ for step in steps))
        run = []

        while steps:
            steps_satisfied = [step for step in steps if results.issuperset(step.__requires__)]

            if not steps_satisfied:
                raise StepRequirementError(run, steps, results)

            for step in steps_satisfied:
                results.update(step.provides)
                run.append(step)
                steps.remove(step)
                yield step

    def __init__(self, parser, registry=None):
        """Construct a Pipeline of Steps extending the given
        `ArgumentParser`.

        """
        if registry is None:
            registry = self.__default_registry__

        super().__init__(step(parser) for step in self.resolve(registry))

        self.results = None

    def __call__(self, parser, args, results=None, **kwargs):
        """Construct an iterator to execute the steps of the pipeline."""
        self.results = self.results_class() if results is None else results
        self.results.__dict__.update(kwargs)

        self.results.__timing__ = Timing()
        self.results.__timing_steps__ = {}

        with self.results.__timing__:
            # pre-pipline
            for step in self:
                step.__pre__(parser, args, self.results)

            run = []

            for step in self[:]:
                results_available = set(self.results.__dict__.keys())

                if not results_available.issuperset(step.__requires__):
                    raise StepRequirementError(run, self, results_available)

                step_timing = self.results.__timing_steps__[step] = Timing()

                with step_timing:
                    step_results = step(args, self.results)

                if step_results is not None:
                    self.merge(step_results)

                run.append(step)
                self.remove(step)

                yield (step, step_results)

    def exhaust(self, args, results=None):
        """Execute the steps of the pipeline (non-iteratively)."""
        iterator = self(args, results)
        collections.deque(iterator, maxlen=0)

    def merge(self, results):
        """Copy the attributes of the given results object into the
        pipeline's composite results.

        """
        try:
            data = results.__dict__
        except AttributeError:
            data = results._asdict()

        for (key, value) in data.items():
            if hasattr(self.results, key):
                raise KeyError('result key already defined', key)

            setattr(self.results, key, value)

    def pre_satisfy(self, *fields):
        """Remove from the pipeline those steps which provide the given
        pre-satisfied `fields` of results.

        This is a generator method, iteration of which produces the
        values of removed steps' `group_parser` attribute, for the
        purpose of updating the CLI to match (e.g. to ensure that
        arguments of ejected steps are not required).

        The pipeline is considered in reverse. Steps which provide no
        more than those fields which have been pre-satisfied are
        removed. Subsequently, fields which were required by only these
        ejected steps are considered pre-satisfied as well (by cascade).

        """
        if not fields:
            return

        satisfied = set(fields)

        for step in reversed(self):
            if satisfied.issuperset(step.provides):
                # we no longer need this step to provide what's already
                # been satisfied -- remove it
                self.remove(step)

                # without the step in the pipeline its parser interface
                # is no longer important/required -- share this with the
                # caller (rather than attempt to handle here).
                yield getattr(step, 'group_parser', None)

                # let's also pretend therefore that all of that step's
                # requirements have been satisfied -- IFF no other steps
                # have the same requirement(s)
                step_required = set(step.__requires__)
                remaining_required = itertools.chain.from_iterable(step.__requires__
                                                                   for step in self)
                cascade_satisfied = step_required.difference(remaining_required)

                satisfied.update(cascade_satisfied)


class PipelineError(Exception):
    pass


class StepRequirementError(PipelineError):

    message = "step requirements could not be satisfied"

    def __init__(self, steps_run, steps_remaining, results_available):
        super().__init__(
            self.message,
            steps_run,
            steps_remaining,
            results_available,
        )
        self.steps_run = steps_run
        self.steps_remaining = steps_remaining
        self.results_available = results_available


class Timing:

    class StaleTimer(ValueError):
        pass

    def __init__(self):
        self.t0 = self.t1 = self.proc0 = self.proc1 = None

    def start(self):
        if self.t0 is not None:
            raise self.StaleTimer

        self.t0 = time.time()
        self.proc0 = time.process_time()

    def stop(self):
        if self.t1 is not None:
            raise self.StaleTimer

        self.t1 = time.time()
        self.proc1 = time.process_time()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc_info):
        self.stop()

    @property
    def time_elapsed(self):
        if self.t0 is None or self.t1 is None:
            return None

        return self.t1 - self.t0

    @property
    def proc_elapsed(self):
        if self.proc0 is None or self.proc1 is None:
            return None

        return self.proc1 - self.proc0

    def __iter__(self):
        yield self.time_elapsed
        yield self.proc_elapsed

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self}>'

    def __str__(self):
        return (f'total time elapsed {self.time_elapsed} | '
                f'process time elapsed {self.proc_elapsed}')
