"""
test_cutoff_submission_level1.py - Level 1 Data-Driven Tests for Cutoff / Overdue

Tests covered (CSV columns: Test ID, Assignment URL, Expected Result):
    TC-002-011: Assignment is overdue  (student / moodle26)

Navigates to an assignment past its due/cutoff date and verifies the
overdue status message is displayed.
"""

import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "cutoff_submission_level1.csv")


class AssignmentCutoffSubmissionLevel1(unittest.TestCase):

    _current_user = None

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        cls._current_user = None

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ---- Credential management ------------------------------------------

    @staticmethod
    def _get_credentials(test_id):
        tc_num = int(test_id.strip().split("-")[-1])
        if 7 <= tc_num <= 9:
            return "ericwebb", "moodle"
        return "student", "moodle26"

    def _switch_user_if_needed(self, test_id):
        username, password = self._get_credentials(test_id)
        if self.__class__._current_user == username:
            return
        self.driver.delete_all_cookies()
        LoginHelper.login(self.driver, username=username, password=password)
        self.__class__._current_user = username
        print(f"    [Auth] Logged in as: {username}")

    # ---- Navigation -----------------------------------------------------

    def _navigate(self, url):
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

    # ---- Verification ---------------------------------------------------

    def _verify(self, expected, test_id):
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))
        page = self.driver.page_source
        self.assertTrue(
            expected.lower() in page.lower(),
            f"{test_id}: Expected '{expected}' not found on page.",
        )

    # ---- Main data-driven test ------------------------------------------

    def test_cutoff_submission_data_driven(self):
        test_data = CSVReader.read_data(DATA_FILE, delimiter=",")

        for row in test_data:
            test_id = row["Test ID"].strip()
            assignment_url = row["Assignment URL"].strip()
            expected = row["Expected Result"].strip()

            print(f"\nRunning {test_id} - Cutoff / Overdue check")

            with self.subTest(test_id=test_id):
                # 1. Switch user if needed.
                self._switch_user_if_needed(test_id)

                # 2. Navigate directly to the assignment page.
                self._navigate(assignment_url)

                # 3. Verify the overdue / cutoff message on the page.
                page_text = self.driver.page_source.lower()
                self.assertTrue(
                    expected.lower() in page_text or "overdue" in page_text or "cut-off" in page_text,
                    f"{test_id}: Expected overdue message not found."
                )

                print(f"PASSED {test_id}")


if __name__ == "__main__":
    unittest.main()
