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
DATA_FILE = os.path.join(BASE_DIR, "data", "responsive_config.csv")


class GlossaryResponsiveTest(unittest.TestCase):
    """Non-functional responsive/compatibility tests for F004 Glossary.

    Testing type: Responsive / compatibility testing.
    Testing approach: Set the browser to specific viewport sizes (desktop,
        tablet, mobile) and verify the glossary UI is
        reachable and usable at each size.
    Testing tool: Python Selenium WebDriver with unittest.
    """

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url, username="student", password="moodle26")

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE, delimiter=",")

    def verify_add_entry_btn(self):
        short_wait = WebDriverWait(self.driver, 5)
        try:
            return short_wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Add entry') or contains(text(), 'Add a new entry')]")))
        except TimeoutException:
            return short_wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='submit' and contains(@value, 'Add a new entry')]")))

    def verify_search_input(self):
        short_wait = WebDriverWait(self.driver, 5)
        return short_wait.until(EC.presence_of_element_located((By.NAME, "hook")))

    def test_glossary_responsive_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            viewport_name = row["viewport_name"]
            width = int(row["width"])
            height = int(row["height"])
            expected_elements = row["expected_elements"].split(",")

            url = "https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL"

            print(f"\nRunning {test_case_id} - viewport: {viewport_name} {width}x{height}")

            with self.subTest(test_case_id=test_case_id):
                driver = self.driver
                driver.set_window_size(width, height)
                
                driver.get(url)
                self.ensure_logged_in(return_url=url)
                self.wait.until(EC.presence_of_element_located((By.ID, "page")))

                for element in expected_elements:
                    if element == "add_entry_btn":
                        found = self.verify_add_entry_btn()
                        self.assertIsNotNone(found)
                    elif element == "search_input":
                        found = self.verify_search_input()
                        self.assertIsNotNone(found)
                    else:
                        self.fail(f"Unknown expected element: {element}")

                print(f"PASSED {test_case_id} for viewport {viewport_name}")

if __name__ == "__main__":
    unittest.main()
