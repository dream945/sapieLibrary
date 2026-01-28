# -*- coding: utf-8 -*-
# Sapie Converter - BES file extraction and conversion

import os
import zipfile
import logging

log = logging.getLogger(__name__)


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

				if ext.upper() == '.BES':
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
