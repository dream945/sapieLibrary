# -*- coding: utf-8 -*-
# Book Viewer - View downloaded Sapie books

import os
import subprocess
import tempfile
import logging
import zipfile
import wx
import config
import ui
import addonHandler

try:
	addonHandler.initTranslation()
except:
	def _(s):
		return s

log = logging.getLogger(__name__)


def open_book(file_path, viewer_method=None, convert_to_kana=None):
	"""Open a downloaded book for viewing"""
	try:
		if convert_to_kana is None:
			convert_to_kana = True

		from . import sapieConverter
		text_content, book_title = sapieConverter.extract_and_convert_bes(file_path, convert_to_kana)

		if not text_content:
			ui.message(_("読み取れるコンテンツがありません"))
			return False

		# Open in Notepad
		_open_in_external_editor(text_content, book_title, is_braille=not convert_to_kana)

		return True
	except Exception as e:
		log.error(f"Error opening book: {e}", exc_info=True)
		ui.message(_("図書を開けませんでした: {}").format(str(e)))
		return False


def _open_in_external_editor(text_content, book_title, is_braille=False):
	"""Save text to temp file and open in notepad"""
	# Use notepad for converted text (kana/unicode braille)
	editor_path = "notepad.exe"

	# Save to temp file
	temp_dir = tempfile.gettempdir()
	safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in book_title)[:50]
	suffix = "_braille" if is_braille else "_kana"
	file_path = os.path.join(temp_dir, f"{safe_title}{suffix}.txt")

	with open(file_path, 'w', encoding='utf-8') as f:
		f.write(text_content)

	subprocess.Popen([editor_path, file_path], shell=True)


def open_in_braille_editor(file_path):
	"""Extract BES file from ZIP and open in external editor"""
	try:
		# Get external editor path from config
		try:
			editor_path = config.conf["sapieLibrary"].get("brailleEditor", "notepad.exe")
			if not editor_path:
				editor_path = "notepad.exe"
		except:
			editor_path = "notepad.exe"

		# Extract BES file from ZIP
		temp_dir = tempfile.gettempdir()
		extracted_files = []

		with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
			for info in zf.infolist():
				try:
					filename = info.filename.encode('cp437').decode('cp932')
				except:
					filename = info.filename

				name, ext = os.path.splitext(filename)

				if ext.upper() == '.BES':
					# Extract BES file to temp directory
					bes_content = zf.read(info.filename)
					safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)[:50]
					bes_path = os.path.join(temp_dir, f"{safe_name}.bes")

					with open(bes_path, 'wb') as f:
						f.write(bes_content)

					extracted_files.append(bes_path)

		if not extracted_files:
			ui.message(_("BESファイルが見つかりませんでした"))
			return False

		# Open all BES files in external editor
		for bes_file in extracted_files:
			subprocess.Popen([editor_path, bes_file], shell=True)

		if len(extracted_files) > 1:
			ui.message(_("{}個のBESファイルを開きました。").format(len(extracted_files)))

		return True

	except Exception as e:
		log.error(f"Error opening in external editor: {e}", exc_info=True)
		ui.message(_("外部エディタで開けませんでした: {}").format(str(e)))
		return False


def open_book_async(file_path, viewer_method=None, convert_to_kana=None, callback=None):
	"""Open a book asynchronously"""
	import threading

	def _open():
		try:
			success = open_book(file_path, viewer_method, convert_to_kana)
			if callback:
				wx.CallAfter(callback, success, None)
		except Exception as e:
			if callback:
				wx.CallAfter(callback, False, str(e))

	thread = threading.Thread(target=_open, daemon=True)
	thread.start()


def browse_and_open_book(parent=None):
	"""Show file dialog to browse and open an existing book"""
	try:
		# Get default directory from config
		try:
			default_dir = config.conf["sapieLibrary"].get("downloadPath", "")
		except:
			default_dir = ""

		dlg = wx.FileDialog(
			parent,
			_("点字図書を開く"),
			defaultDir=default_dir,
			wildcard=_("点字図書 (*.zip;*.exe)|*.zip;*.exe|すべてのファイル (*.*)|*.*"),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		)

		if dlg.ShowModal() == wx.ID_OK:
			file_path = dlg.GetPath()
			dlg.Destroy()

			# Show view options dialog
			from .sapieDialog import ViewOptionsDialog
			view_dlg = ViewOptionsDialog(parent, file_path, is_new_download=False)
			view_dlg.ShowModal()
			view_dlg.Destroy()
			return True
		else:
			dlg.Destroy()
			return False

	except Exception as e:
		log.error(f"Error browsing for book: {e}", exc_info=True)
		ui.message(_("ファイルを開けませんでした: {}").format(str(e)))
		return False
