import unittest

from cirunner.gha import GHAToolAnalyzer


class TestingGHAAnalyzer(unittest.TestCase):

        def test_gha_analyze(self):
            gha = GHAToolAnalyzer()
            gha.analyze()