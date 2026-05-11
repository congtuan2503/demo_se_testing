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
DATA_FILE = os.path.join(BASE_DIR, "data", "delete_reply_level1.csv")


class ForumDeleteReplyLevel1(unittest.TestCase):

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

        iframe = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )

        # Set content via the iframe body first (works even if TinyMCE API
        # hasn't fully initialised yet).
        driver.switch_to.frame(iframe)
        body = wait.until(EC.presence_of_element_located((By.ID, "tinymce")))
        driver.execute_script("arguments[0].innerHTML = arguments[1];", body, message or "")
        driver.switch_to.default_content()

        # Then sync through the TinyMCE API + hidden textarea so Moodle's
        # form validation sees the value.
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

        unique_subject = f"{seed_subject} {uuid.uuid4().hex[:6]}"

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

    def create_seed_reply(self, reply_message):
        self.click_reply()
        self.submit_inline_reply(reply_message)
        time.sleep(1)

    def click_delete_for_reply(self, reply_message):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        post_ancestor_classes = [
            "forumpost",
            "forum-post-container",
            "post-content-container",
            "post",
        ]

        for cls in post_ancestor_classes:
            locator = (
                By.XPATH,
                f"//*[contains(normalize-space(), '{reply_message}')]"
                f"/ancestor::*[contains(@class, '{cls}')]"
                "[1]//a[normalize-space()='Delete']"
            )

            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                return
            except TimeoutException:
                continue

        # Fallback: the reply is usually the newest post, so its Delete link is
        # usually the last Delete link on the page.
        delete_links = driver.find_elements(By.LINK_TEXT, "Delete")
        if not delete_links:
            self.fail("Delete link for reply not found.")

        delete_links[-1].click()

    def confirm_delete(self):
        driver = self.driver
        wait = self.wait

        confirm_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(normalize-space(), 'Continue')]"
                    " | //input[@type='submit' and contains(@value, 'Continue')]"
                    " | //button[contains(normalize-space(), 'Delete')]"
                    " | //input[@type='submit' and contains(@value, 'Delete')]"
                    " | //button[contains(normalize-space(), 'Yes')]"
                    " | //input[@type='submit' and contains(@value, 'Yes')]"
                )
            )
        )

        confirm_btn.click()

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(confirm_btn))
        except TimeoutException:
            pass

    def delete_reply(self, reply_message):
        self.click_delete_for_reply(reply_message)
        self.confirm_delete()

    def verify_reply_deleted(self, reply_message):
        driver = self.driver
        wait = self.wait

        wait.until(EC.presence_of_element_located((By.ID, "page")))
        time.sleep(1)

        matching_elements = driver.find_elements(
            By.XPATH,
            f"//*[contains(normalize-space(), '{reply_message}')]"
        )

        self.assertEqual(
            len(matching_elements),
            0,
            f"Reply was not deleted. Still found: {reply_message}"
        )

    def test_delete_reply_data_driven(self):
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
                    reply_message=row["reply_message"]
                )

                self.delete_reply(
                    reply_message=row["reply_message"]
                )

                self.verify_reply_deleted(
                    reply_message=row["reply_message"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()