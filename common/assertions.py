import unittest

class Assertions:
    @staticmethod
    def assert_element_text(element, expected_text, test_case: unittest.TestCase):
        test_case.assertIn(expected_text, element.text)

    @staticmethod
    def assert_element_displayed(element, test_case: unittest.TestCase):
        test_case.assertTrue(element.is_displayed(), "Element should be displayed")
