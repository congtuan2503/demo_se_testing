import csv
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


class Level1DataDrivenTest(unittest.TestCase):
	# Base URL from the Katalon exports
	BASE_URL = "https://school.moodledemo.net/"

	def setUp(self):
		# Per-test placeholders; a fresh browser is created for each CSV row
		self.driver = None
		self.wait = None
		self.errors = []

		# self.screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
		# os.makedirs(self.screenshot_dir, exist_ok=True)

		# Locators from TC001 exports; dynamic IDs were replaced with stable text-based XPath
		self.loc_login_link = (By.LINK_TEXT, "Log in")
		self.loc_input_username = (By.ID, "username")
		self.loc_input_password = (By.ID, "password")
		self.loc_btn_login = (By.ID, "loginbtn")
		self.loc_link_my_courses = (By.LINK_TEXT, "My courses")
		self.loc_link_course = (By.PARTIAL_LINK_TEXT, "Chemical Nomenclature")
		self.loc_link_quiz = (By.PARTIAL_LINK_TEXT, "Balancing Chemical Equations")
		self.loc_btn_attempt_quiz = (
			By.XPATH,
			"//button[contains(., 'Attempt quiz') or contains(., 'Re-attempt quiz') or contains(., 'Continue your attempt')]"
			" | //input[contains(@value, 'Attempt quiz') or contains(@value, 'Re-attempt quiz') or contains(@value, 'Continue your attempt')]",
		)
		self.loc_inputs_quiz = (By.XPATH, "//input[contains(@id, '_answer')]")
		self.loc_btn_next = (By.ID, "mod_quiz-next-nav")
		self.loc_finish_attempt = (
			By.XPATH,
			"//a[contains(., 'Finish attempt...')]"
			" | //button[contains(., 'Finish attempt...')]"
			" | //input[contains(@value, 'Finish attempt...')]",
		)
		self.loc_btn_submit_all = (
			By.XPATH,
			"//button[contains(., 'Submit all and finish')]"
			" | //input[contains(@value, 'Submit all and finish')]",
		)
		self.loc_btn_submit_cancel = (
			By.XPATH,
			"//div[contains(@class, 'modal') or @role='dialog']"
			"//button[contains(., 'Cancel')]"
			" | //div[contains(@class, 'modal') or @role='dialog']"
			"//input[contains(@value, 'Cancel')]",
		)
		self.loc_btn_submit_confirm = (
			By.XPATH,
			"//div[contains(@class, 'modal') or @role='dialog']"
			"//button[contains(., 'Submit all and finish')]"
			" | //div[contains(@class, 'modal') or @role='dialog']"
			"//input[contains(@value, 'Submit all and finish')]",
		)
		self.loc_btn_finish_review = (
			By.XPATH,
			"//button[contains(., 'Finish review')]"
			" | //input[contains(@value, 'Finish review')]"
			" | //a[contains(., 'Finish review')]",
		)
		self.loc_user_menu = (By.ID, "user-menu-toggle")
		self.loc_link_logout = (By.LINK_TEXT, "Log out")

	def tearDown(self):
		# Safety cleanup if a test crashed before closing the browser
		self._stop_driver()

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
		return self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body"))).text

	# def _save_screenshot(self, test_id):
	# 	if not self.driver:
	# 		return
	# 	file_name = f"{test_id}_fail.png"
	# 	file_path = os.path.join(self.screenshot_dir, file_name)
	# 	self.driver.save_screenshot(file_path)

	# ===== Flow steps =====
	def _login(self, username, password):
		# 1. Open Moodle and go to login
		self.driver.get(self.BASE_URL)
		self._wait_click(self.loc_login_link)

		# 2. Login
		self._wait_send_keys(self.loc_input_username, username)
		self._wait_send_keys(self.loc_input_password, password)
		self._wait_click(self.loc_btn_login)

	def _open_course_and_quiz(self):
		# 3. Open course and quiz
		self._try_click(self.loc_link_my_courses, timeout=5)
		self._wait_click(self.loc_link_course)
		self._wait_click(self.loc_link_quiz)

		# 4. Attempt quiz
		self._wait_click(self.loc_btn_attempt_quiz)

	def _fill_answers(self, input_answer):
		# 5. Input answers based on CSV
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

	def _get_modal_text(self):
		def _get_visible_modal_text(driver):
			modals = driver.find_elements(
				By.XPATH,
				"//div[contains(@class, 'modal') or @role='dialog']",
			)
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
	def test_level1_data_driven(self):
		csv_path = os.path.join(os.path.dirname(__file__), "data", "data_level_1.csv")

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
