import csv
import os
import time
import unittest
import uuid

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "edit_discussion_level1.csv")


class ForumEditDiscussionLevel1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.wait = WebDriverWait(cls.driver, 15)

        cls.login()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    @classmethod
    def login(cls):
        driver = cls.driver
        wait = cls.wait

        for _ in range(3):
            driver.get("https://school.moodledemo.net/login/index.php")

            try:
                username_input = wait.until(
                    EC.element_to_be_clickable((By.ID, "username"))
                )
                username_input.clear()
                username_input.send_keys("student")

                password_input = wait.until(
                    EC.element_to_be_clickable((By.ID, "password"))
                )
                password_input.clear()
                password_input.send_keys("moodle26")

                wait.until(
                    EC.element_to_be_clickable((By.ID, "loginbtn"))
                ).click()

                wait.until(EC.presence_of_element_located((By.ID, "page")))
                return
            except StaleElementReferenceException:
                continue
            except TimeoutException:
                continue

        raise TimeoutException("Login failed after retries.")

    def ensure_logged_in(self, return_url=None):
        driver = self.driver

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "user-menu-toggle"))
            )
            return
        except TimeoutException:
            self.login()
            if return_url:
                driver.get(return_url)

    def read_test_data(self):
        with open(DATA_FILE, newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file, delimiter="\t"))

    def input_tinymce_message(self, message):
        driver = self.driver
        wait = self.wait

        # Wait for TinyMCE iframe to be present.
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )

        # Set content via TinyMCE API from default content (no iframe switch needed).
        # This ensures the editor's internal state, the iframe body, and the hidden
        # textarea are all kept in sync.
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
            "var ta = document.querySelector('textarea#id_message, textarea[name=\"message\"]');"
            "if (ta) {"
            "  ta.value = arguments[0];"
            "  ta.dispatchEvent(new Event('input', {bubbles:true}));"
            "  ta.dispatchEvent(new Event('change', {bubbles:true}));"
            "}",
            content
        )
        # Small delay to let Moodle's JS pick up the change.
        time.sleep(0.5)

    def click_add_discussion(self):
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
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                return
            except TimeoutException:
                continue

        link_candidates = driver.find_elements(By.CSS_SELECTOR, "a[href*='mod/forum/post.php']")
        for link in link_candidates:
            href = link.get_attribute("href")
            if href:
                driver.get(href)
                return

        self.fail("Add discussion topic link/button not found.")

    def create_seed_discussion(self, forum_url, seed_subject, seed_message):
        driver = self.driver
        wait = self.wait

        unique_suffix = uuid.uuid4().hex[:6]
        unique_subject = f"{seed_subject} {unique_suffix}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        ).click()

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Your post was successfully added.')]")
            )
        )

        driver.get(forum_url)

        wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, unique_subject))
        ).click()

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//*[contains(normalize-space(), '{unique_subject}')]")
            )
        )

        return unique_suffix

    def open_discussion_by_subject(self, forum_url, subjects):
        driver = self.driver
        wait = self.wait

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)

        for subject in subjects:
            if not subject:
                continue

            try:
                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//a[contains(normalize-space(), '{subject}')]" )
                    )
                ).click()
                return True
            except TimeoutException:
                continue

        return False

    def wait_for_subject_text(self, subject_candidates):
        short_wait = WebDriverWait(self.driver, 10)

        for subject in subject_candidates:
            if not subject:
                continue

            # Try multiple locator strategies for the subject text.
            locators = [
                (By.XPATH, f"//*[contains(normalize-space(), '{subject}')]"),
                (By.XPATH, f"//h3[contains(normalize-space(), '{subject}')]"),
                (By.XPATH, f"//h2[contains(normalize-space(), '{subject}')]"),
                (By.XPATH, f"//a[contains(normalize-space(), '{subject}')]"),
            ]

            for locator in locators:
                try:
                    return short_wait.until(
                        EC.visibility_of_element_located(locator)
                    )
                except TimeoutException:
                    continue

        raise TimeoutException("Updated subject text not found.")

    def click_edit_discussion(self):
        wait = self.wait

        edit_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Edit"))
        )
        edit_link.click()

        wait.until(
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )

    def edit_discussion(self, updated_subject, updated_message, unique_suffix):
        driver = self.driver
        wait = self.wait

        self.click_edit_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )
        subject_input.clear()

        final_subject = updated_subject

        if updated_subject:
            final_subject = f"{updated_subject} {unique_suffix}"
            subject_input.send_keys(final_subject)

        self.input_tinymce_message(updated_message)

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        )
        submit_btn.click()

        # For the success case, wait for the edit form to disappear (page redirect).
        # For error cases the form stays, so we swallow the timeout.
        if updated_subject and updated_message:
            try:
                WebDriverWait(driver, 15).until(
                    EC.staleness_of(submit_btn)
                )
            except TimeoutException:
                pass

        return final_subject

    def verify_result(self, expected_type, expected_text, final_subject=None, forum_url=None):
        wait = self.wait

        if expected_type == "success":
            # After a successful edit, Moodle redirects to the discussion view.
            # Wait briefly for any flash/confirmation message.
            try:
                wait.until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            "//*[contains(text(), 'post was updated')"
                            " or contains(text(), 'successfully updated')"
                            " or contains(text(), 'successfully added')]"
                        )
                    )
                )
            except TimeoutException:
                pass

            # Try to find the updated subject on the current page.
            try:
                title_element = self.wait_for_subject_text([final_subject, expected_text])
            except TimeoutException:
                # Fallback: navigate to the forum list and open the discussion.
                if not forum_url:
                    raise

                opened = self.open_discussion_by_subject(
                    forum_url,
                    [final_subject, expected_text]
                )
                if not opened:
                    raise

                title_element = self.wait_for_subject_text([final_subject, expected_text])

            self.assertIn(expected_text, title_element.text)

            if final_subject:
                self.assertIn(expected_text, final_subject)

        elif expected_type == "error_subject":
            result_element = wait.until(
                EC.visibility_of_element_located((By.ID, "id_error_subject"))
            )
            self.assertIn(expected_text, result_element.text)

        elif expected_type == "error_message":
            result_element = self.wait_for_validation_message(expected_text)
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def wait_for_validation_message(self, expected_text):
        short_wait = WebDriverWait(self.driver, 10)
        locators = [
            (By.ID, "id_error_message"),
            (By.ID, "id_error_message_editor"),
            (
                By.XPATH,
                f"//*[contains(@class, 'invalid-feedback') and contains(normalize-space(), '{expected_text}')]"
            ),
            (
                By.XPATH,
                f"//*[contains(@class, 'form-control-feedback') and contains(normalize-space(), '{expected_text}')]"
            ),
        ]

        for locator in locators:
            try:
                element = short_wait.until(EC.visibility_of_element_located(locator))
                if expected_text in element.text:
                    return element
            except TimeoutException:
                continue

        return short_wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    f"//*[contains(@id, 'error') and contains(normalize-space(), '{expected_text}')]"
                )
            )
        )

    def test_edit_discussion_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                unique_suffix = self.create_seed_discussion(
                    forum_url=row["forum_url"],
                    seed_subject=row["seed_subject"],
                    seed_message=row["seed_message"]
                )

                final_subject = self.edit_discussion(
                    updated_subject=row["updated_subject"],
                    updated_message=row["updated_message"],
                    unique_suffix=unique_suffix
                )

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"],
                    final_subject=final_subject,
                    forum_url=row["forum_url"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()