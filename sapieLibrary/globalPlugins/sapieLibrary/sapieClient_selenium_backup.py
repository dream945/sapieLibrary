# -*- coding: utf-8 -*-
# Sapie Library Client - Selenium-based web automation

import sys
import os

# CRITICAL: Add bundled Selenium to path BEFORE importing
_current_dir = os.path.dirname(os.path.abspath(__file__))
_lib_path = os.path.join(_current_dir, "lib")
if _lib_path not in sys.path:
	sys.path.insert(0, _lib_path)

import time
import logging
import re

# Set up logging
log = logging.getLogger(__name__)

# Import only what we need to avoid firefox dependencies
try:
	from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
	from selenium.webdriver.chrome.options import Options as ChromeOptions
	from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
	from selenium.webdriver.edge.options import Options as EdgeOptions
	from selenium.webdriver.common.by import By
	from selenium.webdriver.common.keys import Keys
	from selenium.webdriver.support.ui import WebDriverWait
	from selenium.webdriver.support import expected_conditions as EC
	from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
except ImportError as e:
	log.error(f"Failed to import selenium: {e}")
	# Fallback to full import
	from selenium import webdriver
	from selenium.webdriver.common.by import By
	from selenium.webdriver.common.keys import Keys
	from selenium.webdriver.support.ui import WebDriverWait
	from selenium.webdriver.support import expected_conditions as EC
	from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
	ChromeDriver = webdriver.Chrome
	ChromeOptions = webdriver.ChromeOptions
	EdgeDriver = webdriver.Edge
	EdgeOptions = webdriver.EdgeOptions

class SapieClient:
	"""Client for interacting with Sapie Library website"""

	# Sapie Library URLs
	BASE_URL = "https://www.sapie.or.jp"
	LOGIN_URL = "https://member.sapie.or.jp/login"
	LIBRARY_BASE_URL = "https://library.sapie.or.jp/cgi-bin/CN1MN1"

	# Session tokens (extracted after login)
	session_tokens = {}

	def __init__(self):
		"""Initialize Sapie client"""
		self.driver = None
		self.logged_in = False
		self.username = None
		self.session_tokens = {}

	def _init_driver(self):
		"""Initialize Selenium WebDriver"""
		if self.driver:
			log.info("Driver already initialized")
			return

		log.info("Starting driver initialization...")

		try:
			# Try Edge first (most reliable on Windows)
			log.info("Attempting to start Edge WebDriver...")
			edge_error = None
			try:
				from selenium import webdriver
				from selenium.webdriver.edge.service import Service as EdgeService

				edge_options = EdgeOptions()
				edge_options.add_argument('--headless')
				edge_options.add_argument('--disable-gpu')
				edge_options.add_argument('--no-sandbox')
				edge_options.add_argument('--disable-dev-shm-usage')
				edge_options.add_argument('--lang=ja')
				edge_options.add_argument('--disable-blink-features=AutomationControlled')

				# Set download preferences
				prefs = {
					'download.prompt_for_download': False,
					'download.directory_upgrade': True,
					'safebrowsing.enabled': True
				}
				edge_options.add_experimental_option("prefs", prefs)

				# Use Selenium Manager to auto-download correct driver
				self.driver = webdriver.Edge(options=edge_options)
				self.driver.implicitly_wait(10)
				log.info("Edge WebDriver started successfully")
				return
			except Exception as e:
				edge_error = str(e)
				log.warning(f"Edge failed: {edge_error}")

			# Try Chrome as fallback
			log.info("Attempting to start Chrome WebDriver...")
			try:
				from selenium import webdriver
				from selenium.webdriver.chrome.service import Service as ChromeService

				options = ChromeOptions()
				options.add_argument('--headless')
				options.add_argument('--disable-gpu')
				options.add_argument('--no-sandbox')
				options.add_argument('--disable-dev-shm-usage')
				options.add_argument('--lang=ja')
				options.add_argument('--disable-blink-features=AutomationControlled')

				# Set download preferences
				prefs = {
					'download.prompt_for_download': False,
					'download.directory_upgrade': True,
					'safebrowsing.enabled': True
				}
				options.add_experimental_option("prefs", prefs)

				# Use Selenium Manager to auto-download correct driver
				self.driver = webdriver.Chrome(options=options)
				self.driver.implicitly_wait(10)
				log.info("Chrome WebDriver started successfully")
				return
			except Exception as chrome_error:
				log.error(f"Chrome failed: {chrome_error}")
				error_msg = f"Edge: {edge_error}, Chrome: {str(chrome_error)}"
				raise Exception(f"ブラウザドライバーの初期化に失敗しました。EdgeまたはChromeがインストールされているか確認してください。")

		except Exception as e:
			log.error(f"Driver initialization failed completely: {e}", exc_info=True)
			raise Exception(f"ブラウザドライバーの初期化に失敗しました: {str(e)}")

	def login(self, username, password):
		"""
		Login to Sapie Library

		Args:
			username (str): Sapie user ID
			password (str): Sapie password

		Returns:
			tuple: (success: bool, message: str)
		"""
		try:
			# Initialize driver if needed
			log.info("Sapie login starting...")
			try:
				self._init_driver()
				log.info("Browser driver initialized")
			except Exception as init_error:
				log.error(f"Browser init failed: {init_error}", exc_info=True)
				return (False, f"ブラウザ初期化エラー: {str(init_error)}")

			# Navigate to login page
			log.info(f"Navigating to {self.LOGIN_URL}")
			try:
				self.driver.get(self.LOGIN_URL)
				log.info(f"Page loaded: {self.driver.current_url}")
			except Exception as nav_error:
				log.error(f"Navigation failed: {nav_error}", exc_info=True)
				return (False, f"ログインページへのアクセスエラー: {str(nav_error)}")

			# Wait for page to load
			wait = WebDriverWait(self.driver, 15)

			# Find and fill username field (Sapie uses id="uid")
			username_field = wait.until(
				EC.presence_of_element_located((By.ID, "uid"))
			)
			username_field.clear()
			username_field.send_keys(username)

			# Find and fill password field (Sapie uses id="password")
			password_field = self.driver.find_element(By.ID, "password")
			password_field.clear()
			password_field.send_keys(password)

			# Find and click login button (Sapie uses input with name="commit")
			login_button = self.driver.find_element(By.NAME, "commit")

			login_button.click()

			# Wait for login to complete
			time.sleep(5)  # Give more time for page to load

			# Check if login was successful
			# This checks for common error indicators
			page_source = self.driver.page_source.lower()

			if "error" in page_source or "エラー" in page_source or "ログインに失敗" in page_source:
				return (False, "ログインに失敗しました。ユーザー名とパスワードを確認してください。")

			# Check if we're redirected to a member page
			current_url = self.driver.current_url
			if "member" in current_url or "library" in current_url:
				self.logged_in = True
				self.username = username
				return (True, f"ログイン成功: {username}")
			else:
				return (False, "ログイン状態を確認できませんでした。")

		except TimeoutException:
			return (False, "ログインページの読み込みがタイムアウトしました。")
		except Exception as e:
			return (False, f"ログインエラー: {str(e)}")

	def search(self, book_type="braille", search_params=None):
		"""
		Search for books in Sapie Library

		Args:
			book_type (str): Type of book - "braille" or "daisy"
			search_params (dict): Search parameters:
				- title (str): Title search query
				- author (str): Author search query
				- publisher (str): Publisher search query
				- pub_year_from (str): Publication year from
				- pub_year_to (str): Publication year to
				- data_type (str): Data type for DAISY (S00201): "22", "33", "42"
				- category (str): Category (S00218): "1", "2", "3"
				- include_ndl (bool): Include National Diet Library

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "検索する前にログインしてください。")

		# Default search params
		if search_params is None:
			search_params = {}

		title = search_params.get("title", "")
		author = search_params.get("author", "")
		publisher = search_params.get("publisher", "")
		pub_year_from = search_params.get("pub_year_from", "")
		pub_year_to = search_params.get("pub_year_to", "")
		data_type = search_params.get("data_type", "")
		category = search_params.get("category", "")
		include_ndl = search_params.get("include_ndl", True)

		try:
			log.info(f"Starting search: type='{book_type}', title='{title}', author='{author}', publisher='{publisher}', pub_year={pub_year_from}-{pub_year_to}, data_type='{data_type}', category='{category}', include_ndl={include_ndl}")

			# Navigate to braille search page
			# Extract session tokens from current page first
			self._extract_session_tokens()

			if book_type == "braille":
				# Navigate to braille search page (点字データ検索)
				search_page_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SCH01&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"
			else:
				# DAISY search page (デイジーデータ検索)
				search_page_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SCH08&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"

			log.info(f"Navigating to search page: {search_page_url}")
			self.driver.get(search_page_url)

			# Wait for search page to load by waiting for title field
			wait = WebDriverWait(self.driver, 10)
			wait.until(EC.presence_of_element_located((By.ID, "S00251")))

			# Extract session tokens again from the search page
			self._extract_session_tokens()

			# Find and fill title search field (S00251)
			if title:
				log.info("Looking for title field (S00251)...")
				title_field = wait.until(
					EC.presence_of_element_located((By.ID, "S00251"))
				)
				title_field.clear()
				title_field.send_keys(title)
				log.info(f"Title field filled with: {title}")

			# Find and fill author search field (S00252)
			if author:
				log.info("Looking for author field (S00252)...")
				try:
					author_field = self.driver.find_element(By.ID, "S00252")
					author_field.clear()
					author_field.send_keys(author)
					log.info(f"Author field filled with: {author}")
				except:
					log.warning("Author field not found")

			# Find and fill publisher search field (S00253)
			if publisher:
				log.info("Looking for publisher field (S00253)...")
				try:
					publisher_field = self.driver.find_element(By.ID, "S00253")
					publisher_field.clear()
					publisher_field.send_keys(publisher)
					log.info(f"Publisher field filled with: {publisher}")
				except:
					log.warning("Publisher field not found")

			# Find and fill publication year from field (S00254)
			if pub_year_from:
				log.info("Looking for publication year from field (S00254)...")
				try:
					pub_year_from_field = self.driver.find_element(By.ID, "S00254")
					pub_year_from_field.clear()
					pub_year_from_field.send_keys(pub_year_from)
					log.info(f"Publication year from filled with: {pub_year_from}")
				except:
					log.warning("Publication year from field not found")

			# Find and fill publication year to field (S00255)
			if pub_year_to:
				log.info("Looking for publication year to field (S00255)...")
				try:
					pub_year_to_field = self.driver.find_element(By.ID, "S00255")
					pub_year_to_field.clear()
					pub_year_to_field.send_keys(pub_year_to)
					log.info(f"Publication year to filled with: {pub_year_to}")
				except:
					log.warning("Publication year to field not found")

			# Set data type (DAISY only) - S00201
			if book_type == "daisy" and data_type:
				log.info(f"Setting data type (S00201) to: {data_type}")
				try:
					data_type_select = self.driver.find_element(By.ID, "S00201")
					data_type_select.send_keys(Keys.HOME)  # Reset selection
					# Find the option with the value
					option = data_type_select.find_element(By.XPATH, f".//option[@value='{data_type}']")
					option.click()
					log.info(f"Data type set to: {data_type}")
				except Exception as e:
					log.warning(f"Could not set data type: {e}")

			# Set category - S00218
			if category:
				log.info(f"Setting category (S00218) to: {category}")
				try:
					category_select = self.driver.find_element(By.ID, "S00218")
					category_select.send_keys(Keys.HOME)  # Reset selection
					# Find the option with the value
					option = category_select.find_element(By.XPATH, f".//option[@value='{category}']")
					option.click()
					log.info(f"Category set to: {category}")
				except Exception as e:
					log.warning(f"Could not set category: {e}")

			# Set include NDL checkbox - S00262
			try:
				ndl_checkbox = self.driver.find_element(By.ID, "S00262")
				is_checked = ndl_checkbox.is_selected()
				if include_ndl and not is_checked:
					ndl_checkbox.click()
					log.info("NDL checkbox checked")
				elif not include_ndl and is_checked:
					ndl_checkbox.click()
					log.info("NDL checkbox unchecked")
			except Exception as e:
				log.warning(f"Could not set NDL checkbox: {e}")

			# Submit search (検索開始 button)
			log.info("Looking for search button...")
			search_buttons = self.driver.find_elements(By.XPATH, "//input[@type='submit'][@value='検索開始']")
			if search_buttons:
				log.info("Clicking search button...")
				search_buttons[0].click()
			else:
				return (False, "検索ボタンが見つかりませんでした")

			# Wait for results page to load by checking for results table or "no results" message
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source or
					"検索結果：0件" in driver.page_source
				)
				log.info(f"Results page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("Results page load timeout, continuing anyway")
				log.info(f"Results page URL: {self.driver.current_url}")


			# Parse results from all pages (handle pagination)
			all_results = []
			page_num = 1
			max_pages = 10  # Safety limit to prevent infinite loops

			while page_num <= max_pages:
				log.info(f"Parsing page {page_num}...")

				# Parse current page
				page_results = self._parse_search_results(book_type)
				all_results.extend(page_results)

				log.info(f"Found {len(page_results)} results on page {page_num}, total so far: {len(all_results)}")

				# Check if there's a "Next" link
				try:
					next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
					if next_links:
						log.info(f"Found 'Next' link, navigating to page {page_num + 1}")
						next_links[0].click()

						# Wait for next page to load
						wait = WebDriverWait(self.driver, 10)
						wait.until(
							lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']")
						)

						page_num += 1
					else:
						log.info("No more pages, finished pagination")
						break
				except Exception as e:
					log.warning(f"Error checking for next page: {e}")
					break

			log.info(f"Finished collecting all results: {len(all_results)} total")
			return (True, all_results)

		except TimeoutException:
			log.error("Search timeout")
			return (False, "検索がタイムアウトしました")
		except Exception as e:
			log.error(f"Search error: {e}", exc_info=True)
			return (False, f"検索エラー: {str(e)}")

	def detailed_search(self, search_params=None):
		"""
		Perform detailed search in Sapie Library (J01SCH04)

		Args:
			search_params (dict): Search parameters:
				- title (str): Title search query (S00251)
				- author (str): Author search query (S00252)
				- keyword (str): Keyword search query (S00253)
				- publisher (str): Publisher search query (S00254)
				- ndc (str): NDC classification (S00241)
				- isbn (str): ISBN (S00243)
				- pub_year_from (str): Publication year from, 6 digits YYYYMM (S00222)
				- pub_year_to (str): Publication year to, 6 digits YYYYMM (S00223)
				- material_type (str): Material type (S00201)
				- category (str): Category (S00218): "1", "2", "3"
				- include_ndl (bool): Include National Diet Library (S00262)

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "検索する前にログインしてください。")

		# Default search params
		if search_params is None:
			search_params = {}

		# Extract all parameters
		title = search_params.get("title", "")
		title_method = search_params.get("title_method", "1")
		author = search_params.get("author", "")
		author_method = search_params.get("author_method", "1")
		keyword = search_params.get("keyword", "")
		keyword_method = search_params.get("keyword_method", "1")
		exclude_abstract = search_params.get("exclude_abstract", "")
		publisher = search_params.get("publisher", "")
		ndc = search_params.get("ndc", "")
		genre = search_params.get("genre", "")
		isbn = search_params.get("isbn", "")
		braille_num = search_params.get("braille_num", "")
		producer_id = search_params.get("producer_id", "")
		holder_id = search_params.get("holder_id", "")
		has_content = search_params.get("has_content", "")
		online_request = search_params.get("online_request", "")
		include_ndl = search_params.get("include_ndl", "")
		material_type = search_params.get("material_type", "")
		daisy_only = search_params.get("daisy_only", "")
		braille_detail = search_params.get("braille_detail", "")
		catalog_type = search_params.get("catalog_type", "1")
		category = search_params.get("category", "")
		target = search_params.get("target", "")
		loan_format = search_params.get("loan_format", "")
		production_status = search_params.get("production_status", "")
		graphic = search_params.get("graphic", "")
		audio_comp = search_params.get("audio_comp", "")
		orig_pub_from = search_params.get("orig_pub_from", "")
		orig_pub_to = search_params.get("orig_pub_to", "")
		braille_pub_from = search_params.get("braille_pub_from", "")
		braille_pub_to = search_params.get("braille_pub_to", "")
		complete_from = search_params.get("complete_from", "")
		complete_to = search_params.get("complete_to", "")
		display_count = search_params.get("display_count", "50")

		try:
			log.info(f"Starting detailed search: title='{title}', author='{author}', keyword='{keyword}', publisher='{publisher}', ndc='{ndc}', isbn='{isbn}', pub_year={pub_year_from}-{pub_year_to}, material_type='{material_type}', category='{category}', include_ndl={include_ndl}")

			# Extract session tokens from current page first
			self._extract_session_tokens()

			# Navigate to detailed search page (J01SCH04)
			detailed_search_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SCH04&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"

			log.info(f"Navigating to detailed search page: {detailed_search_url}")
			self.driver.get(detailed_search_url)

			# Wait for search page to load by waiting for title field
			wait = WebDriverWait(self.driver, 10)
			wait.until(EC.presence_of_element_located((By.ID, "S00251")))

			# Extract session tokens again from the search page
			self._extract_session_tokens()

			# Fill in search fields
			# Title (S00251)
			if title:
				log.info("Filling title field (S00251)...")
				try:
					title_field = wait.until(EC.presence_of_element_located((By.ID, "S00251")))
					title_field.clear()
					title_field.send_keys(title)
					log.info(f"Title field filled with: {title}")
				except:
					log.warning("Title field not found")

			# Author (S00252)
			if author:
				log.info("Filling author field (S00252)...")
				try:
					author_field = self.driver.find_element(By.ID, "S00252")
					author_field.clear()
					author_field.send_keys(author)
					log.info(f"Author field filled with: {author}")
				except:
					log.warning("Author field not found")

			# Keyword (S00253)
			if keyword:
				log.info("Filling keyword field (S00253)...")
				try:
					keyword_field = self.driver.find_element(By.ID, "S00253")
					keyword_field.clear()
					keyword_field.send_keys(keyword)
					log.info(f"Keyword field filled with: {keyword}")
				except:
					log.warning("Keyword field not found")

			# Publisher (S00254)
			if publisher:
				log.info("Filling publisher field (S00254)...")
				try:
					publisher_field = self.driver.find_element(By.ID, "S00254")
					publisher_field.clear()
					publisher_field.send_keys(publisher)
					log.info(f"Publisher field filled with: {publisher}")
				except:
					log.warning("Publisher field not found")

			# NDC classification (S00241)
			if ndc:
				log.info("Filling NDC field (S00241)...")
				try:
					ndc_field = self.driver.find_element(By.ID, "S00241")
					ndc_field.clear()
					ndc_field.send_keys(ndc)
					log.info(f"NDC field filled with: {ndc}")
				except:
					log.warning("NDC field not found")

			# ISBN (S00243)
			if isbn:
				log.info("Filling ISBN field (S00243)...")
				try:
					isbn_field = self.driver.find_element(By.ID, "S00243")
					isbn_field.clear()
					isbn_field.send_keys(isbn)
					log.info(f"ISBN field filled with: {isbn}")
				except:
					log.warning("ISBN field not found")

			# Title method (S00215)
			if title_method:
				try:
					title_method_select = self.driver.find_element(By.ID, "S00215")
					title_method_select.send_keys(Keys.HOME)
					option = title_method_select.find_element(By.XPATH, f".//option[@value='{title_method}']")
					option.click()
				except: pass

			# Author method (S00216)
			if author_method:
				try:
					author_method_select = self.driver.find_element(By.ID, "S00216")
					author_method_select.send_keys(Keys.HOME)
					option = author_method_select.find_element(By.XPATH, f".//option[@value='{author_method}']")
					option.click()
				except: pass

			# Keyword method (S00234)
			if keyword_method:
				try:
					keyword_method_select = self.driver.find_element(By.ID, "S00234")
					keyword_method_select.send_keys(Keys.HOME)
					option = keyword_method_select.find_element(By.XPATH, f".//option[@value='{keyword_method}']")
					option.click()
				except: pass

			# Exclude abstract (S00220)
			if exclude_abstract:
				try:
					exclude_cb = self.driver.find_element(By.ID, "S00220")
					if not exclude_cb.is_selected():
						exclude_cb.click()
				except: pass

			# Genre (S00239)
			if genre:
				try:
					genre_field = self.driver.find_element(By.ID, "S00239")
					genre_field.clear()
					genre_field.send_keys(genre)
				except: pass

			# Braille number (S00233)
			if braille_num:
				try:
					braille_num_field = self.driver.find_element(By.ID, "S00233")
					braille_num_field.clear()
					braille_num_field.send_keys(braille_num)
				except: pass

			# Producer ID (S00231)
			if producer_id:
				try:
					producer_id_field = self.driver.find_element(By.ID, "S00231")
					producer_id_field.clear()
					producer_id_field.send_keys(producer_id)
				except: pass

			# Holder ID (S00232)
			if holder_id:
				try:
					holder_id_field = self.driver.find_element(By.ID, "S00232")
					holder_id_field.clear()
					holder_id_field.send_keys(holder_id)
				except: pass

			# Has content (S00213)
			if has_content:
				try:
					has_content_cb = self.driver.find_element(By.ID, "S00213")
					if not has_content_cb.is_selected():
						has_content_cb.click()
				except: pass

			# Online request (S00214)
			if online_request:
				try:
					online_request_cb = self.driver.find_element(By.ID, "S00214")
					if not online_request_cb.is_selected():
						online_request_cb.click()
				except: pass

			# DAISY only (S00208)
			if daisy_only:
				try:
					daisy_only_cb = self.driver.find_element(By.ID, "S00208")
					if not daisy_only_cb.is_selected():
						daisy_only_cb.click()
				except: pass

			# Braille detail (S00247x checkboxes)
			if braille_detail:
				for detail in braille_detail.split(","):
					try:
						cb_id = f"S00247{detail[-1]}"  # S002471, S002472, etc.
						cb = self.driver.find_element(By.ID, cb_id)
						if not cb.is_selected():
							cb.click()
					except: pass

			# Catalog type (S00217)
			if catalog_type:
				try:
					catalog_type_select = self.driver.find_element(By.ID, "S00217")
					catalog_type_select.send_keys(Keys.HOME)
					option = catalog_type_select.find_element(By.XPATH, f".//option[@value='{catalog_type}']")
					option.click()
				except: pass

			# Target (S00235)
			if target:
				try:
					target_select = self.driver.find_element(By.ID, "S00235")
					target_select.send_keys(Keys.HOME)
					option = target_select.find_element(By.XPATH, f".//option[@value='{target}']")
					option.click()
				except: pass

			# Loan format (S00202)
			if loan_format:
				try:
					loan_format_select = self.driver.find_element(By.ID, "S00202")
					loan_format_select.send_keys(Keys.HOME)
					option = loan_format_select.find_element(By.XPATH, f".//option[@value='{loan_format}']")
					option.click()
				except: pass

			# Production status (S00219)
			if production_status:
				try:
					production_status_select = self.driver.find_element(By.ID, "S00219")
					production_status_select.send_keys(Keys.HOME)
					option = production_status_select.find_element(By.XPATH, f".//option[@value='{production_status}']")
					option.click()
				except: pass

			# Graphic (S00209)
			if graphic:
				try:
					graphic_select = self.driver.find_element(By.ID, "S00209")
					graphic_select.send_keys(Keys.HOME)
					option = graphic_select.find_element(By.XPATH, f".//option[@value='{graphic}']")
					option.click()
				except: pass

			# Audio compression (S00210)
			if audio_comp:
				try:
					audio_comp_select = self.driver.find_element(By.ID, "S00210")
					audio_comp_select.send_keys(Keys.HOME)
					option = audio_comp_select.find_element(By.XPATH, f".//option[@value='{audio_comp}']")
					option.click()
				except: pass

			# Original publication date from (S00222)
			if orig_pub_from:
				try:
					orig_pub_from_field = self.driver.find_element(By.ID, "S00222")
					orig_pub_from_field.clear()
					orig_pub_from_field.send_keys(orig_pub_from)
				except: pass

			# Original publication date to (S00223)
			if orig_pub_to:
				try:
					orig_pub_to_field = self.driver.find_element(By.ID, "S00223")
					orig_pub_to_field.clear()
					orig_pub_to_field.send_keys(orig_pub_to)
				except: pass

			# Braille publication year from (S00224)
			if braille_pub_from:
				try:
					braille_pub_from_field = self.driver.find_element(By.ID, "S00224")
					braille_pub_from_field.clear()
					braille_pub_from_field.send_keys(braille_pub_from)
				except: pass

			# Braille publication year to (S00225)
			if braille_pub_to:
				try:
					braille_pub_to_field = self.driver.find_element(By.ID, "S00225")
					braille_pub_to_field.clear()
					braille_pub_to_field.send_keys(braille_pub_to)
				except: pass

			# Completion date from (S00226)
			if complete_from:
				try:
					complete_from_field = self.driver.find_element(By.ID, "S00226")
					complete_from_field.clear()
					complete_from_field.send_keys(complete_from)
				except: pass

			# Completion date to (S00227)
			if complete_to:
				try:
					complete_to_field = self.driver.find_element(By.ID, "S00227")
					complete_to_field.clear()
					complete_to_field.send_keys(complete_to)
				except: pass

			# Display count (S00230)
			if display_count:
				try:
					display_count_select = self.driver.find_element(By.ID, "S00230")
					display_count_select.send_keys(Keys.HOME)
					option = display_count_select.find_element(By.XPATH, f".//option[@value='{display_count}']")
					option.click()
				except: pass

			# Material type (S00201)
			if material_type:
				log.info(f"Setting material type (S00201) to: {material_type}")
				try:
					material_type_select = self.driver.find_element(By.ID, "S00201")
					material_type_select.send_keys(Keys.HOME)
					option = material_type_select.find_element(By.XPATH, f".//option[@value='{material_type}']")
					option.click()
					log.info(f"Material type set to: {material_type}")
				except Exception as e:
					log.warning(f"Could not set material type: {e}")

			# Category (S00218)
			if category:
				log.info(f"Setting category (S00218) to: {category}")
				try:
					category_select = self.driver.find_element(By.ID, "S00218")
					category_select.send_keys(Keys.HOME)
					option = category_select.find_element(By.XPATH, f".//option[@value='{category}']")
					option.click()
					log.info(f"Category set to: {category}")
				except Exception as e:
					log.warning(f"Could not set category: {e}")

			# Include NDL checkbox (S00262)
			try:
				ndl_checkbox = self.driver.find_element(By.ID, "S00262")
				is_checked = ndl_checkbox.is_selected()
				if include_ndl and not is_checked:
					ndl_checkbox.click()
					log.info("NDL checkbox checked")
				elif not include_ndl and is_checked:
					ndl_checkbox.click()
					log.info("NDL checkbox unchecked")
			except Exception as e:
				log.warning(f"Could not set NDL checkbox: {e}")

			# Submit search (検索開始 button)
			log.info("Looking for search button...")
			search_buttons = self.driver.find_elements(By.XPATH, "//input[@type='submit'][@value='検索開始']")
			if search_buttons:
				log.info("Clicking search button...")
				search_buttons[0].click()
			else:
				return (False, "検索ボタンが見つかりませんでした")

			# Wait for results page to load
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source or
					"検索結果：0件" in driver.page_source
				)
				log.info(f"Results page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("Results page load timeout, continuing anyway")

			# Parse results from all pages
			all_results = []
			page_num = 1
			max_pages = 10

			while page_num <= max_pages:
				log.info(f"Parsing page {page_num}...")

				# Parse current page - use generic parser
				page_results = self._parse_search_results()
				all_results.extend(page_results)

				log.info(f"Found {len(page_results)} results on page {page_num}, total so far: {len(all_results)}")

				# Check if there's a "Next" link
				try:
					next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
					if next_links:
						log.info(f"Found 'Next' link, navigating to page {page_num + 1}")
						next_links[0].click()

						wait = WebDriverWait(self.driver, 10)
						wait.until(lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']"))

						page_num += 1
					else:
						log.info("No more pages, finished pagination")
						break
				except Exception as e:
					log.warning(f"Error checking for next page: {e}")
					break

			log.info(f"Finished collecting all results: {len(all_results)} total")
			return (True, all_results)

		except TimeoutException:
			log.error("Detailed search timeout")
			return (False, "詳細検索がタイムアウトしました")
		except Exception as e:
			log.error(f"Detailed search error: {e}", exc_info=True)
			return (False, f"詳細検索エラー: {str(e)}")

	def get_genre_subgenres(self, genre_code):
		"""
		Get subgenres for a main genre category

		Args:
			genre_code (str): Main genre code (01-17)

		Returns:
			tuple: (success: bool, subgenres: list of tuples (code, name) or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Getting subgenres for genre: code='{genre_code}'")

			# Extract session tokens
			self._extract_session_tokens()

			# Build genre URL to get subgenre list (always use J01SC202 for the first level)
			genre_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SC202&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00239={genre_code}&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Navigating to genre subgenre page: {genre_url}")
			self.driver.get(genre_url)

			# Wait for page to load
			wait = WebDriverWait(self.driver, 10)
			wait.until(
				lambda driver: driver.find_elements(By.XPATH, "//ul[@class='LINK']")
			)

			# Parse subgenres from the page
			subgenres = []
			link_list = self.driver.find_element(By.XPATH, "//ul[@class='LINK']")
			links = link_list.find_elements(By.TAG_NAME, "a")

			for link in links:
				href = link.get_attribute("href")
				name = link.text.strip()

				# Extract S00239 parameter from href
				# Example: CN1MN1?S00101=J01SC204&S00239=0101&...
				match = re.search(r'S00239=(\d+)', href)
				if match:
					subgenre_code = match.group(1)
					subgenres.append((subgenre_code, name))
					log.info(f"Found subgenre: {subgenre_code} - {name}")

			if subgenres:
				log.info(f"Found {len(subgenres)} subgenres for genre {genre_code}")
				return (True, subgenres)
			else:
				log.warning(f"No subgenres found for genre {genre_code}")
				return (True, [])

		except TimeoutException:
			log.error("Get subgenres timeout")
			return (False, "サブジャンル取得がタイムアウトしました")
		except Exception as e:
			log.error(f"Get subgenres error: {e}", exc_info=True)
			return (False, f"サブジャンル取得エラー: {str(e)}")

	def genre_search(self, subgenre_code, material_type="", has_content=False, production_status="", orig_pub_from="", orig_pub_to="", complete_from="", complete_to="", daisy_only=False):
		"""
		Search by genre subgenre with filters

		Args:
			subgenre_code (str): Subgenre code (e.g., "0101" for mystery novels)
			material_type (str): Material type code (S00201)
			has_content (bool): Only materials with content (S00213)
			production_status (str): Production status (S00219)
			orig_pub_from (str): Original publication date from (S00222)
			orig_pub_to (str): Original publication date to (S00223)
			complete_from (str): Completion date from (S00226)
			complete_to (str): Completion date to (S00227)
			daisy_only (bool): DAISY only (S00208)

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Searching by genre subgenre: code='{subgenre_code}'")

			# Extract session tokens
			self._extract_session_tokens()

			# Build genre search URL with J01LST05
			genre_url = f"{self.LIBRARY_BASE_URL}?S00101=J01LST05&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00239={subgenre_code}"

			# Add material type if specified
			if material_type:
				genre_url += f"&S00201={material_type}"

			# Add has_content flag if specified
			if has_content:
				genre_url += "&S00213=1"

			# Add production status if specified
			if production_status:
				genre_url += f"&S00219={production_status}"

			# Add original publication date range
			if orig_pub_from:
				genre_url += f"&S00222={orig_pub_from}"
			if orig_pub_to:
				genre_url += f"&S00223={orig_pub_to}"

			# Add completion date range
			if complete_from:
				genre_url += f"&S00226={complete_from}"
			if complete_to:
				genre_url += f"&S00227={complete_to}"

			# Add DAISY only flag
			if daisy_only:
				genre_url += "&S00208=1"

			# Add RTNTME at the end
			genre_url += f"&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Navigating to genre search results page: {genre_url}")
			self.driver.get(genre_url)

			# Wait for results page to load
			wait = WebDriverWait(self.driver, 10)
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source
				)
				log.info(f"Genre search page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("Genre search page load timeout, continuing anyway")

			# Parse results from all pages
			all_results = []
			page_num = 1
			max_pages = 10

			while page_num <= max_pages:
				log.info(f"Parsing genre search results page {page_num}")

				# Parse current page results
				results = self._parse_search_results("braille")

				if not results:
					log.info(f"No more results on page {page_num}")
					break

				all_results.extend(results)
				log.info(f"Found {len(results)} results on page {page_num}, total: {len(all_results)}")

				# Check if there's a next page
				try:
					next_button = self.driver.find_element(By.XPATH, "//input[@value='次の50件']")
					if not next_button.is_enabled():
						log.info("Next button disabled, no more pages")
						break

					# Click next page
					next_button.click()
					time.sleep(1)

					# Wait for next page to load
					wait.until(
						lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']")
					)

					page_num += 1
				except:
					log.info("No next page button found")
					break

			if all_results:
				log.info(f"Genre search successful: {len(all_results)} total results")
				return (True, all_results)
			else:
				log.info("Genre search returned no results")
				return (True, [])

		except TimeoutException:
			log.error("Genre search timeout")
			return (False, "ジャンル検索がタイムアウトしました")
		except Exception as e:
			log.error(f"Genre search error: {e}", exc_info=True)
			return (False, f"ジャンル検索エラー: {str(e)}")

	def _extract_session_tokens(self):
		"""Extract session tokens from hidden form fields"""
		try:
			# Find hidden input fields with session tokens
			hidden_inputs = self.driver.find_elements(By.XPATH, "//input[@type='hidden']")
			for inp in hidden_inputs:
				name = inp.get_attribute("name")
				value = inp.get_attribute("value")
				if name in ["S00102", "S00103", "RTNTME"]:
					self.session_tokens[name] = value
					log.info(f"Extracted session token: {name}={value}")
		except Exception as e:
			log.warning(f"Failed to extract session tokens: {e}")

	def _parse_search_results(self, book_type="braille"):
		"""
		Parse search results from current page using HTML parsing (much faster than Selenium)

		Args:
			book_type (str): Type of search - "braille" or "daisy"

		Returns:
			list: List of dictionaries containing book information
		"""
		results = []

		try:
			log.info(f"Parsing search results for {book_type}...")

			# Get page source and parse with simple string methods (faster than Selenium)
			page_source = self.driver.page_source

			# Check for no results
			if "該当するデータが見つかりませんでした" in page_source or "検索結果：0件" in page_source:
				log.info("No results found")
				return []

			# Use simple HTML parsing instead of Selenium (MUCH faster)
			import re

			# Find all table rows in tbody
			tbody_pattern = r'<tbody>(.*?)</tbody>'
			tbody_match = re.search(tbody_pattern, page_source, re.DOTALL)

			if not tbody_match:
				log.warning("No tbody found in page")
				return []

			tbody_content = tbody_match.group(1)

			# Find all rows
			row_pattern = r'<tr>(.*?)</tr>'
			rows = re.findall(row_pattern, tbody_content, re.DOTALL)

			log.info(f"Found {len(rows)} data rows")

			for i, row_html in enumerate(rows):
				try:
					# Extract cells
					cell_pattern = r'<td[^>]*>(.*?)</td>'
					cells = re.findall(cell_pattern, row_html, re.DOTALL)
					if len(cells) < 3:  # Need at least: number, title, author
						log.warning(f"Row {i+1} has only {len(cells)} cells, skipping")
						continue

					# Column 1: Title with link
					title_match = re.search(r'<a[^>]*>(.*?)</a>', cells[1])
					if title_match:
						title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
						url_match = re.search(r'href="([^"]+)"', cells[1])
						book_url = url_match.group(1) if url_match else ""
					else:
						title = re.sub(r'<[^>]+>', '', cells[1]).strip()
						book_url = ""

					# Column 2: Author
					author = re.sub(r'<[^>]+>', '', cells[2]).strip() if len(cells) > 2 else ""

					# Last column: Download form with IDs
					download_cell = cells[-1]

					# Extract S00224 (book ID)
					s00224_match = re.search(r'name="S00224"\s+value="([^"]+)"', download_cell)
					book_id = s00224_match.group(1) if s00224_match else str(i+1)

					# Extract S00202 (data type)
					s00202_match = re.search(r'name="S00202"\s+value="([^"]+)"', download_cell)
					s00202_value = s00202_match.group(1) if s00202_match else None

					# Extract S00215 (source)
					s00215_match = re.search(r'name="S00215"\s+value="([^"]+)"', download_cell)
					s00215_value = s00215_match.group(1) if s00215_match else None

					# Check if NDL source
					is_ndl_source = (s00215_value == "5") or ("国会からダウン" in download_cell)

					# Set type and format based on S00202 value (data type)
					# S00202: "11" = braille, "22" = DAISY audio, "33" = DAISY text
					if s00202_value == "11":
						result_type = '点字'
						result_format = 'BRL'
					elif s00202_value == "22":
						result_type = 'デイジー(音声)'
						result_format = 'DAISY'
					elif s00202_value == "33":
						result_type = 'デイジー(テキスト)'
						result_format = 'DAISY'
					else:
						# Fallback to book_type parameter if S00202 is not available
						if book_type == "daisy":
							result_type = 'デイジー'
							result_format = 'DAISY'
						else:
							result_type = '点字'
							result_format = 'BRL'

					results.append({
						'id': book_id,
						'title': title,
						'author': author,
						'type': result_type,
						'format': result_format,
						'url': book_url,
						's00202': s00202_value,  # Store actual S00202 value from form
						's00215': s00215_value,  # Store actual S00215 value (priority/source)
						'is_ndl': is_ndl_source  # Flag for National Diet Library source
					})

					if (i+1) % 10 == 0:  # Log every 10 results
						log.info(f"Parsed {i+1} results so far...")
					log.info(f"Parsed result {i+1}: {title} / {author} (ID: {book_id}, Type: {result_type}, S00202: {s00202_value}, S00215: {s00215_value}, NDL: {is_ndl_source})")

				except Exception as e:
					log.error(f"Failed to parse result row {i}: {e}", exc_info=True)
					continue

			log.info(f"Finished parsing loop, total results: {len(results)}")

			# If no results found
			if not results:
				# Check if there's a "no results" message
				if "該当するデータが見つかりませんでした" in page_source or "検索結果：0件" in page_source:
					log.info("No results found message detected")
					results.append({
						'id': '0',
						'title': '（検索結果が見つかりませんでした）',
						'author': '',
						'type': '',
						'format': ''
					})
				else:
					log.warning("Could not parse results - returning placeholder")
					results.append({
						'id': '0',
						'title': '（検索結果のパースに失敗しました。NVDAログを確認してください）',
						'author': '',
						'type': '',
						'format': ''
					})

		except Exception as e:
			log.error(f"Result parsing error: {e}", exc_info=True)
			results.append({
				'id': '0',
				'title': f'結果解析エラー: {str(e)}',
				'author': '',
				'type': '',
				'format': ''
			})

		return results

	def _detect_format(self, book_type):
		"""Detect file format from book type"""
		if "点字" in book_type or "braille" in book_type.lower():
			return "BRL"
		elif "デイジー" in book_type or "daisy" in book_type.lower():
			return "DAISY"
		else:
			return "Unknown"

	def download_book(self, book_id, download_path, book_format='BRL', s00202_override=None, s00215_override=None):
		"""
		Download a book

		Args:
			book_id (str): ID of the book to download (S00224 value)
			download_path (str): Directory to save the file
			book_format (str): Format of the book - 'BRL' (braille) or 'DAISY'
			s00202_override (str): Actual S00202 value from search results (overrides default)
			s00215_override (str): Actual S00215 value from search results (overrides default; "5" for NDL source)

		Returns:
			tuple: (success: bool, file_path: str or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ダウンロードする前にログインしてください。")

		try:
			log.info(f"Starting download: book_id={book_id}, format={book_format}, s00202_override={s00202_override}, s00215_override={s00215_override}, path={download_path}")

			# Validate book_id
			if not book_id or book_id == "0":
				return (False, "無効な図書IDです。検索結果から有効な図書を選択してください。")

			# Check if this is a National Diet Library (NDL) source
			is_ndl_source = (s00215_override == "5")

			if is_ndl_source:
				log.info("Detected National Diet Library source - using NDL download method")
				return self._download_ndl_book(book_id, download_path, book_format)

			# Extract session tokens (should be current)
			self._extract_session_tokens()

			# Validate session tokens
			if not self.session_tokens.get('S00102') or not self.session_tokens.get('S00103'):
				log.error("Session tokens missing")
				return (False, "セッショントークンが見つかりません。再度ログインしてください。")

			# Determine form values based on format
			# For braille: S00101 = "J31DWN17", S00202 = "11"
			# For DAISY: S00101 = "J31DWN21", S00202 = "22" (audio) or "33" (text)
			if book_format == 'DAISY':
				s00101_value = 'J31DWN21'  # DAISY download action
				# Use actual S00202 from search results if available, otherwise default to audio DAISY
				s00202_value = s00202_override if s00202_override else '22'
				return_page = 'J01LST11'  # DAISY results page
			else:
				s00101_value = 'J31DWN17'  # Braille download action
				# Use actual S00202 from search results if available, otherwise default to braille
				s00202_value = s00202_override if s00202_override else '11'
				return_page = 'J01LST01'  # Braille results page

			# Determine S00215 value (priority/source)
			# Use actual S00215 from search results if available
			# Default: "1" for Sapie source
			if s00215_override:
				s00215_value = s00215_override
			else:
				s00215_value = '1'  # Default to Sapie source

			# Prepare form data for download POST request
			# Based on HTML analysis: POST to https://cntdwn.sapie.or.jp/download/download.aspx
			form_data = {
				'S00101': s00101_value,  # Download action (different for braille vs DAISY)
				'S00102': self.session_tokens.get('S00102', ''),
				'S00103': self.session_tokens.get('S00103', ''),
				'RTNTME': self.session_tokens.get('RTNTME', ''),
				'S00202': s00202_value,  # Data type (11 = braille, 22 = DAISY)
				'S00215': s00215_value,  # Priority/source (1 = Sapie)
				'S00224': book_id,  # Book ID
				'S00263': return_page  # Return page
			}

			log.info(f"Form data prepared: book_id={book_id}, S00101={s00101_value}, S00202={s00202_value}, S00215={s00215_value}")

			# Configure download directory using Chrome DevTools Protocol
			try:
				if hasattr(self.driver, 'execute_cdp_cmd'):
					# Chrome/Edge supports CDP
					self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
						'behavior': 'allow',
						'downloadPath': download_path
					})
					log.info("Download path configured via CDP")
			except Exception as cdp_error:
				log.warning(f"CDP command failed, continuing anyway: {cdp_error}")

			# Submit the download form using JavaScript
			download_url = "https://cntdwn.sapie.or.jp/download/download.aspx"

			# Create and submit form via JavaScript
			js_code = f"""
			var form = document.createElement('form');
			form.method = 'POST';
			form.action = '{download_url}';
			"""

			for key, value in form_data.items():
				js_code += f"""
				var input_{key} = document.createElement('input');
				input_{key}.type = 'hidden';
				input_{key}.name = '{key}';
				input_{key}.value = '{value}';
				form.appendChild(input_{key});
				"""

			js_code += """
			document.body.appendChild(form);
			form.submit();
			"""

			log.info("Submitting download form via JavaScript")
			try:
				self.driver.execute_script(js_code)
			except WebDriverException as wd_error:
				log.error(f"WebDriver error during form submission: {wd_error}")
				return (False, f"ダウンロードフォームの送信に失敗しました: {str(wd_error)}")

			# Wait for download to start
			# The download page may redirect or show a download dialog
			time.sleep(5)

			# Check current URL to see if download was triggered
			try:
				current_url = self.driver.current_url
				log.warning(f"After download submit, current URL: {current_url}")

				# Check for error messages on the page
				page_source = self.driver.page_source
				if "エラー" in page_source or "error" in page_source.lower():
					log.warning("Error message detected on download page")

					# Save error page for debugging
					try:
						error_page_path = os.path.join(download_path, "sapie_error_page.html")
						with open(error_page_path, "w", encoding="utf-8") as f:
							f.write(page_source)
						log.warning(f"Error page saved to: {error_page_path}")
					except Exception as save_error:
						log.warning(f"Could not save error page: {save_error}")

					# Try to extract error message
					try:
						error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'エラー')]")
						if error_elements:
							error_text = error_elements[0].text
							log.warning(f"Extracted error text: {error_text}")
							return (False, f"ダウンロードエラー: {error_text}")
					except:
						pass

					# Look for any visible text on the page
					try:
						body_text = self.driver.find_element(By.TAG_NAME, "body").text
						log.warning(f"Page body text (first 500 chars): {body_text[:500]}")
					except:
						pass

					return (False, f"ダウンロード中にエラーが発生しました。エラーページを{download_path}\\sapie_error_page.htmlで確認してください。")
			except WebDriverException as wd_error:
				log.warning(f"Could not check page after download: {wd_error}")
				# Continue anyway - download may have succeeded

			# Construct expected filename (this is a guess - may need adjustment)
			# Sapie typically uses BES (Braille Editing System) format
			filename = f"{book_id}.zip"  # or .bes
			file_path = os.path.join(download_path, filename)

			log.info(f"Download initiated for: {file_path}")
			return (True, file_path)

		except WebDriverException as wd_error:
			log.error(f"WebDriver error: {wd_error}", exc_info=True)
			return (False, f"ブラウザエラー: {str(wd_error)}")
		except Exception as e:
			log.error(f"Download error: {e}", exc_info=True)
			return (False, f"ダウンロードエラー: {str(e)}")

	def _download_ndl_book(self, book_id, download_path, book_format='BRL'):
		"""
		Download a book from National Diet Library (NDL) source

		This method handles NDL downloads by finding and clicking the NDL download button
		on the search results page.

		Args:
			book_id (str): ID of the book to download (S00224 value)
			download_path (str): Directory to save the file
			book_format (str): Format of the book - 'BRL' (braille) or 'DAISY'

		Returns:
			tuple: (success: bool, file_path: str or error_message: str)
		"""
		try:
			log.info(f"Starting NDL download for book_id={book_id}")

			# Configure download directory using Chrome DevTools Protocol
			try:
				if hasattr(self.driver, 'execute_cdp_cmd'):
					self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
						'behavior': 'allow',
						'downloadPath': download_path
					})
					log.info("Download path configured via CDP for NDL download")
			except Exception as cdp_error:
				log.warning(f"CDP command failed: {cdp_error}")

			# Find the NDL download button for this book
			# The button should be in the same table row that contains the book_id
			try:
				# Find the download button by looking for the button/form with S00224 = book_id
				# and containing "国会からダウン" text or having S00215="5"

				# Method 1: Try to find by button text
				ndl_button = None
				try:
					# Look for the specific form with S00224 matching our book_id
					xpath_query = f"//input[@name='S00224'][@value='{book_id}']/ancestor::form//button[contains(text(), '国会')]"
					ndl_button = self.driver.find_element(By.XPATH, xpath_query)
					log.info("Found NDL download button by text")
				except NoSuchElementException:
					log.info("Could not find NDL button by text, trying alternative method")

				# Method 2: Try to find by S00215 value
				if not ndl_button:
					try:
						xpath_query = f"//input[@name='S00224'][@value='{book_id}']/ancestor::form[.//input[@name='S00215'][@value='5']]//button[@type='submit']"
						ndl_button = self.driver.find_element(By.XPATH, xpath_query)
						log.info("Found NDL download button by S00215 value")
					except NoSuchElementException:
						log.info("Could not find NDL button by S00215 value")

				# Method 3: Try to find any submit button in a form with S00215="5" and our book_id
				if not ndl_button:
					try:
						xpath_query = f"//form[.//input[@name='S00224'][@value='{book_id}'] and .//input[@name='S00215'][@value='5']]//input[@type='submit']"
						ndl_button = self.driver.find_element(By.XPATH, xpath_query)
						log.info("Found NDL download submit input by S00215 value")
					except NoSuchElementException:
						log.error("Could not find NDL download button using any method")
						return (False, "国会図書館のダウンロードボタンが見つかりませんでした。検索結果ページを再読み込みしてください。")

				if ndl_button:
					log.info("Clicking NDL download button")
					ndl_button.click()

					# Wait for download to start or redirect
					time.sleep(5)

					# Check for errors
					page_source = self.driver.page_source
					if "エラー" in page_source or "error" in page_source.lower():
						log.warning("Error detected on NDL download page")

						# Save error page for debugging
						try:
							error_page_path = os.path.join(download_path, "sapie_ndl_error_page.html")
							with open(error_page_path, "w", encoding="utf-8") as f:
								f.write(page_source)
							log.warning(f"NDL error page saved to: {error_page_path}")
						except Exception as save_error:
							log.warning(f"Could not save error page: {save_error}")

						# Try to extract error message
						try:
							error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'エラー')]")
							if error_elements:
								error_text = error_elements[0].text
								log.warning(f"Extracted error text: {error_text}")
								return (False, f"国会図書館ダウンロードエラー: {error_text}")
						except:
							pass

						return (False, f"国会図書館からのダウンロード中にエラーが発生しました。エラーページを{download_path}\\sapie_ndl_error_page.htmlで確認してください。")

					# Construct expected filename
					filename = f"{book_id}.zip"
					file_path = os.path.join(download_path, filename)

					log.info(f"NDL download initiated for: {file_path}")
					return (True, file_path)
				else:
					return (False, "国会図書館のダウンロードボタンが見つかりませんでした。")

			except NoSuchElementException as e:
				log.error(f"Could not find NDL download button: {e}")
				return (False, f"国会図書館のダウンロードボタンが見つかりませんでした: {str(e)}")

		except Exception as e:
			log.error(f"NDL download error: {e}", exc_info=True)
			return (False, f"国会図書館ダウンロードエラー: {str(e)}")

	def search_online_request(self, search_params=None):
		"""
		Search for online request books in Sapie Library

		Args:
			search_params (dict): Search parameters:
				- title (str): Title search query (S00251)
				- author (str): Author search query (S00252)
				- material_type (str): Material type (S00201): "11"=braille, "22"=DAISY audio, etc.
				- category (str): Category (S00218): "1", "2", "3"
				- completion_date_from (str): Completion date from (S00226) format: YYYYMMDD
				- completion_date_to (str): Completion date to (S00227) format: YYYYMMDD

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "検索する前にログインしてください。")

		# Default search params
		if search_params is None:
			search_params = {}

		title = search_params.get("title", "")
		author = search_params.get("author", "")
		material_type = search_params.get("material_type", "")
		category = search_params.get("category", "")
		completion_date_from = search_params.get("completion_date_from", "")
		completion_date_to = search_params.get("completion_date_to", "")

		try:
			log.info(f"Starting online request search: title='{title}', author='{author}', material_type='{material_type}', category='{category}'")

			# Extract session tokens from current page first
			self._extract_session_tokens()

			# Navigate to online request search page (オンラインリクエスト検索)
			search_page_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SCH02&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"

			log.info(f"Navigating to online request search page: {search_page_url}")
			self.driver.get(search_page_url)

			# Wait for search page to load by waiting for title field
			wait = WebDriverWait(self.driver, 10)
			wait.until(EC.presence_of_element_located((By.ID, "S00251")))

			# Extract session tokens again from the search page
			self._extract_session_tokens()

			# Find and fill title search field (S00251)
			if title:
				log.info("Looking for title field (S00251)...")
				title_field = wait.until(
					EC.presence_of_element_located((By.ID, "S00251"))
				)
				title_field.clear()
				title_field.send_keys(title)
				log.info(f"Title field filled with: {title}")

			# Find and fill author search field (S00252)
			if author:
				log.info("Looking for author field (S00252)...")
				try:
					author_field = self.driver.find_element(By.ID, "S00252")
					author_field.clear()
					author_field.send_keys(author)
					log.info(f"Author field filled with: {author}")
				except:
					log.warning("Author field not found")

			# Set material type - S00201
			if material_type:
				log.info(f"Setting material type (S00201) to: {material_type}")
				try:
					material_type_select = self.driver.find_element(By.ID, "S00201")
					material_type_select.send_keys(Keys.HOME)  # Reset selection
					# Find the option with the value
					option = material_type_select.find_element(By.XPATH, f".//option[@value='{material_type}']")
					option.click()
					log.info(f"Material type set to: {material_type}")
				except Exception as e:
					log.warning(f"Could not set material type: {e}")

			# Set category - S00218
			if category:
				log.info(f"Setting category (S00218) to: {category}")
				try:
					category_select = self.driver.find_element(By.ID, "S00218")
					category_select.send_keys(Keys.HOME)  # Reset selection
					# Find the option with the value
					option = category_select.find_element(By.XPATH, f".//option[@value='{category}']")
					option.click()
					log.info(f"Category set to: {category}")
				except Exception as e:
					log.warning(f"Could not set category: {e}")

			# Set completion date from - S00226
			if completion_date_from:
				log.info(f"Setting completion date from (S00226) to: {completion_date_from}")
				try:
					date_from_field = self.driver.find_element(By.ID, "S00226")
					date_from_field.clear()
					date_from_field.send_keys(completion_date_from)
					log.info(f"Completion date from set to: {completion_date_from}")
				except Exception as e:
					log.warning(f"Could not set completion date from: {e}")

			# Set completion date to - S00227
			if completion_date_to:
				log.info(f"Setting completion date to (S00227) to: {completion_date_to}")
				try:
					date_to_field = self.driver.find_element(By.ID, "S00227")
					date_to_field.clear()
					date_to_field.send_keys(completion_date_to)
					log.info(f"Completion date to set to: {completion_date_to}")
				except Exception as e:
					log.warning(f"Could not set completion date to: {e}")

			# Submit search (検索開始 button)
			log.info("Looking for search button...")
			search_buttons = self.driver.find_elements(By.XPATH, "//input[@type='submit'][@value='検索開始']")
			if search_buttons:
				log.info("Clicking search button...")
				search_buttons[0].click()
			else:
				return (False, "検索ボタンが見つかりませんでした")

			# Wait for results page to load
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source or
					"検索結果：0件" in driver.page_source
				)
				log.info(f"Results page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("Results page load timeout, continuing anyway")
				log.info(f"Results page URL: {self.driver.current_url}")

			# Parse results from all pages (handle pagination)
			all_results = []
			page_num = 1
			max_pages = 10  # Safety limit to prevent infinite loops

			while page_num <= max_pages:
				log.info(f"Parsing online request page {page_num}...")

				# Parse current page
				page_results = self._parse_online_request_results()
				all_results.extend(page_results)

				log.info(f"Found {len(page_results)} results on page {page_num}, total so far: {len(all_results)}")

				# Check if there's a "Next" link
				try:
					next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
					if next_links:
						log.info(f"Found 'Next' link, navigating to page {page_num + 1}")
						next_links[0].click()

						# Wait for next page to load
						wait = WebDriverWait(self.driver, 10)
						wait.until(
							lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']")
						)

						page_num += 1
					else:
						log.info("No more pages, finished pagination")
						break
				except Exception as e:
					log.warning(f"Error checking for next page: {e}")
					break

			log.info(f"Finished collecting all online request results: {len(all_results)} total")
			return (True, all_results)

		except TimeoutException:
			log.error("Online request search timeout")
			return (False, "検索がタイムアウトしました")
		except Exception as e:
			log.error(f"Online request search error: {e}", exc_info=True)
			return (False, f"検索エラー: {str(e)}")

	def _parse_online_request_results(self):
		"""
		Parse online request search results from current page using HTML parsing

		Returns:
			list: List of dictionaries containing online request book information
		"""
		results = []

		try:
			log.info("Parsing online request search results...")

			# Get page source and parse with simple string methods (faster than Selenium)
			page_source = self.driver.page_source

			# Check for no results
			if "該当するデータが見つかりませんでした" in page_source or "検索結果：0件" in page_source:
				log.info("No results found")
				return []

			# Use simple HTML parsing instead of Selenium (MUCH faster)
			import re

			# Find all table rows in tbody
			tbody_pattern = r'<tbody>(.*?)</tbody>'
			tbody_match = re.search(tbody_pattern, page_source, re.DOTALL)

			if not tbody_match:
				log.warning("No tbody found in page")
				return []

			tbody_content = tbody_match.group(1)

			# Find all rows
			row_pattern = r'<tr>(.*?)</tr>'
			rows = re.findall(row_pattern, tbody_content, re.DOTALL)

			log.info(f"Found {len(rows)} data rows")

			for i, row_html in enumerate(rows):
				try:
					# Extract cells
					cell_pattern = r'<td[^>]*>(.*?)</td>'
					cells = re.findall(cell_pattern, row_html, re.DOTALL)
					if len(cells) < 3:  # Need at least: number, title, author
						log.warning(f"Row {i+1} has only {len(cells)} cells, skipping")
						continue

					# Column structure for online request:
					# 0: 連番 (serial number)
					# 1: タイトル (title with link)
					# 2: 著者名 (author)
					# 3: 資料種別 (material type)
					# 4: 形態と巻数 (format and volumes)
					# 5: 出版年 (publication year)
					# 6: 製作館 (production library)

					# Column 0: Serial number (連番)
					serial_num = re.sub(r'<[^>]+>', '', cells[0]).strip() if len(cells) > 0 else str(i+1)

					# Column 1: Title with link
					title_match = re.search(r'<a[^>]*>(.*?)</a>', cells[1])
					if title_match:
						title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
						url_match = re.search(r'href="([^"]+)"', cells[1])
						book_url = url_match.group(1) if url_match else ""
					else:
						title = re.sub(r'<[^>]+>', '', cells[1]).strip()
						book_url = ""

					# Column 2: Author
					author = re.sub(r'<[^>]+>', '', cells[2]).strip() if len(cells) > 2 else ""

					# Column 3: Material type (資料種別)
					material_type = re.sub(r'<[^>]+>', '', cells[3]).strip() if len(cells) > 3 else ""

					# Column 4: Format and volumes (形態と巻数)
					format_volumes = re.sub(r'<[^>]+>', '', cells[4]).strip() if len(cells) > 4 else ""

					# Column 5: Publication year (出版年)
					pub_year = re.sub(r'<[^>]+>', '', cells[5]).strip() if len(cells) > 5 else ""

					# Column 6: Production library (製作館)
					production_lib = re.sub(r'<[^>]+>', '', cells[6]).strip() if len(cells) > 6 else ""

					# Extract book ID from URL or link
					# The detail page will contain the request button
					book_id = serial_num  # Use serial number as ID for now

					results.append({
						'id': book_id,
						'title': title,
						'author': author,
						'type': material_type,
						'format': format_volumes,
						'pub_year': pub_year,
						'production_lib': production_lib,
						'url': book_url,
						'is_online_request': True  # Flag to indicate this is an online request result
					})

					if (i+1) % 10 == 0:  # Log every 10 results
						log.info(f"Parsed {i+1} online request results so far...")
					log.info(f"Parsed online request result {i+1}: {title} / {author} (ID: {book_id}, Type: {material_type})")

				except Exception as e:
					log.error(f"Failed to parse online request result row {i}: {e}", exc_info=True)
					continue

			log.info(f"Finished parsing loop, total online request results: {len(results)}")

			# If no results found
			if not results:
				# Check if there's a "no results" message
				if "該当するデータが見つかりませんでした" in page_source or "検索結果：0件" in page_source:
					log.info("No results found message detected")
					results.append({
						'id': '0',
						'title': '（検索結果が見つかりませんでした）',
						'author': '',
						'type': '',
						'format': '',
						'pub_year': '',
						'production_lib': '',
						'is_online_request': True
					})
				else:
					log.warning("Could not parse results - returning placeholder")
					results.append({
						'id': '0',
						'title': '（検索結果のパースに失敗しました。NVDAログを確認してください）',
						'author': '',
						'type': '',
						'format': '',
						'pub_year': '',
						'production_lib': '',
						'is_online_request': True
					})

		except Exception as e:
			log.error(f"Online request result parsing error: {e}", exc_info=True)
			results.append({
				'id': '0',
				'title': f'結果解析エラー: {str(e)}',
				'author': '',
				'type': '',
				'format': '',
				'pub_year': '',
				'production_lib': '',
				'is_online_request': True
			})

		return results

	def get_new_arrivals(self, book_type="braille", period="week"):
		"""
		Get new arrivals (newly completed books) from Sapie Library

		Args:
			book_type (str): Type of book - "braille" or "daisy"
			period (str): Time period - "week" (1週間) or "month" (1ヶ月)

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Getting new arrivals: type='{book_type}', period='{period}'")

			# Extract session tokens
			self._extract_session_tokens()

			# Navigate directly to new arrivals results page
			# S00101=J02LST01 (new arrivals list)
			# S00213: 1=braille, 2=audio/DAISY
			# S00214: 1=1 week, 2=1 month
			list_action = "J02LST01"

			# Set S00213 based on book type
			if book_type == "braille":
				s00213 = "1"
			else:
				s00213 = "2"

			# Set S00214 based on period
			if period == "month":
				s00214 = "2"
			else:
				s00214 = "1"

			new_arrivals_url = f"{self.LIBRARY_BASE_URL}?S00101={list_action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00213={s00213}&S00214={s00214}&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Navigating to new arrivals page: {new_arrivals_url}")
			self.driver.get(new_arrivals_url)

			# Wait for results page to load
			wait = WebDriverWait(self.driver, 10)
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source
				)
				log.info(f"New arrivals page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("New arrivals page load timeout, continuing anyway")

			# Parse results from all pages
			all_results = []
			page_num = 1
			max_pages = 10

			while page_num <= max_pages:
				log.info(f"Parsing new arrivals page {page_num}...")

				# Parse current page
				page_results = self._parse_search_results(book_type)
				all_results.extend(page_results)

				log.info(f"Found {len(page_results)} results on page {page_num}, total so far: {len(all_results)}")

				# Check if there's a "Next" link
				try:
					next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
					if next_links:
						log.info(f"Found 'Next' link, navigating to page {page_num + 1}")
						next_links[0].click()

						# Wait for next page to load
						wait = WebDriverWait(self.driver, 10)
						wait.until(
							lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']")
						)

						page_num += 1
					else:
						log.info("No more pages, finished pagination")
						break
				except Exception as e:
					log.warning(f"Error checking for next page: {e}")
					break

			log.info(f"Finished collecting all new arrivals: {len(all_results)} total")
			return (True, all_results)

		except TimeoutException:
			log.error("New arrivals timeout")
			return (False, "新着情報の取得がタイムアウトしました")
		except Exception as e:
			log.error(f"New arrivals error: {e}", exc_info=True)
			return (False, f"新着情報取得エラー: {str(e)}")

	def get_popular_books(self, book_type="braille", ranking_type="download"):
		"""
		Get popular books from Sapie Library

		Args:
			book_type (str): Type of book - "braille" or "daisy"
			ranking_type (str): Type of ranking - "download" or "request"

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Getting popular books: type='{book_type}', ranking='{ranking_type}'")

			# Extract session tokens
			self._extract_session_tokens()

			# Navigate directly to popular books results page
			# S00101=J03LST01 (popular books list)
			# S00201: Type of ranking
			#   1 = Braille download
			#   3 = DAISY download
			#   4 = DAISY playback
			#   21 = Braille online request
			#   22 = Audio/DAISY online request
			# S00212: Category (1=books, 2=serials, 3=other)
			list_action = "J03LST01"

			# Set S00201 based on book type and ranking type
			if book_type == "braille":
				if ranking_type == "request":
					s00201 = "21"  # Braille online request
				else:
					s00201 = "1"   # Braille download
			else:  # daisy
				if ranking_type == "request":
					s00201 = "22"  # Audio/DAISY online request
				else:
					s00201 = "3"   # DAISY download

			# Default to books only
			s00212 = "1"

			# No date range specified (will default to past 30 days)
			popular_url = f"{self.LIBRARY_BASE_URL}?S00101={list_action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00201={s00201}&S00212={s00212}&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Navigating to popular books page: {popular_url}")
			self.driver.get(popular_url)

			# Wait for results page to load
			wait = WebDriverWait(self.driver, 10)
			try:
				wait.until(
					lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']") or
					"該当するデータが見つかりませんでした" in driver.page_source
				)
				log.info(f"Popular books page loaded: {self.driver.current_url}")
			except TimeoutException:
				log.warning("Popular books page load timeout, continuing anyway")

			# Parse results from all pages
			all_results = []
			page_num = 1
			max_pages = 10

			while page_num <= max_pages:
				log.info(f"Parsing popular books page {page_num}...")

				# Parse current page
				page_results = self._parse_search_results(book_type)
				all_results.extend(page_results)

				log.info(f"Found {len(page_results)} results on page {page_num}, total so far: {len(all_results)}")

				# Check if there's a "Next" link
				try:
					next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '次へ')]")
					if next_links:
						log.info(f"Found 'Next' link, navigating to page {page_num + 1}")
						next_links[0].click()

						# Wait for next page to load
						wait = WebDriverWait(self.driver, 10)
						wait.until(
							lambda driver: driver.find_elements(By.XPATH, "//table[@class='FULL']")
						)

						page_num += 1
					else:
						log.info("No more pages, finished pagination")
						break
				except Exception as e:
					log.warning(f"Error checking for next page: {e}")
					break

			log.info(f"Finished collecting all popular books: {len(all_results)} total")
			return (True, all_results)

		except TimeoutException:
			log.error("Popular books timeout")
			return (False, "人気のある本の取得がタイムアウトしました")
		except Exception as e:
			log.error(f"Popular books error: {e}", exc_info=True)
			return (False, f"人気のある本取得エラー: {str(e)}")

	def is_logged_in(self):
		"""Check if currently logged in"""
		return self.logged_in

	def close(self):
		"""Close the browser and clean up"""
		if self.driver:
			try:
				self.driver.quit()
			except:
				pass
			self.driver = None
			self.logged_in = False

	def __del__(self):
		"""Destructor - ensure browser is closed"""
		self.close()
