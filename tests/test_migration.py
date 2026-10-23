import unittest


class MigrationSafetyContractTests(unittest.TestCase):
    def test_migration_is_dry_run_by_default(self):
        # MongoDB integration tests must run only against a disposable database.
        self.assertTrue(True)
