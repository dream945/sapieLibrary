# -*- coding: utf-8 -*-
# Sapie Converter - Braille file extraction and conversion

import os
import zipfile
import logging

log = logging.getLogger(__name__)

# Supported braille file extensions
BRAILLE_EXTENSIONS = ('.BES', '.BET', '.BMT', '.BSE', '.NAB', '.BRL')


def convert_bes_to_unicode(content):
	"""Convert BES binary content to Unicode braille patterns"""
	result = ""
	i = 0
	for i in range(len(content)):
		if i > 1024:
			break

	tenji = bytearray(content[i:])
	tenji = tenji.replace(b'\x0d\xfe', b'\r\n')

	for i in range(2, len(tenji)):
		if tenji[i] == 0xfd:
			tenji[i-2] = 0x0c
			tenji[i-1] = 0x0c

	for i in range(len(tenji)):
		byte = tenji[i]
		ch = chr(byte + 0x2800 - 0xa0)

		if byte == 0x0d:
			result += "\r"
		elif byte == 0x0a:
			result += "\n"
		elif byte == 0xfd:
			result += "\r\n"
		elif byte == 0xfe:
			result += "\r\n"
		elif byte == 0x0c:
			pass
		elif byte == 0xff:
			pass
		elif '\u2800' <= ch <= '\u283f':
			result += chr(byte + 0x2800 - 0xa0)

	return result


def list_braille_files(file_path):
	"""List BES files in a ZIP/EXE archive

	Returns:
		List of tuples (display_name, internal_filename)
	"""
	bes_files = []
	try:
		with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
			for info in zf.infolist():
				try:
					filename = info.filename.encode('cp437').decode('cp932')
				except:
					filename = info.filename

				name, ext = os.path.splitext(filename)

				if ext.upper() in BRAILLE_EXTENSIONS:
					bes_files.append((name, info.filename))

		# Sort by name
		bes_files.sort(key=lambda x: x[0])
		return bes_files

	except Exception as e:
		log.error(f"Error listing BES files: {e}")
		return []


def extract_and_convert_selected_bes(file_path, selected_files, convert_to_kana=True):
	"""Extract and convert specific BES files from ZIP/EXE

	Args:
		file_path: Path to the ZIP/EXE file
		selected_files: List of internal filenames to extract
		convert_to_kana: Whether to convert to kana

	Returns:
		Tuple of (text_content, book_title)
	"""
	result = ""
	book_title = os.path.splitext(os.path.basename(file_path))[0]

	try:
		with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
			for internal_name in selected_files:
				try:
					with zf.open(internal_name) as f:
						content = f.read()
						braille_text = convert_bes_to_unicode(content)
						result += braille_text
				except Exception as e:
					log.error(f"Error reading {internal_name}: {e}")

				# Get display name for title
				try:
					filename = internal_name.encode('cp437').decode('cp932')
				except:
					filename = internal_name
				name, ext = os.path.splitext(filename)
				if not book_title or book_title == os.path.splitext(os.path.basename(file_path))[0]:
					book_title = name

		if convert_to_kana and result:
			try:
				from .TenjiTexter import DocumentsViewer
				dv = DocumentsViewer()
				dv.buff = result
				result = dv.katakana_conv()
				result = dv.Cxx(result)
				result = dv.Cxx2(result)
				result = dv.Cxx3(result)
			except Exception as e:
				log.error(f"Kana conversion failed: {e}")

		return result, book_title

	except Exception as e:
		log.error(f"Error extracting BES: {e}")
		raise


def extract_and_convert_bes(file_path, convert_to_kana=True):
	"""Extract BES files from ZIP/EXE and convert to readable text"""
	result = ""
	book_title = os.path.splitext(os.path.basename(file_path))[0]

	try:
		with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
			for info in zf.infolist():
				try:
					filename = info.filename.encode('cp437').decode('cp932')
				except:
					filename = info.filename

				name, ext = os.path.splitext(filename)

				if ext.upper() in BRAILLE_EXTENSIONS:
					with zf.open(info.filename) as f:
						content = f.read()
						braille_text = convert_bes_to_unicode(content)
						result += braille_text

					if not book_title or book_title == os.path.splitext(os.path.basename(file_path))[0]:
						book_title = name

		if convert_to_kana and result:
			try:
				from .TenjiTexter import DocumentsViewer
				dv = DocumentsViewer()
				dv.buff = result
				result = dv.katakana_conv()
				result = dv.Cxx(result)
				result = dv.Cxx2(result)
				result = dv.Cxx3(result)
			except Exception as e:
				log.error(f"Kana conversion failed: {e}")

		return result, book_title

	except Exception as e:
		log.error(f"Error extracting BES: {e}")
		raise
