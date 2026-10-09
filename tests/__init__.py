"""Wiretight test suite.

This package marker exists so ``tests.conftest`` and ``tests.unit.test_x``
resolve to the *same* module objects under pytest's default import mode.
Without it, ``conftest.py`` is imported as top-level ``conftest`` and a test
doing ``from tests.conftest import SocketBlocked`` gets a *different* class
object than the one the fixture raises — which makes the exception uncatchable.
"""
