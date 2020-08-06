from downward.cached_revision import CachedRevision
from downward.experiment import _DownwardAlgorithm, FastDownwardRun, FastDownwardExperiment

import logging
import math
import os
import re

PATTERN_PROBLEM_IDX = re.compile(".*?(\d+)\.pddl")

class SkipFlag(Exception):
    pass


class _DynamicDownwardAlgorithm(_DownwardAlgorithm):
    def __init__(self, name, cached_revision, driver_options, component_options,
                 dynamic_resources=None, callbacks=None):
        _DownwardAlgorithm.__init__(self, name, cached_revision, driver_options,
                                    component_options)
        self.dynamic_resources = dynamic_resources
        self.callbacks = callbacks


class DynamicFastDownwardRun(FastDownwardRun):
    def __init__(self, exp, algo, task):
        FastDownwardRun.__init__(self,exp, algo, task)

        dynamic_resources = self.algo.dynamic_resources
        if dynamic_resources is not None:
            for entry in dynamic_resources:
                if len(entry) == 1:
                    entry = [entry[0], entry[0]]
                if len(entry) == 2:
                    entry = [x for x in entry] + [False]
                if len(entry) == 3:
                    entry = [x for x in entry] + entry[1]
                assert len(entry) == 4

                path_resource = os.path.join(
                    os.path.dirname(self.task.problem_file), entry[1])
                if os.path.exists(path_resource):
                    self.add_resource(entry[0], path_resource, entry[3],
                                      symlink=True)
                else:
                    if entry[2]:
                        raise SkipFlag("Missing %s" % entry[0])
                    else:
                        logging.critical(
                            'Resource not found: {}'.format(entry[0]))

        callback = self.algo.callbacks
        if callback is not None:
            for cb in [callback] if callable(callback) else callback:
                cb(self)


class DynamicFastDownwardExperiment(FastDownwardExperiment):

    def add_algorithm(self, name, repo, rev, component_options,
                      build_options=None, driver_options=None,
                      dynamic_resources=None, callbacks=None):
        """
        Add a Fast Downward algorithm to the experiment, i.e., a
        planner configuration in a given repository at a given
        revision.

        *name* is a string describing the algorithm (e.g.
        ``"issue123-lmcut"``).

        *repo* must be a path to a Fast Downward repository.

        *rev* must be a valid revision in the given repository (e.g.,
        ``"default"``, ``"tip"``, ``"issue123"``).

        *component_options* must be a list of strings. By default these
        options are passed to the search component. Use
        ``"--translate-options"``, ``"--preprocess-options"`` or
        ``"--search-options"`` within the component options to override
        the default for the following options, until overridden again.

        If given, *build_options* must be a list of strings. They will
        be passed to the ``build.py`` script. Options can be build names
        (e.g., ``"release32"``, ``"debug64"``), ``build.py`` options
        (e.g., ``"--debug"``) or options for Make. If *build_options* is
        omitted, the ``"release32"`` version is built.

        If given, *driver_options* must be a list of strings. They will
        be passed to the ``fast-downward.py`` script. See
        ``fast-downward.py --help`` for available options. The list is
        always prepended with ``["--validate", "--overall-time-limit",
        "30m", "--overall-memory-limit', "3584M"]``. Specifying custom
        limits overrides the default limits.

        Example experiment setup:

        >>> import os.path
        >>> exp = FastDownwardExperiment()
        >>> repo = os.environ["DOWNWARD_REPO"]

        Test iPDB in the latest revision on the default branch:

        >>> exp.add_algorithm(
        ...     "ipdb", repo, "default",
        ...     ["--search", "astar(ipdb())"])

        Test LM-Cut in an issue experiment:

        >>> exp.add_algorithm(
        ...     "issue123-v1-lmcut", repo, "issue123-v1",
        ...     ["--search", "astar(lmcut())"])

        Run blind search in debug mode:

        >>> exp.add_algorithm(
        ...     "blind", repo, "default",
        ...     ["--search", "astar(blind())"],
        ...     build_options=["--debug"],
        ...     driver_options=["--debug"])

        Run FF in 64-bit mode:

        >>> exp.add_algorithm(
        ...     "ff", repo, "default",
        ...     ["--search", "lazy_greedy([ff()])"],
        ...     build_options=["release64"],
        ...     driver_options=["--build", "release64"])

        Run LAMA-2011 with custom planner time limit:

        >>> exp.add_algorithm(
        ...     "lama", repo, "default",
        ...     [],
        ...     driver_options=[
        ...         "--alias", "seq-saq-lama-2011",
        ...         "--overall-time-limit", "5m"])

        :param dynamic_resources: None or Iterable. Entries are up to quadruple.
                                  (have to be of an iterable type):
                          (Resource Name,
                          PATH TO ADD TO PROBLEM DIR FOR RESOURCE,
                          [True, False] if resource missing, True throws an
                              SkipFlag, if False aborts,
                          Path to copy the symbolic link to). If not given as
                          triple, the defaults are (X, False, X)

        :param callback: None or Callable or Iterable of Callables.
                         Each callable is called with a DynamicFastDownwardRun
                         object which it shall modify.
        """
        if not isinstance(name, basestring):
            logging.critical('Algorithm name must be a string: {}'.format(name))
        if name in self._algorithms:
            logging.critical('Algorithm names must be unique: {}'.format(name))
        build_options = build_options or []
        driver_options = ([
            '--validate',
            '--overall-time-limit', '30m',
            '--overall-memory-limit', '3584M'] +
            (driver_options or []))
        self._algorithms[name] = _DynamicDownwardAlgorithm(
            name, CachedRevision(repo, rev, build_options),
            driver_options, component_options, dynamic_resources, callbacks)

    def _add_runs(self):
        for algo in self._algorithms.values():
            for task in self._get_tasks():
                try:
                    self.add_run(DynamicFastDownwardRun(self, algo, task))
                except SkipFlag:
                    pass
