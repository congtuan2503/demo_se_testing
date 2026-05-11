import base64
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
DATA_FILE = os.path.join(BASE_DIR, "data", "attachment_level1.csv")


class ForumAttachmentLevel1(unittest.TestCase):

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

    def ensure_sample_image_exists(self):
        image_path = os.path.join(BASE_DIR, "data", "sample_image.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)

        if os.path.exists(image_path):
            return

        png_base64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
            "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )

        with open(image_path, "wb") as file:
            file.write(base64.b64decode(png_base64))

    def input_tinymce_message(self, message):
        driver = self.driver
        wait = self.wait

        iframe = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )

        driver.switch_to.frame(iframe)
        body = wait.until(EC.presence_of_element_located((By.ID, "tinymce")))
        driver.execute_script("arguments[0].innerHTML = arguments[1];", body, message or "")
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

    def upload_image_via_tinymce(self, attachment_path):
        """Upload an image through the TinyMCE toolbar 'Image' button.

        In Moodle's inline forum form there is no filemanager attachment
        widget.  The only way to attach an image is via the TinyMCE editor's
        built-in Image button, which opens a Moodle modal dialog.

        Flow:
          1. Click the TinyMCE "Image" toolbar button.
          2. The "Insert image" modal appears with a hidden file input.
          3. Make the file input visible and send the image path.
          4. The modal changes to "Image details" showing a preview.
          5. Click "Save" to insert the image into the editor body.
        """
        driver = self.driver
        wait = self.wait

        abs_path = attachment_path
        if not os.path.isabs(abs_path):
            abs_path = os.path.join(BASE_DIR, attachment_path)
        abs_path = os.path.abspath(abs_path)

        if not os.path.exists(abs_path):
            self.fail(f"Attachment file not found: {abs_path}")

        # 1. Click the Image button in the TinyMCE toolbar.
        img_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button.tox-tbtn[aria-label="Image"]')
            )
        )
        img_btn.click()

        # 2. Wait for the "Insert image" modal to appear.
        modal = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show"))
        )

        # 3. Find the hidden file input inside the modal, make it visible,
        #    and send the image path.
        file_inputs = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not file_inputs:
            self.fail("No file input found in the Insert image modal.")

        file_input = file_inputs[0]
        driver.execute_script(
            "var el = arguments[0];"
            "el.style.display='block';"
            "el.style.visibility='visible';"
            "el.style.opacity='1';"
            "el.style.height='50px';"
            "el.style.width='200px';"
            "el.style.position='static';"
            "el.removeAttribute('hidden');",
            file_input
        )
        time.sleep(0.5)
        file_input.send_keys(abs_path)

        # 4. Wait for the modal to switch to "Image details" (shows "Save").
        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//*[contains(@class, 'modal')]"
                 "//button[normalize-space()='Save']")
            )
        )

        # 4b. Fill in the alternative text description (required by Moodle).
        alt_input_locators = [
            (By.CSS_SELECTOR, "input[aria-label*='description']"),
            (By.CSS_SELECTOR, "input[alt*='text']"),
            (By.XPATH, ".//label[contains(normalize-space(), 'Alternative text')]/following::input[1]"),
            (By.XPATH, ".//label[contains(normalize-space(), 'description')]/following::input[1]"),
            (By.XPATH, ".//input[@type='text' and not(@type='file')]"),
        ]

        alt_filled = False
        for locator in alt_input_locators:
            try:
                alt_inputs = modal.find_elements(*locator)
                for alt_input in alt_inputs:
                    if alt_input.is_displayed() and alt_input.get_attribute("type") != "file":
                        alt_input.clear()
                        alt_input.send_keys("Test image")
                        alt_filled = True
                        break
                if alt_filled:
                    break
            except Exception:
                continue

        if not alt_filled:
            # Fallback: check the "Decorative image" checkbox instead.
            try:
                decorative_cb = modal.find_element(
                    By.XPATH,
                    ".//input[@type='checkbox' and ("
                    "contains(@aria-label, 'Decorative') or "
                    "contains(@id, 'decorative') or "
                    "contains(@name, 'decorative'))]"
                )
                if not decorative_cb.is_selected():
                    driver.execute_script("arguments[0].click();", decorative_cb)
            except Exception:
                # Last resort: try any checkbox near "Decorative" text.
                try:
                    decorative_cb = modal.find_element(
                        By.XPATH,
                        ".//label[contains(normalize-space(), 'Decorative')]"
                        "/preceding-sibling::input[@type='checkbox']"
                        " | .//label[contains(normalize-space(), 'Decorative')]"
                        "/following-sibling::input[@type='checkbox']"
                        " | .//label[contains(normalize-space(), 'Decorative')]"
                        "//input[@type='checkbox']"
                    )
                    if not decorative_cb.is_selected():
                        driver.execute_script("arguments[0].click();", decorative_cb)
                except Exception:
                    pass

        time.sleep(0.3)

        # 5. Click "Save" to insert the image into the editor.
        save_btn = modal.find_element(
            By.XPATH, ".//button[normalize-space()='Save']"
        )
        save_btn.click()

        # Wait for the modal to close.
        try:
            WebDriverWait(driver, 10).until(EC.staleness_of(modal))
        except TimeoutException:
            pass

        time.sleep(0.5)

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

    def create_discussion_with_attachment(self, forum_url, subject, message, attachment_path):
        driver = self.driver
        wait = self.wait

        unique_subject = f"{subject} {uuid.uuid4().hex[:6]}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()

        subject_input = wait.until(EC.visibility_of_element_located((By.ID, "id_subject")))
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(message)
        self.upload_image_via_tinymce(attachment_path)

        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "id_submitbutton")))
        submit_btn.click()

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

    def reply_with_attachment(self, message, attachment_path):
        driver = self.driver
        wait = self.wait

        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Reply"))).click()

        advanced_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(normalize-space(), 'Advanced')]"
                    " | //input[contains(@value, 'Advanced')]"
                    " | //a[contains(normalize-space(), 'Advanced')]"
                )
            )
        )
        advanced_button.click()

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )

        self.input_tinymce_message(message)
        self.upload_image_via_tinymce(attachment_path)

        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "id_submitbutton")))
        submit_btn.click()

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

    def verify_result(self, expected_type, expected_text):
        wait = self.wait

        if expected_type == "success":
            result_element = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, f"//*[contains(normalize-space(), '{expected_text}')]")
                )
            )
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def test_attachment_data_driven(self):
        self.ensure_sample_image_exists()
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Action: {row['action']}")

            with self.subTest(test_case_id=test_case_id):
                if row["action"] == "reply_attachment":
                    self.create_seed_discussion(
                        forum_url=row["forum_url"],
                        seed_subject=row["seed_subject"],
                        seed_message=row["seed_message"]
                    )

                    self.reply_with_attachment(
                        message=row["message"],
                        attachment_path=row["attachment_path"]
                    )

                elif row["action"] == "create_attachment":
                    self.create_discussion_with_attachment(
                        forum_url=row["forum_url"],
                        subject=row["subject"],
                        message=row["message"],
                        attachment_path=row["attachment_path"]
                    )

                else:
                    self.fail(f"Unknown action: {row['action']}")

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()