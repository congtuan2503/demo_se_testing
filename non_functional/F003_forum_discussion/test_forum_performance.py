import os
import time
import unittest
import uuid

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "performance_config.csv")


class ForumPerformanceTest(unittest.TestCase):
    """Non-functional performance tests for F003 Forum Discussion.

    Testing type: Performance testing (response time measurement).
    Testing approach: Measure elapsed wall-clock time for key forum actions
        and assert each completes within a configured threshold.
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

    def input_tinymce_message(self, message):
        """Two-layer TinyMCE input: iframe innerHTML first, then API sync.

        Copied from test_attachment_level1.py — the most robust variant.
        """
        driver = self.driver
        wait = self.wait

        iframe = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")
            )
        )

        driver.switch_to.frame(iframe)
        body = wait.until(EC.presence_of_element_located((By.ID, "tinymce")))
        driver.execute_script(
            "arguments[0].innerHTML = arguments[1];", body, message or ""
        )
        driver.switch_to.default_content()

        content = message or ""
        driver.execute_script(
            "if (window.tinymce && tinymce.activeEditor) {"
            "  var editor = tinymce.activeEditor;"
            "  editor.setContent(arguments[0]);"
            "  editor.fire('change');"
            "  editor.save();"
            "}"
            "if (window.tinymce && tinymce.triggerSave) {"
            "  tinymce.triggerSave();"
            "}"
            "var ta = document.querySelector("
            "'textarea#id_message, textarea[name=\"message\"]');"
            "if (ta) {"
            "  ta.value = arguments[0];"
            "  ta.dispatchEvent(new Event('input', {bubbles:true}));"
            "  ta.dispatchEvent(new Event('change', {bubbles:true}));"
            "}",
            content,
        )
        time.sleep(0.5)

    # ------------------------------------------------------------------
    # Scenario methods
    # ------------------------------------------------------------------

    def scenario_forum_page_load(self, forum_url):
        """Measure time to load the forum page until #page is present."""
        driver = self.driver
        wait = self.wait

        start = time.time()
        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))
        elapsed = time.time() - start
        return elapsed

    def scenario_add_discussion_form_load(self, forum_url):
        """Measure time from forum page to Add discussion form fully loaded."""
        driver = self.driver
        wait = self.wait

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()
        start = time.time()
        wait.until(EC.visibility_of_element_located((By.ID, "id_subject")))
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")
            )
        )
        elapsed = time.time() - start
        return elapsed

    def scenario_validation_error_display(self, forum_url):
        """Measure time from empty-form submit to validation error display."""
        driver = self.driver
        wait = self.wait

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()
        wait.until(EC.visibility_of_element_located((By.ID, "id_subject")))

        # Leave subject empty, leave TinyMCE empty, click submit.
        start = time.time()
        wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        ).click()
        wait.until(
            EC.visibility_of_element_located((By.ID, "id_error_subject"))
        )
        elapsed = time.time() - start
        return elapsed

    def scenario_create_discussion_submit(self, forum_url):
        """Measure time from submit to success message for a real post."""
        driver = self.driver
        wait = self.wait

        unique_subject = f"NF-PERF Discussion {uuid.uuid4().hex[:6]}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(
            "Performance test message for non-functional testing."
        )

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        )

        start = time.time()
        submit_btn.click()

        # Wait for success confirmation or page redirect.
        try:
            wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(text(), 'Your post was successfully added.')]",
                    )
                )
            )
        except TimeoutException:
            # The page may have already redirected past the flash message.
            pass

        elapsed = time.time() - start
        return elapsed

    # ------------------------------------------------------------------
    # Data-driven test method
    # ------------------------------------------------------------------

    def test_forum_performance_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            scenario = row["scenario"]
            threshold = float(row["threshold_seconds"])
            forum_url = row["forum_url"]

            print(f"\nRunning {test_case_id} - scenario: {scenario}")

            with self.subTest(test_case_id=test_case_id):
                if scenario == "forum_page_load":
                    elapsed = self.scenario_forum_page_load(forum_url)

                elif scenario == "add_discussion_form_load":
                    elapsed = self.scenario_add_discussion_form_load(forum_url)

                elif scenario == "validation_error_display":
                    elapsed = self.scenario_validation_error_display(forum_url)

                elif scenario == "create_discussion_submit":
                    elapsed = self.scenario_create_discussion_submit(forum_url)

                else:
                    self.fail(f"Unknown scenario: {scenario}")

                self.assertLessEqual(
                    elapsed,
                    threshold,
                    f"{test_case_id} took {elapsed:.2f}s, "
                    f"exceeding threshold of {threshold:.2f}s",
                )

                print(
                    f"PASSED {test_case_id} - "
                    f"actual: {elapsed:.2f}s  threshold: {threshold:.2f}s"
                )


if __name__ == "__main__":
    unittest.main()
