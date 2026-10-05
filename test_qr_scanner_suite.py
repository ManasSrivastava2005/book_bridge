"""Safe regression entry point: isolated fixtures, no live seeding or demo passwords.

The former script mutated the working database. UI/server smoke checks are
recorded separately in LIBRARIAN_COMPLETION_REPORT.md.
"""
import unittest

def load_tests(loader, tests, pattern):
    return loader.loadTestsFromNames(['test_qr_management'])

if __name__ == '__main__':
    unittest.main()
