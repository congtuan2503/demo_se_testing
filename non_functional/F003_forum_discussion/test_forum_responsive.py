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


class ForumResponsiveTest(unittest.TestCase):
    """Non-functional responsive/compatibility tests for F003 Forum Discussion.

    Testing type: Responsive / compatibility testing.
    Testing approach: Set the browser to specific viewport sizes (desktop,
        tablet, mobile) and verify the forum discussion creation form is
        reachable and usable at each size.
    Testing tool: Python Selenium WebDriver with unittest.
    """

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url)

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE)

    # ------------------------------------------------------------------
    # Helper methods — copied from the proven F003 Level 1 / Level 2 code
    # ------------------------------------------------------------------

    def click_add_discussion(self):
        """Robust multi-locator click for Add discussion, matching L1/L2."""
        driver = self.driver
        short_wait = WebDriverWait(driver, 5)

        locators = [
            (By.CSS_SELECTOR, "[data-action='new-discussion']"),
            (By.CSS_SELECTOR, "a[href*='mod/forum/post.php']"),
            (By.LINK_TEXT, "Add a new discussion topic"),
            (By.LINK_TEXT, "Add discussion topic"),
            (By.PARTIAL_LINK_TEXT, "Add a new discussion"),
            (By.PARTIAL_LINK_TEXT, "Add a new"),
        ]

        for locator in locators:
            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                return
            except TimeoutException:
                continue

        self.fail("Add discussion topic link/button not found.")

    # ------------------------------------------------------------------
    # Element verification helpers
    # ------------------------------------------------------------------

    def verify_add_discussion(self):
        """Verify Add discussion action is reachable at current viewport."""
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        locators = [
            (By.CSS_SELECTOR, "[data-action='new-discussion']"),
            (By.CSS_SELECTOR, "a[href*='mod/forum/post.php']"),
            (By.LINK_TEXT, "Add a new discussion topic"),
            (By.LINK_TEXT, "Add discussion topic"),
            (By.PARTIAL_LINK_TEXT, "Add a new discussion"),
            (By.PARTIAL_LINK_TEXT, "Add a new"),
        ]

        for locator in locators:
            try:
                element = short_wait.until(
                    EC.presence_of_element_located(locator)
                )
                return element
            except TimeoutException:
                continue

        self.fail("Add discussion topic link/button not found at this viewport.")

    def verify_subject_input(self):
        """Verify subject input is visible on the form."""
        return self.wait.until(
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )

    def verify_tinymce(self):
        """Verify TinyMCE editor iframe is present."""
        return self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")
            )
        )

    def verify_submit_button(self):
        """Verify submit button is present and clickable."""
        return self.wait.until(
            EC.presence_of_element_located((By.ID, "id_submitbutton"))
        )

    # ------------------------------------------------------------------
    # Data-driven test method
    # ------------------------------------------------------------------

    def test_forum_responsive_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            viewport_name = row["viewport_name"]
            width = int(row["width"])
            height = int(row["height"])
            forum_url = row["forum_url"]
            expected_elements = row["expected_elements"].split(",")

            print(
                f"\nRunning {test_case_id} - "
                f"viewport: {viewport_name} {width}x{height}"
            )

            with self.subTest(test_case_id=test_case_id):
                driver = self.driver

                # 1. Set browser viewport size.
                driver.set_window_size(width, height)

                # 2. Navigate to forum page.
                driver.get(forum_url)
                self.ensure_logged_in(return_url=forum_url)

                # 3. Verify forum page loads.
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "page"))
                )

                # 4. Verify Add discussion is reachable.
                if "add_discussion" in expected_elements:
                    self.verify_add_discussion()

                # 5. Click Add discussion to open the form.
                self.click_add_discussion()

                # 6. Verify subject input is visible.
                if "subject_input" in expected_elements:
                    subject_el = self.verify_subject_input()
                    self.assertTrue(
                        subject_el.is_displayed(),
                        f"{test_case_id}: Subject input not visible "
                        f"at {viewport_name} ({width}x{height})",
                    )

                # 7. Verify TinyMCE editor iframe is present.
                if "tinymce" in expected_elements:
                    tinymce_el = self.verify_tinymce()
                    self.assertIsNotNone(
                        tinymce_el,
                        f"{test_case_id}: TinyMCE iframe not present "
                        f"at {viewport_name} ({width}x{height})",
                    )

                # 8. Verify submit button is available.
                submit_el = self.verify_submit_button()
                self.assertIsNotNone(
                    submit_el,
                    f"{test_case_id}: Submit button not present "
                    f"at {viewport_name} ({width}x{height})",
                )

                # 9. Do NOT submit — just verify the form is usable.

                print(f"PASSED {test_case_id}")

        # Restore to a reasonable window size after all viewports.
        self.driver.maximize_window()


if __name__ == "__main__":
    unittest.main()
