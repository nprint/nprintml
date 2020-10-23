import unittest

from nprintml import cli


class CLITestCase(unittest.TestCase):

    class CommandError(Exception):
        pass

    def try_execute(self, *argv):
        try:
            cli.execute(argv)
        except SystemExit as exc:
            if exc.code > 0:
                raise self.CommandError(exc.code) from exc


class TestDemo(CLITestCase):

    def test_demo_help(self):
        self.try_execute('--help')

    def test_demo_yelp(self):
        with self.assertRaises(self.CommandError) as context:
            self.try_execute('--yelp')

        self.assertEqual(context.exception.args, (2,))
