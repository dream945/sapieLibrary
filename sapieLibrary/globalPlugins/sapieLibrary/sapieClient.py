# -*- coding: utf-8 -*-
# Sapie Library Client - requests + BeautifulSoup based implementation

import time
import logging
import re

# Import requests and BeautifulSoup
try:
	import requests
	from bs4 import BeautifulSoup
except ImportError as e:
	raise ImportError(f"Required libraries not found: {e}")

# Set up logging
log = logging.getLogger(__name__)

class SapieClient:
	"""Client for accessing Sapie Library using requests"""

	def __init__(self):
		"""Initialize the Sapie client"""
		self.session = requests.Session()
		self.LOGIN_URL = "https://member.sapie.or.jp/login"
		self.LIBRARY_BASE_URL = "https://library.sapie.or.jp/cgi-bin/CN1MN1"
		self.logged_in = False
		self.session_tokens = {}
		self.username = None

		# Disable proxy to avoid connection issues
		self.session.trust_env = False
		self.session.proxies = {'http': None, 'https': None}

		# Set user agent to avoid being blocked
		self.session.headers.update({
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
		})

		log.info("SapieClient initialized with requests")

	def login(self, username, password):
		"""
		Login to Sapie Library

		Args:
			username (str): Sapie user ID
			password (str): Password

		Returns:
			tuple: (success: bool, message: str)
		"""
		try:
			log.info(f"Attempting login for user: {username}")

			# First, get the login page to extract CSRF token and cookies
			response = self.session.get(self.LOGIN_URL)
			response.encoding = 'shift_jis'

			if response.status_code != 200:
				log.error(f"Failed to access login page: {response.status_code}")
				return (False, f"ログインページにアクセスできませんでした: {response.status_code}")

			# Parse the page to get CSRF token
			soup = BeautifulSoup(response.text, 'html.parser')

			# Extract CSRF token (Rails uses authenticity_token)
			csrf_token = None
			csrf_input = soup.find('input', {'name': 'authenticity_token'})
			if csrf_input:
				csrf_token = csrf_input.get('value')
				log.info(f"Found CSRF token")

			# Prepare login data (Rails form format)
			login_data = {
				'uid': username,
				'password': password,
				'commit': 'ログイン'
			}

			# Add CSRF token if found
			if csrf_token:
				login_data['authenticity_token'] = csrf_token

			log.info(f"Submitting login with fields: {list(login_data.keys())}")

			# Submit login form
			response = self.session.post(self.LOGIN_URL, data=login_data, allow_redirects=True)
			response.encoding = 'shift_jis'

			log.info(f"Login response URL: {response.url}")
			log.info(f"Login response status: {response.status_code}")

			# Parse the response to check for errors first
			# Use response.content with explicit encoding to avoid mojibake
			soup = BeautifulSoup(response.content, 'html.parser', from_encoding='shift_jis')

			# Check for login error in page title (most reliable check)
			page_title = soup.find('p', class_='acc')
			if page_title and 'ログインエラー' in page_title.get_text():
				log.error("Login failed: Error found in page title")
				# Extract specific error message
				error_div = soup.find('div', {'id': 'errorExplanation'}) or soup.find('div', class_='error')
				if error_div:
					error_li = error_div.find('li')
					if error_li:
						error_text = error_li.get_text(strip=True)
						return (False, f"ログインエラー: {error_text}")
					error_text = error_div.get_text(strip=True)
					return (False, error_text)
				return (False, "ログインに失敗しました。ユーザーIDまたはパスワードが正しくありません。")

			# Check for error div with id errorExplanation
			error_div = soup.find('div', {'id': 'errorExplanation'})
			if error_div:
				error_li = error_div.find('li')
				if error_li:
					error_text = error_li.get_text(strip=True)
					log.error(f"Login failed: {error_text}")
					return (False, f"ログインエラー: {error_text}")

			# Check if login was successful by checking the final URL
			# Successful login should redirect to member page or library
			if "member" in response.url or "library" in response.url:
				self.logged_in = True
				self.username = username
				self._extract_session_tokens()
				log.info("Login successful")
				return (True, f"ログイン成功: {username}")

			# Check for other error messages in the response
			if "エラー" in response.text or "error" in response.text.lower():
				error_div = soup.find('div', class_='error') or soup.find('div', class_='alert')
				if error_div:
					error_text = error_div.get_text(strip=True)
					log.error(f"Login failed: {error_text}")
					return (False, error_text)

			log.error("Login failed: Unknown error")
			return (False, "ログインに失敗しました。ユーザーIDまたはパスワードが正しくありません。")

		except requests.exceptions.RequestException as e:
			log.error(f"Network error during login: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Login error: {e}", exc_info=True)
			return (False, f"ログインエラー: {str(e)}")

	def search(self, book_type="braille", search_params=None):
		"""
		Search for books

		Args:
			book_type (str): Type of book - "braille" or "daisy"
			search_params (dict): Search parameters (title, author, etc.)

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		if search_params is None:
			search_params = {}

		try:
			log.info(f"Searching: type={book_type}, params={search_params}")

			# Extract current session tokens
			self._extract_session_tokens()

			# Step 1: Navigate to search page
			if book_type == "braille":
				search_action = "J01SCH01"  # Braille search
			else:
				search_action = "J01SCH08"  # DAISY search

			search_page_url = f"{self.LIBRARY_BASE_URL}?S00101={search_action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"

			log.info(f"Navigating to search page: {search_page_url}")
			response = self.session.get(search_page_url)
			response.encoding = 'shift_jis'

			# Extract ALL form fields from search page
			soup = BeautifulSoup(response.text, 'html.parser')

			# Get all hidden fields from the form
			search_data = {}
			for hidden in soup.find_all('input', type='hidden'):
				name = hidden.get('name')
				value = hidden.get('value', '')
				if name:
					search_data[name] = value
					self.session_tokens[name] = value

			# Add search parameters
			search_data['S00251'] = search_params.get('title', '')  # Title
			search_data['S00252'] = search_params.get('author', '')  # Author
			search_data['S00218'] = search_params.get('category', '')  # Category (種別)

			# Include NDL checkbox
			if search_params.get('include_ndl', True):
				search_data['S00262'] = '5'

			# Log search parameters (safely handle encoding issues)
			try:
				title_log = search_data.get('S00251', '').encode('ascii', errors='replace').decode('ascii')
				author_log = search_data.get('S00252', '').encode('ascii', errors='replace').decode('ascii')
				log.info(f"Submitting search with title='{title_log}', author='{author_log}'")
			except:
				log.info("Submitting search")

			# Encode POST data as Shift_JIS for Japanese text
			import urllib.parse

			# Manually URL encode with shift_jis to handle encoding errors gracefully
			encoded_parts = []
			for key, value in search_data.items():
				# Encode key and value to shift_jis bytes, ignoring problematic characters
				if isinstance(key, str):
					key_bytes = key.encode('shift_jis', errors='ignore')
				else:
					key_bytes = str(key).encode('shift_jis', errors='ignore')

				if isinstance(value, str):
					value_bytes = value.encode('shift_jis', errors='ignore')
				else:
					value_bytes = str(value).encode('shift_jis', errors='ignore')

				# URL encode the bytes
				encoded_key = urllib.parse.quote_from_bytes(key_bytes)
				encoded_value = urllib.parse.quote_from_bytes(value_bytes)

				encoded_parts.append(f'{encoded_key}={encoded_value}')

			# Join all parts with &
			encoded_body = '&'.join(encoded_parts)

			# Send the encoded body as bytes
			response = self.session.post(
				self.LIBRARY_BASE_URL,
				data=encoded_body.encode('ascii'),  # Already URL-encoded, so ASCII is fine
				headers={'Content-Type': 'application/x-www-form-urlencoded'}
			)
			response.encoding = 'shift_jis'

			# DEBUG: Save response HTML to file
			import os
			debug_file = os.path.join(os.path.expanduser('~'), 'sapie_search_debug.html')
			try:
				with open(debug_file, 'w', encoding='shift_jis', errors='ignore') as f:
					f.write(response.text)
				log.info(f"DEBUG: Response HTML saved to {debug_file}")
			except Exception as e:
				log.warning(f"Could not save debug file: {e}")

			# Parse results from all pages
			all_results = []
			current_page = 1
			max_pages = 100  # Safety limit to prevent infinite loops

			while current_page <= max_pages:
				soup = BeautifulSoup(response.text, 'html.parser')

				# Check for "no results" message
				if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
					log.info("No results found")
					break

				# Parse search results from current page
				page_results = self._parse_search_results(soup, book_type)
				all_results.extend(page_results)
				log.info(f"Page {current_page}: {len(page_results)} results (total: {len(all_results)})")

				# Check if there's a next page
				next_page_url = self._has_next_page(soup)
				if not next_page_url:
					log.info("No more pages")
					break

				# Get next page
				try:
					current_page += 1
					# Construct full URL
					if next_page_url.startswith('http'):
						full_url = next_page_url
					else:
						# Relative URL, prepend base URL
						full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

					log.info(f"Requesting page {current_page}: {full_url}")

					# Request next page with GET
					response = self.session.get(full_url)
					response.encoding = 'shift_jis'

				except Exception as e:
					log.error(f"Error fetching next page: {e}")
					break

			if all_results:
				log.info(f"Search successful: {len(all_results)} total results from {current_page} page(s)")
				return (True, all_results)
			else:
				log.info("Search returned no results")
				return (True, [])

		except requests.exceptions.RequestException as e:
			log.error(f"Network error during search: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Search error: {e}", exc_info=True)
			return (False, f"検索エラー: {str(e)}")

	def _extract_session_tokens(self):
		"""Extract session tokens from current page"""
		try:
			# Get current page to extract tokens
			response = self.session.get(self.LIBRARY_BASE_URL)
			response.encoding = 'shift_jis'

			soup = BeautifulSoup(response.text, 'html.parser')

			# Find hidden input fields with session tokens
			for hidden in soup.find_all('input', type='hidden'):
				name = hidden.get('name')
				value = hidden.get('value')
				if name and value:
					self.session_tokens[name] = value

			log.debug(f"Extracted session tokens: {list(self.session_tokens.keys())}")

		except Exception as e:
			log.error(f"Error extracting session tokens: {e}")

	def _has_next_page(self, soup):
		"""
		Check if there's a next page in search results

		Args:
			soup (BeautifulSoup): Parsed HTML of current search results page

		Returns:
			str or None: URL of next page if exists, None otherwise
		"""
		try:
			# Look for "次へ" (Next) link in pager
			pager = soup.find('ul', class_='pager')
			if pager:
				links = pager.find_all('a')
				for link in links:
					link_text = link.get_text(strip=True)
					if '次' in link_text:
						next_url = link.get('href', '')
						if next_url:
							log.info(f"Next page detected: {link_text}")
							return next_url

			log.info("No next page detected")
			return None

		except Exception as e:
			log.warning(f"Error checking for next page: {e}")
			return None

	def _parse_search_results(self, soup, book_type="braille"):
		"""
		Parse search results from HTML

		Args:
			soup (BeautifulSoup): Parsed HTML
			book_type (str): Type of book

		Returns:
			list: List of result dictionaries
		"""
		results = []

		try:
			# Find the results table
			table = soup.find('table', class_='FULL')

			if not table:
				log.warning("No results table found")
				return results

			# Parse each row (skip header row)
			rows = table.find_all('tr')[1:]

			for row in rows:
				cols = row.find_all('td')

				if len(cols) < 3:  # Need at least: number, title, author
					continue

				# Column 0: Row number (skip)
				# Column 1: Title with link
				# Column 2: Author
				# Last column: Download form

				# Extract book ID from the download form (last column)
				download_cell = cols[-1]
				book_id = None

				# Try to find S00224 (book ID) in the download form
				s00224_input = download_cell.find('input', {'name': 'S00224'})
				if s00224_input:
					book_id = s00224_input.get('value', '')

				# If not found, try to extract from link
				if not book_id and len(cols) > 1:
					link = cols[1].find('a')
					if link and link.get('href'):
						match = re.search(r'S00224=([^&]+)', link.get('href'))
						if match:
							book_id = match.group(1)

				# Extract title (column 1) and detail link parameters
				title = ''
				s00221 = ''
				s00222 = ''
				if len(cols) > 1:
					title_link = cols[1].find('a')
					if title_link:
						title = title_link.get_text(strip=True)
						# Extract S00221 and S00222 from detail link
						href = title_link.get('href', '')
						s00221_match = re.search(r'S00221=([^&]+)', href)
						s00222_match = re.search(r'S00222=([^&]+)', href)
						if s00221_match:
							s00221 = s00221_match.group(1)
						if s00222_match:
							s00222 = s00222_match.group(1)
					else:
						title = cols[1].get_text(strip=True)

				# Extract author (column 2)
				author = ''
				if len(cols) > 2:
					author = cols[2].get_text(strip=True)

				# Extract type from download form
				result_type = '不明'
				s00202_input = download_cell.find('input', {'name': 'S00202'})
				if s00202_input:
					s00202_value = s00202_input.get('value', '')
					if s00202_value == "11":
						result_type = '点字'
					elif s00202_value == "22":
						result_type = 'デイジー(音声)'
					elif s00202_value == "33":
						result_type = 'デイジー(テキスト)'

				result = {
					'id': book_id or '',
					'title': title,
					'author': author,
					'type': result_type,
					'producer': '',  # Not extracted for now
					's00202': s00202_value if s00202_input else '',  # Store for download
					's00215': '',  # Could extract from download form if needed
					's00221': s00221,  # Search ID for detail page
					's00222': s00222   # Book ID for detail page
				}

				results.append(result)
				log.debug(f"Parsed result: {result['title']}")

		except Exception as e:
			log.error(f"Error parsing search results: {e}", exc_info=True)

		return results

	def is_logged_in(self):
		"""Check if user is logged in"""
		return self.logged_in

	def download_book(self, book_id, download_path, book_format='BRL', s00202_override=None, s00215_override=None):
		"""
		Download a book

		Args:
			book_id (str): ID of the book to download (S00224 value)
			download_path (str): Directory to save the file
			book_format (str): Format of the book - 'BRL' (braille) or 'DAISY'
			s00202_override (str): Actual S00202 value from search results
			s00215_override (str): Actual S00215 value from search results

		Returns:
			tuple: (success: bool, file_path: str or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ダウンロードする前にログインしてください。")

		try:
			import os
			log.info(f"Starting download: book_id={book_id}, format={book_format}, path={download_path}")

			# Validate book_id
			if not book_id or book_id == "0":
				return (False, "この図書はダウンロードできない資料です。\nコンテンツが登録されていないか、現物貸出のみの資料の可能性があります。")

			# Extract session tokens
			self._extract_session_tokens()

			# Determine form values based on format
			if book_format == 'DAISY':
				s00101_value = 'J31DWN21'  # DAISY download action
				s00202_value = s00202_override if s00202_override else '22'
				return_page = 'J01LST11'
			else:
				s00101_value = 'J31DWN17'  # Braille download action
				s00202_value = s00202_override if s00202_override else '11'
				return_page = 'J01LST01'

			# Determine S00215 value (source)
			s00215_value = s00215_override if s00215_override else '1'

			# Prepare form data
			form_data = {
				'S00101': s00101_value,
				'S00102': self.session_tokens.get('S00102', ''),
				'S00103': self.session_tokens.get('S00103', ''),
				'RTNTME': self.session_tokens.get('RTNTME', ''),
				'S00202': s00202_value,
				'S00215': s00215_value,
				'S00224': book_id,
				'S00263': return_page
			}

			log.info(f"Downloading book_id={book_id}, S00202={s00202_value}")

			# Submit download request
			download_url = "https://cntdwn.sapie.or.jp/download/download.aspx"
			response = self.session.post(download_url, data=form_data, stream=True)

			log.info(f"Response status: {response.status_code}")

			# Check for errors in response
			if response.status_code != 200:
				log.error(f"Download failed: HTTP {response.status_code}")
				return (False, f"ダウンロード失敗: HTTP {response.status_code}")

			# Get filename from Content-Disposition header
			filename = None
			if 'Content-Disposition' in response.headers:
				from urllib.parse import unquote
				cd = response.headers['Content-Disposition']
				filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', cd)
				if filename_match:
					filename = filename_match.group(1).strip('"\'')
					# URL decode the filename
					filename = unquote(filename)
					log.info(f"Decoded filename: {filename}")

			# If no filename in header, generate one
			if not filename:
				# Determine extension based on format
				if book_format == 'DAISY':
					ext = '.zip'
				else:
					ext = '.zip'  # Braille is also usually .zip
				filename = f"sapie_book_{book_id}{ext}"

			# Sanitize filename - remove invalid characters and limit length
			import string
			valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
			# Keep Japanese characters too
			filename = ''.join(c if c in valid_chars or ord(c) > 127 else '_' for c in filename)
			# Limit filename length (keep extension)
			name_part, ext_part = os.path.splitext(filename)
			if len(name_part) > 100:
				name_part = name_part[:100]
			filename = name_part + ext_part
			log.info(f"Sanitized filename: {filename}")

			# Save file
			file_path = os.path.join(download_path, filename)
			log.info(f"Saving to: {file_path}")

			with open(file_path, 'wb') as f:
				for chunk in response.iter_content(chunk_size=8192):
					if chunk:
						f.write(chunk)

			log.info(f"Download complete: {file_path}")
			return (True, file_path)

		except Exception as e:
			log.error(f"Download error: {e}", exc_info=True)
			return (False, f"ダウンロードエラー: {str(e)}")

	def get_new_arrivals(self, book_type="braille", period="week"):
		"""
		Get new arrivals from Sapie Library

		Args:
			book_type (str): Type of book - "braille" or "daisy"
			period (str): Time period - "week" or "month"

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Getting new arrivals: type={book_type}, period={period}")

			# Extract current session tokens
			self._extract_session_tokens()

			# New arrivals use J02LST01 action with S00213 (type) and S00214 (period)
			action = "J02LST01"

			# Determine type parameter (S00213)
			if book_type == "braille":
				type_param = "1"  # Braille
			else:
				type_param = "2"  # DAISY (録音)

			# Determine period parameter (S00214)
			if period == "month":
				period_param = "2"  # 1 month
			else:
				period_param = "1"  # 1 week

			# Build URL for new arrivals page
			new_arrivals_url = f"{self.LIBRARY_BASE_URL}?S00101={action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00213={type_param}&S00214={period_param}&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Requesting new arrivals: {new_arrivals_url}")

			# Request new arrivals page
			response = self.session.get(new_arrivals_url)
			response.encoding = 'shift_jis'

			# DEBUG: Save response HTML to file
			import os
			debug_file = os.path.join(os.path.expanduser('~'), 'sapie_new_arrivals_debug.html')
			try:
				with open(debug_file, 'w', encoding='shift_jis', errors='ignore') as f:
					f.write(response.text)
				log.info(f"DEBUG: New arrivals HTML saved to {debug_file}")
			except Exception as e:
				log.warning(f"Could not save debug file: {e}")

			# Parse results from all pages
			all_results = []
			current_page = 1
			max_pages = 100

			while current_page <= max_pages:
				soup = BeautifulSoup(response.text, 'html.parser')

				# Check for "no results" message
				if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
					log.info("No new arrivals found")
					break

				# Parse results from current page
				page_results = self._parse_search_results(soup, book_type)
				all_results.extend(page_results)
				log.info(f"Page {current_page}: {len(page_results)} results (total: {len(all_results)})")

				# Check if there's a next page
				next_page_url = self._has_next_page(soup)
				if not next_page_url:
					log.info("No more pages")
					break

				# Get next page
				try:
					current_page += 1
					if next_page_url.startswith('http'):
						full_url = next_page_url
					else:
						full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

					log.info(f"Requesting page {current_page}: {full_url}")
					response = self.session.get(full_url)
					response.encoding = 'shift_jis'

				except Exception as e:
					log.error(f"Error fetching next page: {e}")
					break

			if all_results:
				log.info(f"New arrivals retrieval successful: {len(all_results)} total results")
				return (True, all_results)
			else:
				log.info("No new arrivals found")
				return (True, [])

		except requests.exceptions.RequestException as e:
			log.error(f"Network error getting new arrivals: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"New arrivals error: {e}", exc_info=True)
			return (False, f"新着取得エラー: {str(e)}")

	def get_popular_books(self, ranking_type="braille_download"):
		"""
		Get popular books from Sapie Library

		Args:
			ranking_type (str): Type of ranking -
				"braille_download", "daisy_download", "daisy_play",
				"braille_request", "daisy_request"

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Getting popular books: ranking_type={ranking_type}")

			# Extract current session tokens
			self._extract_session_tokens()

			# Popular books use J03LST01 action
			action = "J03LST01"

			# Mapping ranking types to S00201 parameter values and book types
			ranking_map = {
				"braille_download": ("1", "braille", "点字ダウンロード"),
				"daisy_download": ("3", "daisy", "デイジーダウンロード"),
				"daisy_play": ("4", "daisy", "デイジー再生"),
				"braille_request": ("21", "braille", "点字オンラインリクエスト"),
				"daisy_request": ("22", "daisy", "録音オンラインリクエスト")
			}

			# Get ranking parameters
			if ranking_type in ranking_map:
				s00201_param, book_type, ranking_name = ranking_map[ranking_type]
			else:
				# Default to braille download
				s00201_param, book_type, ranking_name = ("1", "braille", "点字ダウンロード")

			# Calculate date for 1 week ago (default period)
			from datetime import datetime, timedelta
			one_week_ago = datetime.now() - timedelta(days=7)
			date_param = one_week_ago.strftime("%Y%m%d")

			# Build URL for popular books page
			# S00201: ranking type, S00212: category (1=books), S00222: start date
			popular_url = f"{self.LIBRARY_BASE_URL}?S00101={action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00201={s00201_param}&S00212=1&S00222={date_param}&RTNTME={self.session_tokens.get('RTNTME', '')}"

			log.info(f"Requesting {ranking_name} ranking: {popular_url}")

			# Request popular books page
			response = self.session.get(popular_url)
			response.encoding = 'shift_jis'

			# Parse results from all pages
			all_results = []
			current_page = 1
			max_pages = 100

			while current_page <= max_pages:
				soup = BeautifulSoup(response.text, 'html.parser')

				# Check for "no results" message
				if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
					log.info("No popular books found")
					break

				# Parse results from current page
				page_results = self._parse_search_results(soup, book_type)
				all_results.extend(page_results)
				log.info(f"Page {current_page}: {len(page_results)} results (total: {len(all_results)})")

				# Check if there's a next page
				next_page_url = self._has_next_page(soup)
				if not next_page_url:
					log.info("No more pages")
					break

				# Get next page
				try:
					current_page += 1
					if next_page_url.startswith('http'):
						full_url = next_page_url
					else:
						full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

					log.info(f"Requesting page {current_page}: {full_url}")
					response = self.session.get(full_url)
					response.encoding = 'shift_jis'

				except Exception as e:
					log.error(f"Error fetching next page: {e}")
					break

			if all_results:
				log.info(f"{ranking_name} ranking retrieval successful: {len(all_results)} total results")
				return (True, all_results)
			else:
				log.info(f"No results found for {ranking_name} ranking")
				return (True, [])

		except requests.exceptions.RequestException as e:
			log.error(f"Network error getting popular books: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Popular books error: {e}", exc_info=True)
			return (False, f"人気図書取得エラー: {str(e)}")

	def _get_all_popular_rankings(self):
		"""
		Get all 5 popular ranking types

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		try:
			# All ranking types with their names
			ranking_types = [
				("3", "デイジーダウンロード", "daisy"),
				("4", "デイジー再生", "daisy"),
				("22", "録音オンラインリクエスト", "daisy"),
				("1", "点字ダウンロード", "braille"),
				("21", "点字オンラインリクエスト", "braille")
			]

			all_results = []
			action = "J03LST01"

			# Calculate date for 1 week ago
			from datetime import datetime, timedelta
			one_week_ago = datetime.now() - timedelta(days=7)
			date_param = one_week_ago.strftime("%Y%m%d")

			for ranking_type, ranking_name, book_type in ranking_types:
				log.info(f"Getting {ranking_name} ranking...")

				# Build URL
				popular_url = f"{self.LIBRARY_BASE_URL}?S00101={action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00201={ranking_type}&S00212=1&S00222={date_param}&RTNTME={self.session_tokens.get('RTNTME', '')}"

				# Request ranking page
				response = self.session.get(popular_url)
				response.encoding = 'shift_jis'

				# Parse results with pagination
				current_page = 1
				max_pages = 100

				while current_page <= max_pages:
					soup = BeautifulSoup(response.text, 'html.parser')

					# Check for "no results" message
					if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
						break

					# Parse results from current page
					page_results = self._parse_search_results(soup, book_type)

					# Add ranking type info to each result
					for result in page_results:
						result['ranking_type'] = ranking_name

					all_results.extend(page_results)

					# Check if there's a next page
					next_page_url = self._has_next_page(soup)
					if not next_page_url:
						break

					# Get next page
					try:
						current_page += 1
						if next_page_url.startswith('http'):
							full_url = next_page_url
						else:
							full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

						response = self.session.get(full_url)
						response.encoding = 'shift_jis'

					except Exception as e:
						log.error(f"Error fetching next page: {e}")
						break

				log.info(f"{ranking_name}: {len([r for r in all_results if r.get('ranking_type') == ranking_name])} results")

			log.info(f"All rankings retrieval successful: {len(all_results)} total results")
			return (True, all_results)

		except Exception as e:
			log.error(f"Error getting all rankings: {e}", exc_info=True)
			return (False, f"全ランキング取得エラー: {str(e)}")

	def detailed_search(self, search_params):
		"""
		Perform detailed search on Sapie Library

		Args:
			search_params (dict): Detailed search parameters

		Returns:
			tuple: (success: bool, results: list or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			log.info(f"Performing detailed search with {len(search_params)} parameters")

			# Extract current session tokens
			self._extract_session_tokens()

			# Detailed search uses J01SCH04 for form page
			search_action = "J01SCH04"
			book_type = search_params.get("book_type", "all")

			# Navigate to search form page first
			search_page_url = f"{self.LIBRARY_BASE_URL}?S00101={search_action}&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}"

			log.info(f"Navigating to detailed search page: {search_page_url}")
			response = self.session.get(search_page_url)
			response.encoding = 'shift_jis'

			# Extract ALL form fields from search page
			soup = BeautifulSoup(response.text, 'html.parser')
			search_data = {}
			for hidden in soup.find_all('input', type='hidden'):
				name = hidden.get('name')
				value = hidden.get('value', '')
				if name:
					search_data[name] = value

			# Set execution action to J01LST04
			search_data['S00101'] = 'J01LST04'

			# Add detailed search parameters (corrected parameter names)
			if search_params.get("title"):
				search_data['S00251'] = search_params.get("title", '')
				search_data['S00215'] = search_params.get("title_method", '1')  # Corrected from S00253

			if search_params.get("author"):
				search_data['S00252'] = search_params.get("author", '')
				search_data['S00216'] = search_params.get("author_method", '1')  # Corrected from S00254

			if search_params.get("keyword"):
				search_data['S00253'] = search_params.get("keyword", '')  # Corrected from S00255
				search_data['S00234'] = search_params.get("keyword_method", '1')  # Corrected from S00256
				if search_params.get("exclude_abstract"):
					search_data['S00220'] = search_params.get("exclude_abstract", '')  # Corrected from S00267

			if search_params.get("publisher"):
				search_data['S00254'] = search_params.get("publisher", '')  # Corrected from S00257

			if search_params.get("ndc"):
				search_data['S00241'] = search_params.get("ndc", '')  # Corrected from S00258

			if search_params.get("genre"):
				search_data['S00239'] = search_params.get("genre", '')  # Corrected from S00259

			if search_params.get("isbn"):
				search_data['S00243'] = search_params.get("isbn", '')  # Corrected from S00260

			if search_params.get("braille_num"):
				search_data['S00233'] = search_params.get("braille_num", '')  # Corrected from S00261

			if search_params.get("producer_id"):
				search_data['S00231'] = search_params.get("producer_id", '')  # Corrected from S00263

			if search_params.get("holder_id"):
				search_data['S00232'] = search_params.get("holder_id", '')  # Corrected from S00264

			if search_params.get("has_content"):
				search_data['S00213'] = search_params.get("has_content", '')  # Corrected from S00265

			if search_params.get("online_request"):
				search_data['S00214'] = search_params.get("online_request", '')  # Corrected from S00266

			if search_params.get("include_ndl"):
				search_data['S00262'] = search_params.get("include_ndl", '')  # Unchanged

			# Submit detailed search
			import urllib.parse

			# Manually URL encode with shift_jis
			encoded_parts = []
			for key, value in search_data.items():
				if isinstance(key, str):
					key_bytes = key.encode('shift_jis', errors='ignore')
				else:
					key_bytes = str(key).encode('shift_jis', errors='ignore')

				if isinstance(value, str):
					value_bytes = value.encode('shift_jis', errors='ignore')
				else:
					value_bytes = str(value).encode('shift_jis', errors='ignore')

				encoded_key = urllib.parse.quote_from_bytes(key_bytes)
				encoded_value = urllib.parse.quote_from_bytes(value_bytes)
				encoded_parts.append(f'{encoded_key}={encoded_value}')

			encoded_body = '&'.join(encoded_parts)

			response = self.session.post(
				self.LIBRARY_BASE_URL,
				data=encoded_body.encode('ascii'),
				headers={'Content-Type': 'application/x-www-form-urlencoded'}
			)
			response.encoding = 'shift_jis'

			# DEBUG: Save response HTML to file
			import os
			debug_file = os.path.join(os.path.expanduser('~'), 'sapie_detailed_search_debug.html')
			try:
				with open(debug_file, 'w', encoding='shift_jis', errors='ignore') as f:
					f.write(response.text)
				log.info(f"DEBUG: Detailed search HTML saved to {debug_file}")
			except Exception as e:
				log.warning(f"Could not save debug file: {e}")

			# Parse results from all pages
			all_results = []
			current_page = 1
			max_pages = 100

			while current_page <= max_pages:
				soup = BeautifulSoup(response.text, 'html.parser')

				# Check for "no results" message
				if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
					log.info("No results found")
					break

				# Parse results from current page
				page_results = self._parse_search_results(soup, book_type)
				all_results.extend(page_results)
				log.info(f"Page {current_page}: {len(page_results)} results (total: {len(all_results)})")

				# Check if there's a next page
				next_page_url = self._has_next_page(soup)
				if not next_page_url:
					log.info("No more pages")
					break

				# Get next page
				try:
					current_page += 1
					if next_page_url.startswith('http'):
						full_url = next_page_url
					else:
						full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

					log.info(f"Requesting page {current_page}: {full_url}")
					response = self.session.get(full_url)
					response.encoding = 'shift_jis'

				except Exception as e:
					log.error(f"Error fetching next page: {e}")
					break

			if all_results:
				log.info(f"Detailed search successful: {len(all_results)} total results")
				return (True, all_results)
			else:
				log.info("Detailed search returned no results")
				return (True, [])

		except requests.exceptions.RequestException as e:
			log.error(f"Network error during detailed search: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
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

			# Build genre URL to get subgenre list
			# Use J01SC202 to navigate to the subgenre selection page for the given main genre
			genre_url = f"{self.LIBRARY_BASE_URL}?S00101=J01SC202&S00102={self.session_tokens.get('S00102', '')}&S00103={self.session_tokens.get('S00103', '')}&S00239={genre_code}"

			log.info(f"Fetching subgenres from: {genre_url}")

			response = self.session.get(genre_url)
			response.encoding = 'shift_jis'

			if response.status_code != 200:
				log.error(f"Failed to load subgenres page: HTTP {response.status_code}")
				return (False, f"サブジャンルページの読み込みに失敗しました (HTTP {response.status_code})")

			soup = BeautifulSoup(response.text, 'html.parser')

			# Parse subgenres from the page
			# Look for ul.LINK which contains the subgenre links
			subgenres = []
			link_list = soup.find('ul', class_='LINK')

			if link_list:
				links = link_list.find_all('a')

				for link in links:
					href = link.get('href', '')
					name = link.get_text(strip=True)

					# Extract S00239 parameter from href (subgenre code)
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

		except requests.RequestException as e:
			log.error(f"Network error during subgenre fetch: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Get subgenres error: {e}", exc_info=True)
			return (False, f"サブジャンル取得エラー: {str(e)}")

	def genre_search(self, subgenre_code, material_type="", has_content=False, production_status="",
	                 orig_pub_from="", orig_pub_to="", complete_from="", complete_to="", daisy_only=False):
		"""
		Perform genre search on Sapie Library

		Args:
			subgenre_code (str): Subgenre code (e.g., "0602")
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
			log.info(f"Performing genre search: subgenre={subgenre_code}")

			# Extract current session tokens
			self._extract_session_tokens()

			# Determine book type for result parsing
			book_type = "daisy" if daisy_only else "braille"

			# Build search data - use J01LST05 action for genre search results
			search_data = {
				'S00101': 'J01LST05',  # Search results action
				'S00102': self.session_tokens.get('S00102', ''),
				'S00103': self.session_tokens.get('S00103', ''),
				'RTNTME': self.session_tokens.get('RTNTME', ''),
				'S00239': subgenre_code,  # Subgenre code
			}

			# Add optional parameters with correct field names
			if material_type:
				search_data['S00201'] = material_type

			if has_content:
				search_data['S00213'] = "1"

			if daisy_only:
				search_data['S00208'] = "1"

			if production_status:
				search_data['S00219'] = production_status

			if orig_pub_from:
				search_data['S00222'] = orig_pub_from

			if orig_pub_to:
				search_data['S00223'] = orig_pub_to

			if complete_from:
				search_data['S00226'] = complete_from

			if complete_to:
				search_data['S00227'] = complete_to

			# Submit genre search
			import urllib.parse

			# Manually URL encode with shift_jis
			encoded_parts = []
			for key, value in search_data.items():
				if isinstance(key, str):
					key_bytes = key.encode('shift_jis', errors='ignore')
				else:
					key_bytes = str(key).encode('shift_jis', errors='ignore')

				if isinstance(value, str):
					value_bytes = value.encode('shift_jis', errors='ignore')
				else:
					value_bytes = str(value).encode('shift_jis', errors='ignore')

				encoded_key = urllib.parse.quote_from_bytes(key_bytes)
				encoded_value = urllib.parse.quote_from_bytes(value_bytes)
				encoded_parts.append(f'{encoded_key}={encoded_value}')

			encoded_body = '&'.join(encoded_parts)

			response = self.session.post(
				self.LIBRARY_BASE_URL,
				data=encoded_body.encode('ascii'),
				headers={'Content-Type': 'application/x-www-form-urlencoded'}
			)
			response.encoding = 'shift_jis'

			# Parse results from all pages
			all_results = []
			current_page = 1
			max_pages = 100

			while current_page <= max_pages:
				soup = BeautifulSoup(response.text, 'html.parser')

				# Check for "no results" message
				if "該当するデータが見つかりませんでした" in response.text or "検索結果：0件" in response.text:
					log.info("No results found")
					break

				# Parse results from current page
				page_results = self._parse_search_results(soup, book_type)
				all_results.extend(page_results)
				log.info(f"Page {current_page}: {len(page_results)} results (total: {len(all_results)})")

				# Check if there's a next page
				next_page_url = self._has_next_page(soup)
				if not next_page_url:
					log.info("No more pages")
					break

				# Get next page
				try:
					current_page += 1
					if next_page_url.startswith('http'):
						full_url = next_page_url
					else:
						full_url = f"https://library.sapie.or.jp/cgi-bin/{next_page_url}"

					log.info(f"Requesting page {current_page}: {full_url}")
					response = self.session.get(full_url)
					response.encoding = 'shift_jis'

				except Exception as e:
					log.error(f"Error fetching next page: {e}")
					break

			if all_results:
				log.info(f"Genre search successful: {len(all_results)} total results")
				return (True, all_results)
			else:
				log.info("Genre search returned no results")
				return (True, [])

		except requests.exceptions.RequestException as e:
			log.error(f"Network error during genre search: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Genre search error: {e}", exc_info=True)
			return (False, f"ジャンル検索エラー: {str(e)}")

	def get_book_details(self, s00221, s00222):
		"""
		Fetch detailed information for a specific book

		Args:
			s00221 (str): Search ID (optional, can be empty)
			s00222 (str): Book ID (required)

		Returns:
			tuple: (success: bool, details: dict or error_message: str)
		"""
		if not self.logged_in:
			return (False, "ログインしてください。")

		try:
			# Extract current session tokens
			self._extract_session_tokens()

			# Build detail page URL
			# S00221 is optional - if not provided, omit it
			if s00221:
				detail_url = (
					f"{self.LIBRARY_BASE_URL}?"
					f"S00101=J00DTL01&"
					f"S00102={self.session_tokens.get('S00102', '')}&"
					f"S00103={self.session_tokens.get('S00103', '')}&"
					f"S00221={s00221}&"
					f"S00222={s00222}&"
					f"RTNTME={self.session_tokens.get('RTNTME', '')}"
				)
			else:
				# Use S00222 only
				detail_url = (
					f"{self.LIBRARY_BASE_URL}?"
					f"S00101=J00DTL01&"
					f"S00102={self.session_tokens.get('S00102', '')}&"
					f"S00103={self.session_tokens.get('S00103', '')}&"
					f"S00222={s00222}&"
					f"RTNTME={self.session_tokens.get('RTNTME', '')}"
				)

			response = self.session.get(detail_url)
			response.encoding = 'shift_jis'

			# Parse the detail page
			soup = BeautifulSoup(response.content.decode('shift_jis', errors='ignore'), 'html.parser')

			# Extract detailed information
			details = {}

			# Find all table rows in the detail page
			rows = soup.find_all('tr')

			for row in rows:
				th = row.find('th')
				td = row.find('td')

				if th and td:
					label = th.get_text(strip=True)
					value = td.get_text(strip=True)
					details[label] = value

			if details:
				log.info(f"Book details retrieved successfully: {len(details)} fields")
				return (True, details)
			else:
				log.warning("No details found on detail page")
				return (False, "詳細情報が見つかりませんでした。")

		except requests.exceptions.RequestException as e:
			log.error(f"Network error fetching book details: {e}")
			return (False, f"ネットワークエラー: {str(e)}")
		except Exception as e:
			log.error(f"Error fetching book details: {e}", exc_info=True)
			return (False, f"詳細情報取得エラー: {str(e)}")

	def close(self):
		"""Close the session"""
		try:
			if self.logged_in:
				# Logout
				logout_data = {
					'S00101': 'J01LGO01',
					'S00102': self.session_tokens.get('S00102', ''),
					'S00103': self.session_tokens.get('S00103', '')
				}
				self.session.post(self.LIBRARY_BASE_URL, data=logout_data)
				log.info("Logged out successfully")

			self.session.close()
			self.logged_in = False
			log.info("Session closed")
		except Exception as e:
			log.error(f"Error closing session: {e}")

	def __del__(self):
		"""Cleanup when object is destroyed"""
		try:
			self.close()
		except:
			pass
