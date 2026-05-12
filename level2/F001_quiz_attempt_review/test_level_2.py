import csv
import json
import logging
import os
import traceback
import unittest

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Level2DataDrivenTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """
        Đọc cấu hình URL và Locators 1 lần từ file locators.json.
        """
        config_path = os.path.join(os.path.dirname(__file__), "data", "locators.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cls.config = json.load(f)
        except FileNotFoundError:
            raise Exception(f"Không tìm thấy file cấu hình tại {config_path}")
            
        cls.BASE_URL = cls.config.get("base_url")
        cls.locators_config = cls.config.get("locators", {})

        cls.BY_MAP = {
            "ID": By.ID,
            "XPATH": By.XPATH,
            "CSS_SELECTOR": By.CSS_SELECTOR,
            "LINK_TEXT": By.LINK_TEXT,
            "PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT,
            "NAME": By.NAME,
            "CLASS_NAME": By.CLASS_NAME,
            "TAG_NAME": By.TAG_NAME
        }

    def setUp(self):
        self.driver = None
        self.wait = None
        self.errors = []

        # Thư mục lưu ảnh khi fail
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # Khởi tạo locator động từ cấu hình
        self.loc_login_link = self._get_locator("login_link")
        self.loc_input_username = self._get_locator("input_username")
        self.loc_input_password = self._get_locator("input_password")
        self.loc_btn_login = self._get_locator("btn_login")
        self.loc_link_my_courses = self._get_locator("link_my_courses")
        self.loc_link_course = self._get_locator("link_course")
        self.loc_link_quiz = self._get_locator("link_quiz")
        self.loc_btn_attempt_quiz = self._get_locator("btn_attempt_quiz")
        self.loc_inputs_quiz = self._get_locator("inputs_quiz")
        self.loc_btn_next = self._get_locator("btn_next")
        self.loc_finish_attempt = self._get_locator("finish_attempt")
        self.loc_btn_submit_all = self._get_locator("btn_submit_all")
        self.loc_btn_submit_cancel = self._get_locator("btn_submit_cancel")
        self.loc_btn_submit_confirm = self._get_locator("btn_submit_confirm")
        self.loc_btn_finish_review = self._get_locator("btn_finish_review")
        self.loc_modal_dialog = self._get_locator("modal_dialog")
        self.loc_body = self._get_locator("body")
        self.loc_user_menu = self._get_locator("user_menu")
        self.loc_link_logout = self._get_locator("link_logout")

    def tearDown(self):
        self._stop_driver()

    # ===== Helper functions cho Level 2 =====
    def _get_locator(self, locator_key):
        loc_data = self.locators_config.get(locator_key)
        if not loc_data:
            raise KeyError(f"Locator '{locator_key}' không tồn tại trong locators.json")
        
        by_type_str = loc_data.get("by").upper()
        value = loc_data.get("value")
        
        by_type = self.BY_MAP.get(by_type_str)
        if not by_type:
            raise ValueError(f"Loại Locator '{by_type_str}' không được hỗ trợ.")
            
        return (by_type, value)

    # ===== Browser helpers =====
    def _start_driver(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)

    def _stop_driver(self):
        if self.driver:
            self.driver.quit()
        self.driver = None
        self.wait = None

    def _wait_click(self, locator):
        element = self.wait.until(EC.element_to_be_clickable(locator))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        try:
            element.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            element = self.wait.until(EC.element_to_be_clickable(locator))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.driver.execute_script("arguments[0].click();", element)

    def _wait_send_keys(self, locator, text):
        element = self.wait.until(EC.visibility_of_element_located(locator))
        element.clear()
        element.send_keys(text)

    def _try_click(self, locator, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(locator)).click()
            return True
        except TimeoutException:
            return False

    def _get_body_text(self):
        return self.wait.until(EC.presence_of_element_located(self.loc_body)).text

    def _save_screenshot(self, test_id):
        if not self.driver:
            return
        file_name = f"{test_id}_fail.png"
        file_path = os.path.join(self.screenshot_dir, file_name)
        self.driver.save_screenshot(file_path)
        logging.info(f"Đã lưu screenshot lỗi tại: {file_path}")

    # ===== Flow steps =====
    def _login(self, username, password):
        self.driver.get(self.BASE_URL)
        self._wait_click(self.loc_login_link)
        self._wait_send_keys(self.loc_input_username, username)
        self._wait_send_keys(self.loc_input_password, password)
        self._wait_click(self.loc_btn_login)

    def _open_course_and_quiz(self):
        self._try_click(self.loc_link_my_courses, timeout=5)
        self._wait_click(self.loc_link_course)
        self._wait_click(self.loc_link_quiz)
        self._wait_click(self.loc_btn_attempt_quiz)

    def _fill_answers(self, input_answer):
        if not input_answer or not input_answer.strip():
            return

        answers = [part.strip() for part in input_answer.split(",") if part.strip()]
        inputs = self.wait.until(EC.presence_of_all_elements_located(self.loc_inputs_quiz))

        for index, answer in enumerate(answers):
            if index >= len(inputs):
                break
            inputs[index].clear()
            inputs[index].send_keys(answer)

    def _collect_expected_parts(self, expected_text):
        if not expected_text:
            return []
        return [part.strip() for part in expected_text.split(",") if part.strip()]

    def _verify_expected_parts(self, expected_text, seen_texts, label):
        parts = self._collect_expected_parts(expected_text)
        if not parts:
            return

        remaining = set(parts)
        for text in seen_texts:
            remaining = {item for item in remaining if item not in text}
            if not remaining:
                break

        if remaining:
            raise AssertionError(f"{label} missing: {', '.join(sorted(remaining))}")

    # === UPDATE LOGIC POPUP TỪ LEVEL 1 ===
    def _get_modal_text(self):
        def _get_visible_modal_text(driver):
            # Sử dụng self.loc_modal_dialog được cấu hình từ file JSON (Level 2)
            modals = driver.find_elements(*self.loc_modal_dialog)
            for modal in modals:
                if modal.is_displayed():
                    text = modal.get_attribute("textContent")
                    if text and text.strip():
                        return text
            return None

        return self.wait.until(_get_visible_modal_text)

    def _normalize_text(self, text):
        if not text:
            return ""
        return " ".join(text.split())

    def _get_warning_text(self, expected_status):
        marker = "Questions without a response"
        if not expected_status or marker not in expected_status:
            return ""
        start = expected_status.index(marker)
        return expected_status[start:].strip()

    def _finish_attempt(self, expected_status, cancel_submit=False):
        # 6. Next page (Finish attempt)
        try:
            self._wait_click(self.loc_btn_next)
        except TimeoutException:
            # Fallback to the Finish attempt link in quiz navigation
            self._wait_click(self.loc_finish_attempt)
        seen_texts = [self._get_body_text()]

        # 8. Submit all and finish (modal confirm if present)
        self._wait_click(self.loc_btn_submit_all)
        warning_text = self._get_warning_text(expected_status)
        if warning_text:
            marker = "Questions without a response"
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: marker in self._normalize_text(self._get_modal_text())
                )
            except TimeoutException:
                pass
                
        modal_text = self._normalize_text(self._get_modal_text())
        if modal_text:
            seen_texts.append(modal_text)
            
        warning_text = self._normalize_text(warning_text)
        if warning_text:
            if warning_text not in modal_text:
                raise AssertionError(f"Popup warning missing: {warning_text}")
        elif expected_status and "Answer saved" in expected_status:
            if "Questions without a response" in modal_text:
                raise AssertionError("Popup warning should not appear")

        if cancel_submit:
            self._wait_click(self.loc_btn_submit_cancel)
            seen_texts.append(self._get_body_text())
            return seen_texts

        self._try_click(self.loc_btn_submit_confirm, timeout=5)
        seen_texts.append(self._get_body_text())
        return seen_texts

    def _finish_review(self):
        # Return from review page to quiz details if the button is present
        self._try_click(self.loc_btn_finish_review, timeout=3)

    def _logout(self):
        # 10. Logout
        self._wait_click(self.loc_user_menu)
        self._wait_click(self.loc_link_logout)

    # ===== Main test =====
    def test_level2_data_driven(self):
        csv_path = os.path.join(os.path.dirname(__file__), "data", "data_level_2.csv")

        with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                test_id = (row.get("test_id") or "UNKNOWN").strip()
                expected_status = (row.get("expected_status") or "").strip()
                expected_score = (row.get("expected_score") or "").strip()
                cancel_submit = (
                    "summary of attempt" in expected_status.lower() and not expected_score
                )

                try:
                    logging.info("Start test case: %s", test_id)
                    self._start_driver()

                    self._login(row.get("username", ""), row.get("password", ""))
                    self._open_course_and_quiz()
                    self._fill_answers(row.get("input_answer", ""))

                    # 6-8. Next page, verify status, and finish attempt
                    seen_texts = self._finish_attempt(expected_status, cancel_submit)

                    self._verify_expected_parts(expected_status, seen_texts, "Status")

                    # 9. Verify score (after submit)
                    self._verify_expected_parts(expected_score, [seen_texts[-1]], "Score")

                    if not cancel_submit:
                        self._finish_review()

                    # 10. Logout
                    self._logout()

                    print(f"[{test_id}] PASS")
                except Exception as exc:
                    print(f"[{test_id}] FAIL")
                    logging.error("Test case failed: %s", test_id)
                    logging.error("%s", traceback.format_exc())
                    # self._save_screenshot(test_id)
                    self.errors.append(f"{test_id}: {type(exc).__name__} - {exc}")
                finally:
                    self._stop_driver()

        if self.errors:
            self.fail("Failures:\n" + "\n".join(self.errors))


if __name__ == "__main__":
    unittest.main()