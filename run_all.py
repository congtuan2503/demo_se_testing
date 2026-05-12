"""
Run all test suites in the project.
Usage: python run_all.py
"""
import unittest
import sys


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover tests from all test directories
    test_dirs = [
        "level1/F001_quiz_attempt_review",
        "level1/F003_forum_discussion",
        "level1/F005_add_course",
        "level2/F001_quiz_attempt_review",
        "level2/F003_forum_discussion",
        "level2/F005_add_course",
        "non_functional/F001_quiz_attempt_review",
        "non_functional/F003_forum_discussion",
        "non_functional/F005_add_course",
    ]

    for test_dir in test_dirs:
        discovered = loader.discover(start_dir=test_dir, pattern="test_*.py")
        suite.addTests(discovered)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
