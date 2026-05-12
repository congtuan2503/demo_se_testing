import base64
import json
import os
import time
import unittest
import uuid

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "attachment_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")


class ForumAttachmentLevel2(unittest.TestCase):

    locators = {}

    @classmethod
    def setUpClass(cls):
        with open(LOCATORS_FILE, "r", encoding="utf-8") as f:
            cls.locators = json.load(f)

        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def get_by(self, locator_key, **format_values):
        strategy, value = self.locators[locator_key]
        if format_values:
            value = value.format(**format_values)
        if strategy == "id":
            return (By.ID, value)
        elif strategy == "css selector":
            return (By.CSS_SELECTOR, value)
        elif strategy == "xpath":
            return (By.XPATH, value)
        elif strategy == "link text":
            return (By.LINK_TEXT, value)
        elif strategy == "partial link text":
            return (By.PARTIAL_LINK_TEXT, value)
        return (By.ID, value)

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url)

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE)

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
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

        driver.switch_to.frame(iframe)
        body = wait.until(EC.presence_of_element_located(self.get_by("tinymce_body")))
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

        locator_keys = [
            "add_discussion_btn",
            "add_discussion_link",
            "add_discussion_link_text",
            "add_discussion_link_text_alt",
            "add_discussion_partial",
            "add_discussion_partial_alt",
        ]

        for key in locator_keys:
            try:
                short_wait.until(EC.element_to_be_clickable(self.get_by(key))).click()
                return
            except TimeoutException:
                continue

        self.fail("Add discussion topic link/button not found.")

    def upload_image_via_tinymce(self, attachment_path):
        """Upload an image through the TinyMCE toolbar 'Image' button."""
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
            EC.element_to_be_clickable(self.get_by("image_toolbar_button"))
        )
        img_btn.click()

        # 2. Wait for the "Insert image" modal to appear.
        modal = wait.until(
            EC.visibility_of_element_located(self.get_by("image_modal"))
        )

        # 3. Find the hidden file input inside the modal, make it visible,
        #    and send the image path.
        time.sleep(1)
        file_inputs = modal.find_elements(*self.get_by("image_file_input"))
        if not file_inputs:
            # Fallback: search the entire page for file inputs in case the
            # modal content is rendered outside the modal container.
            file_inputs = driver.find_elements(*self.get_by("image_file_input"))
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
            EC.visibility_of_element_located(self.get_by("image_save_button"))
        )

        # 4b. Fill in the alternative text description (required by Moodle).
        alt_input_locator_keys = [
            "image_alt_input_description",
            "image_alt_input_alt",
            "image_alt_label_alt_text",
            "image_alt_label_description",
            "image_alt_any_text_input",
        ]

        alt_filled = False
        for key in alt_input_locator_keys:
            try:
                alt_inputs = modal.find_elements(*self.get_by(key))
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
                decorative_cb = modal.find_element(*self.get_by("decorative_checkbox"))
                if not decorative_cb.is_selected():
                    driver.execute_script("arguments[0].click();", decorative_cb)
            except Exception:
                # Last resort: try any checkbox near "Decorative" text.
                try:
                    decorative_cb = modal.find_element(
                        *self.get_by("decorative_checkbox_fallback")
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
        wait.until(EC.presence_of_element_located(self.get_by("page")))

        self.click_add_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located(self.get_by("subject_input"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(EC.element_to_be_clickable(self.get_by("submit_button"))).click()

        wait.until(
            EC.visibility_of_element_located(self.get_by("success_post_added"))
        )

        driver.get(forum_url)

        wait.until(
            EC.element_to_be_clickable(
                self.get_by("discussion_link_template", subject=unique_subject)
            )
        ).click()

        wait.until(
            EC.presence_of_element_located(
                self.get_by("text_contains_template", text=unique_subject)
            )
        )

        return unique_subject

    def create_discussion_with_attachment(self, forum_url, subject, message, attachment_path):
        driver = self.driver
        wait = self.wait

        unique_subject = f"{subject} {uuid.uuid4().hex[:6]}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located(self.get_by("page")))

        self.click_add_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located(self.get_by("subject_input"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(message)
        self.upload_image_via_tinymce(attachment_path)

        submit_btn = wait.until(EC.element_to_be_clickable(self.get_by("submit_button")))
        submit_btn.click()

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

    def reply_with_attachment(self, message, attachment_path):
        driver = self.driver
        wait = self.wait

        wait.until(EC.element_to_be_clickable(self.get_by("reply_link"))).click()

        advanced_button = wait.until(
            EC.element_to_be_clickable(self.get_by("advanced_button_fallback"))
        )
        advanced_button.click()

        wait.until(
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

        self.input_tinymce_message(message)
        self.upload_image_via_tinymce(attachment_path)

        submit_btn = wait.until(EC.element_to_be_clickable(self.get_by("submit_button")))
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
                    self.get_by("text_contains_template", text=expected_text)
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
