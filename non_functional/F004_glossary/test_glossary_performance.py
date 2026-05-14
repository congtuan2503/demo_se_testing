import os
import time
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "performance_config.csv")


class GlossaryPerformanceTest(unittest.TestCase):
    """Non-functional performance tests for F004 Glossary.

    Testing type: Performance testing (response time measurement).
    Testing approach: Measure elapsed wall-clock time for key glossary actions
        and assert each completes within a configured threshold.
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

    def scenario_page_load(self):
        """Measure time to load the glossary page."""
        driver = self.driver
        wait = self.wait

        url = "https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL"
        
        start = time.time()
        driver.get(url)
        self.ensure_logged_in(return_url=url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))
        elapsed = time.time() - start
        return elapsed

    def scenario_add_form_load(self):
        """Measure time to click add entry and form completely loaded."""
        driver = self.driver
        wait = self.wait

        url = "https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL"
        driver.get(url)
        self.ensure_logged_in(return_url=url)

        try:
            add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add entry') or contains(text(), 'Add a new entry')]")))
            driver.execute_script("arguments[0].click();", add_btn)
        except TimeoutException:
            add_btn = driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Add a new entry')]")
            driver.execute_script("arguments[0].click();", add_btn)

        start = time.time()
        wait.until(EC.visibility_of_element_located((By.ID, "id_concept")))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")))
        elapsed = time.time() - start
        return elapsed

    def scenario_search_action(self):
        """Measure time to perform a search action."""
        driver = self.driver
        wait = self.wait

        url = "https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL"
        driver.get(url)
        self.ensure_logged_in(return_url=url)

        search_input = wait.until(EC.visibility_of_element_located((By.NAME, "hook")))
        search_input.clear()
        search_input.send_keys("Testing Performance")

        start = time.time()
        search_input.send_keys(Keys.RETURN)
        wait.until(EC.presence_of_element_located((By.ID, "page")))
        elapsed = time.time() - start
        return elapsed

    def test_glossary_performance_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            action = row["action"]
            threshold = float(row["threshold_seconds"])

            print(f"\nRunning {test_case_id} - action: {action} (threshold: {threshold}s)")

            with self.subTest(test_case_id=test_case_id):
                elapsed = -1
                if action == "page_load":
                    elapsed = self.scenario_page_load()
                elif action == "add_form_load":
                    elapsed = self.scenario_add_form_load()
                elif action == "search_action":
                    elapsed = self.scenario_search_action()
                else:
                    self.fail(f"Unknown action: {action}")

                print(f"Elapsed time: {elapsed:.2f}s")
                self.assertLessEqual(
                    elapsed,
                    threshold,
                    f"Action '{action}' took {elapsed:.2f}s, exceeding threshold {threshold}s",
                )

if __name__ == "__main__":
    unittest.main()
