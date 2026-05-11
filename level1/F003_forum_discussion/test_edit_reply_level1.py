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
DATA_FILE = os.path.join(BASE_DIR, "data", "edit_reply_level1.csv")


class ForumEditReplyLevel1(unittest.TestCase):

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
                username_input = wait.until(EC.element_to_be_clickable((By.ID, "username")))
                username_input.clear()
                username_input.send_keys("student")

                password_input = wait.until(EC.element_to_be_clickable((By.ID, "password")))
                password_input.clear()
                password_input.send_keys("moodle26")

                wait.until(EC.element_to_be_clickable((By.ID, "loginbtn"))).click()
                wait.until(EC.presence_of_element_located((By.ID, "page")))
                return

            except (TimeoutException, StaleElementReferenceException):
                continue

        raise TimeoutException("Login failed after retries.")

    def ensure_logged_in(self, return_url=None):
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "user-menu-toggle"))
            )
            return
        except TimeoutException:
            self.login()
            if return_url:
                self.driver.get(return_url)

    def read_test_data(self):
        with open(DATA_FILE, newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file, delimiter="\t"))

    def input_tinymce_message(self, message):
        driver = self.driver
        wait = self.wait

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )

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

        subject_input = wait.until(EC.visibility_of_element_located((By.ID, "id_subject")))
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(EC.element_to_be_clickable((By.ID, "id_submitbutton"))).click()

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

        return unique_subject

    def click_reply(self):
        self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Reply"))
        ).click()

    def submit_inline_reply(self, reply_message):
        driver = self.driver
        wait = self.wait

        textarea = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[name='post']"))
        )

        textarea.clear()
        textarea.send_keys(reply_message)

        form = textarea.find_element(By.XPATH, "./ancestor::form")

        submit_button = form.find_element(
            By.XPATH,
            ".//button[contains(normalize-space(), 'Post to forum') or contains(@class, 'btn-primary')]"
        )

        driver.execute_script("arguments[0].click();", submit_button)

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, f"//*[contains(normalize-space(), '{reply_message}')]")
            )
        )

    def create_seed_reply(self, original_reply):
        self.click_reply()
        self.submit_inline_reply(original_reply)
        time.sleep(1)

    def click_edit_for_reply(self, original_reply):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        # Find the post that contains the reply text, then click its own Edit link.
        # Try several ancestor class names that Moodle uses across versions.
        post_ancestor_classes = [
            "forumpost",
            "forum-post-container",
            "post-content-container",
            "post",
        ]

        for cls in post_ancestor_classes:
            locator = (
                By.XPATH,
                f"//*[contains(normalize-space(), '{original_reply}')]"
                f"/ancestor::*[contains(@class, '{cls}')]"
                "[1]//a[normalize-space()='Edit']"
            )
            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                short_wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")
                    )
                )
                return
            except TimeoutException:
                continue

        # Fallback: the reply is the most recent post, so its Edit link is the
        # last one on the page.
        edit_links = driver.find_elements(By.LINK_TEXT, "Edit")
        if not edit_links:
            self.fail("Edit link for reply not found.")
        edit_links[-1].click()

        short_wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe.tox-edit-area__iframe")
            )
        )

    def edit_reply(self, original_reply, updated_reply):
        driver = self.driver
        wait = self.wait

        self.click_edit_for_reply(original_reply)

        self.input_tinymce_message(updated_reply)

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        )
        submit_btn.click()

        if updated_reply:
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
            except TimeoutException:
                pass

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
            (
                By.XPATH,
                f"//*[contains(@id, 'error') and contains(normalize-space(), '{expected_text}')]"
            ),
        ]

        for locator in locators:
            try:
                element = short_wait.until(EC.visibility_of_element_located(locator))
                if expected_text in element.text:
                    return element
            except TimeoutException:
                continue

        raise TimeoutException("Validation message not found.")

    def verify_result(self, expected_type, expected_text):
        wait = self.wait

        if expected_type == "success":
            result_element = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, f"//*[contains(normalize-space(), '{expected_text}')]")
                )
            )
            self.assertIn(expected_text, result_element.text)

        elif expected_type == "error_message":
            result_element = self.wait_for_validation_message(expected_text)
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def test_edit_reply_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                self.create_seed_discussion(
                    forum_url=row["forum_url"],
                    seed_subject=row["seed_subject"],
                    seed_message=row["seed_message"]
                )

                self.create_seed_reply(
                    original_reply=row["original_reply"]
                )

                self.edit_reply(
                    original_reply=row["original_reply"],
                    updated_reply=row["updated_reply"]
                )

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()