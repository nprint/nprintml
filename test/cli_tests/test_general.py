import nprintml

from .base import CLITestCase


class TestGeneral(CLITestCase):

    def test_error(self):
        result = self.try_execute('--yelp', raise_exc=False, stderr=True)
        self.assertEqual(result.code, 2)
        self.assertGreater(len(result.stderr), 0)

    def test_help(self):
        result = self.try_execute('--help', stdout=True)
        self.assertGreater(len(result.stdout), 0)

    def test_version(self):
        result = self.try_execute('--version', stdout=True)
        self.assertIn(f'nprintML {nprintml.__version__} | nPrint {nprintml.__nprint_version__}',
                      result.stdout)
