# -*- coding: utf-8 -*-
# DAISY Converter - Extract and convert DAISY books

import os
import zipfile
import tempfile
import logging
import re
import webbrowser

log = logging.getLogger(__name__)


def is_daisy_file(file_path):
	"""Check if a file is a DAISY book"""
	try:
		with zipfile.ZipFile(file_path, mode='r') as zf:
			names = [n.lower() for n in zf.namelist()]
			# DAISY 2.02: ncc.html
			if any('ncc.html' in n or 'ncc.htm' in n for n in names):
				return True
			# DAISY 3: .opf file
			if any(n.endswith('.opf') for n in names):
				return True
			# Check for SMIL files (common in DAISY)
			if any(n.endswith('.smil') for n in names):
				return True
		return False
	except:
		return False


def get_daisy_type(file_path):
	"""Determine DAISY type (2.02 or 3)"""
	try:
		with zipfile.ZipFile(file_path, mode='r') as zf:
			names = [n.lower() for n in zf.namelist()]
			if any('ncc.html' in n or 'ncc.htm' in n for n in names):
				return "2.02"
			if any(n.endswith('.opf') for n in names):
				return "3"
		return None
	except:
		return None


def extract_daisy_content(file_path):
	"""Extract content from DAISY book and return as structured data

	Returns:
		dict with keys: title, sections (list of {level, title, content})
	"""
	result = {
		'title': os.path.splitext(os.path.basename(file_path))[0],
		'sections': []
	}

	try:
		with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
			daisy_type = get_daisy_type(file_path)

			if daisy_type == "2.02":
				result = _extract_daisy_202(zf, result)
			elif daisy_type == "3":
				result = _extract_daisy_3(zf, result)
			else:
				# Try to extract any HTML/text content
				result = _extract_generic_content(zf, result)

	except Exception as e:
		log.error(f"Error extracting DAISY content: {e}")

	return result


def _decode_filename(filename):
	"""Decode filename from ZIP"""
	try:
		return filename.encode('cp437').decode('cp932')
	except:
		try:
			return filename.encode('cp437').decode('utf-8')
		except:
			return filename


def _extract_daisy_202(zf, result):
	"""Extract content from DAISY 2.02 format"""
	# Find ncc.html for navigation
	ncc_content = None
	ncc_name = None

	for info in zf.infolist():
		name_lower = info.filename.lower()
		if 'ncc.html' in name_lower or 'ncc.htm' in name_lower:
			ncc_name = info.filename
			ncc_content = zf.read(info.filename)
			break

	if ncc_content:
		# Parse NCC to get structure and content files
		ncc_text = _try_decode(ncc_content)
		result['title'] = _extract_title(ncc_text) or result['title']

		# Extract headings and content references
		heading_pattern = re.compile(r'<h(\d)[^>]*>.*?<a[^>]*href=["\']([^"\'#]+)[^"\']*["\'][^>]*>([^<]*)</a>.*?</h\1>', re.IGNORECASE | re.DOTALL)

		for match in heading_pattern.finditer(ncc_text):
			level = int(match.group(1))
			href = match.group(2)
			title = _clean_html(match.group(3))

			# Try to read the referenced content file
			content = ""
			try:
				# Resolve relative path
				if ncc_name:
					base_dir = os.path.dirname(ncc_name)
					content_path = os.path.join(base_dir, href).replace('\\', '/')
				else:
					content_path = href

				# Find the file in archive
				for info in zf.infolist():
					if info.filename.lower() == content_path.lower() or info.filename.lower().endswith('/' + href.lower()):
						content_bytes = zf.read(info.filename)
						content = _extract_text_from_html(_try_decode(content_bytes))
						break
			except Exception as e:
				log.debug(f"Could not read content file {href}: {e}")

			result['sections'].append({
				'level': level,
				'title': title,
				'content': content
			})

	# If no sections found, try to extract from HTML files directly
	if not result['sections']:
		result = _extract_generic_content(zf, result)

	return result


def _extract_daisy_3(zf, result):
	"""Extract content from DAISY 3 (ANSI/NISO Z39.86) format"""
	# Collect all XML files
	xml_files = []
	for info in zf.infolist():
		name_lower = info.filename.lower()
		if name_lower.endswith('.xml'):
			xml_files.append(info)

	# Sort XML files by filename (ptk00001.xml, ptk00002.xml, ...)
	xml_files.sort(key=lambda x: x.filename.lower())

	# Process ALL XML files
	for info in xml_files:
		try:
			xml_content = zf.read(info.filename)
			xml_text = _try_decode(xml_content)

			# Check if it's DTBook format
			if 'dtbook' in xml_text.lower() or '<level' in xml_text.lower() or '<book' in xml_text.lower():
				result = _parse_dtbook(xml_text, result)
		except Exception as e:
			log.debug(f"Error processing {info.filename}: {e}")
			continue

	# If no sections found, try generic extraction
	if not result['sections']:
		result = _extract_generic_content(zf, result)

	return result


def _parse_dtbook(xml_text, result):
	"""Parse DTBook XML format - extracts content from a single XML file"""
	# Extract title from dc:Title meta or doctitle
	if not result.get('title') or result['title'] == os.path.splitext(os.path.basename(result.get('_filepath', '')))[0]:
		title_match = re.search(r'<meta[^>]*name=["\']dc:Title["\'][^>]*content=["\']([^"\']+)["\']', xml_text, re.IGNORECASE)
		if title_match:
			result['title'] = _clean_html(title_match.group(1))
		else:
			title_match = re.search(r'<doctitle[^>]*>([^<]*)</doctitle>', xml_text, re.IGNORECASE)
			if title_match:
				result['title'] = _clean_html(title_match.group(1))

	# Extract headings and content from level elements
	# DTBook uses level1, level2, level3, etc.
	level_pattern = re.compile(r'<level(\d)[^>]*>(.*?)</level\1>', re.IGNORECASE | re.DOTALL)

	for level_match in level_pattern.finditer(xml_text):
		level = int(level_match.group(1))
		section_content = level_match.group(2)

		# Find heading in this section (h1, h2, etc. or text in <sent> tags)
		heading_pattern = re.compile(r'<h(\d)[^>]*>(.*?)</h\1>', re.IGNORECASE | re.DOTALL)
		heading_match = heading_pattern.search(section_content)

		if heading_match:
			# Extract text from heading, handling nested tags like <sent>, <span>, etc.
			heading_html = heading_match.group(2)
			title = _extract_text_from_html(heading_html).strip()
			# Get first line only for title
			title = title.split('\n')[0].strip()
		else:
			title = f"セクション"

		# Extract text content from paragraphs
		content = _extract_text_from_html(section_content)

		if title or content.strip():
			result['sections'].append({
				'level': level,
				'title': title if title else "（無題）",
				'content': content
			})

	return result


def _extract_generic_content(zf, result):
	"""Extract content from HTML/HTM files when structure is unknown"""
	html_files = []

	for info in zf.infolist():
		name_lower = info.filename.lower()
		if name_lower.endswith('.html') or name_lower.endswith('.htm'):
			# Skip ncc.html
			if 'ncc.' not in name_lower:
				html_files.append(info)

	# Sort by filename
	html_files.sort(key=lambda x: x.filename.lower())

	for info in html_files:
		try:
			content_bytes = zf.read(info.filename)
			html_text = _try_decode(content_bytes)

			# Extract title from this file
			title = _extract_title(html_text)
			if not title:
				title = os.path.splitext(_decode_filename(info.filename))[0]

			# Extract text content
			content = _extract_text_from_html(html_text)

			if content.strip():
				result['sections'].append({
					'level': 1,
					'title': title,
					'content': content
				})
		except Exception as e:
			log.debug(f"Error reading {info.filename}: {e}")

	return result


def _try_decode(content_bytes):
	"""Try to decode bytes to string with various encodings"""
	encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp', 'iso-2022-jp', 'latin-1']
	for encoding in encodings:
		try:
			return content_bytes.decode(encoding)
		except:
			continue
	return content_bytes.decode('utf-8', errors='replace')


def _extract_title(html_text):
	"""Extract title from HTML"""
	match = re.search(r'<title[^>]*>([^<]*)</title>', html_text, re.IGNORECASE)
	if match:
		return _clean_html(match.group(1))
	return None


def _extract_text_from_html(html_text):
	"""Extract plain text from HTML, preserving some structure"""
	# Remove script and style
	text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.IGNORECASE | re.DOTALL)
	text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)

	# Convert br and p to newlines
	text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
	text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
	text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)

	# Remove all other tags
	text = re.sub(r'<[^>]+>', '', text)

	# Decode HTML entities
	text = re.sub(r'&nbsp;', ' ', text)
	text = re.sub(r'&lt;', '<', text)
	text = re.sub(r'&gt;', '>', text)
	text = re.sub(r'&amp;', '&', text)
	text = re.sub(r'&quot;', '"', text)
	text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)

	# Clean up whitespace
	text = re.sub(r'\n\s*\n', '\n\n', text)
	text = text.strip()

	return text


def _clean_html(text):
	"""Remove HTML tags and clean whitespace"""
	text = re.sub(r'<[^>]+>', '', text)
	text = re.sub(r'\s+', ' ', text)
	return text.strip()


def generate_html(daisy_content):
	"""Generate navigable HTML from DAISY content"""
	title = daisy_content.get('title', 'DAISY図書')
	sections = daisy_content.get('sections', [])

	html_parts = [
		'<!DOCTYPE html>',
		'<html lang="ja">',
		'<head>',
		'<meta charset="UTF-8">',
		f'<title>{title}</title>',
		'<style>',
		'body { font-family: "メイリオ", "Meiryo", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }',
		'h1 { border-bottom: 2px solid #333; padding-bottom: 10px; }',
		'h2 { border-left: 4px solid #666; padding-left: 10px; margin-top: 2em; }',
		'h3 { margin-top: 1.5em; }',
		'nav { background: #f5f5f5; padding: 15px; margin-bottom: 20px; }',
		'nav h2 { margin-top: 0; }',
		'nav ul { list-style: none; padding-left: 0; }',
		'nav li { margin: 5px 0; }',
		'nav a { text-decoration: none; color: #0066cc; }',
		'nav a:hover { text-decoration: underline; }',
		'.section { margin-bottom: 2em; }',
		'.content { white-space: pre-wrap; }',
		'</style>',
		'</head>',
		'<body>',
		f'<h1>{title}</h1>',
	]

	# Generate table of contents
	if sections:
		html_parts.append('<nav>')
		html_parts.append('<h2>目次</h2>')
		html_parts.append('<ul>')
		for i, section in enumerate(sections):
			level = section.get('level', 1)
			section_title = section.get('title', f'セクション {i+1}')
			indent = '　' * (level - 1)
			html_parts.append(f'<li>{indent}<a href="#section{i}">{section_title}</a></li>')
		html_parts.append('</ul>')
		html_parts.append('</nav>')

	# Generate content sections
	for i, section in enumerate(sections):
		level = min(section.get('level', 1), 6)
		section_title = section.get('title', f'セクション {i+1}')
		content = section.get('content', '')

		html_parts.append(f'<div class="section" id="section{i}">')
		html_parts.append(f'<h{level}>{section_title}</h{level}>')
		if content:
			# Escape HTML in content
			content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
			html_parts.append(f'<div class="content">{content}</div>')
		html_parts.append('</div>')

	html_parts.extend([
		'</body>',
		'</html>'
	])

	return '\n'.join(html_parts)


def open_daisy_in_browser(file_path):
	"""Extract DAISY content and open in browser"""
	try:
		# Extract content
		content = extract_daisy_content(file_path)

		if not content['sections']:
			return False, "DAISYコンテンツを抽出できませんでした"

		# Generate HTML
		html = generate_html(content)

		# Save to temp file
		temp_dir = tempfile.gettempdir()
		safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in content['title'])[:50]
		html_path = os.path.join(temp_dir, f"{safe_title}_daisy.html")

		with open(html_path, 'w', encoding='utf-8') as f:
			f.write(html)

		# Open in default browser
		webbrowser.open(f'file:///{html_path.replace(os.sep, "/")}')

		return True, content['title']

	except Exception as e:
		log.error(f"Error opening DAISY: {e}", exc_info=True)
		return False, str(e)
