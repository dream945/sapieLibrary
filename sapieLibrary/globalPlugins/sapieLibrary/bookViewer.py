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


def open_book(file_path, viewer_method=None, convert_to_kana=None, parent=None):
	"""Open a downloaded book for viewing"""
	try:
		if convert_to_kana is None:
			convert_to_kana = True

		from . import sapieConverter

		# List BES files
		bes_files = sapieConverter.list_bes_files(file_path)

		if not bes_files:
			ui.message(_("BESファイルが見つかりませんでした"))
			return False

		if len(bes_files) == 1:
			# Only one file, convert directly
			text_content, book_title = sapieConverter.extract_and_convert_bes(file_path, convert_to_kana)
		else:
			# Multiple files, show selection dialog
			dlg = VolumeSelectionDialog(parent, bes_files)
			if dlg.ShowModal() == wx.ID_OK:
				selected = dlg.GetSelectedFiles()
				if not selected:
					dlg.Destroy()
					return False
				text_content, book_title = sapieConverter.extract_and_convert_selected_bes(
					file_path, selected, convert_to_kana
				)
			else:
				dlg.Destroy()
				return False
			dlg.Destroy()

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


class VolumeSelectionDialog(wx.Dialog):
	"""Dialog to select which volume(s) to open"""

	def __init__(self, parent, volume_list):
		"""
		Initialize the volume selection dialog

		Args:
			parent: Parent window
			volume_list: List of tuples (display_name, file_path)
		"""
		super(VolumeSelectionDialog, self).__init__(
			parent,
			title=_("巻の選択"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
		)
		self.volume_list = volume_list
		self.selected_files = []

		sizer = wx.BoxSizer(wx.VERTICAL)

		# Message
		msg = wx.StaticText(self, label=_("開く巻を選択してください（複数選択可）:"))
		sizer.Add(msg, flag=wx.ALL, border=10)

		# List box with multiple selection
		self.listBox = wx.ListBox(
			self,
			choices=[v[0] for v in volume_list],
			style=wx.LB_EXTENDED | wx.LB_HSCROLL
		)
		self.listBox.SetMinSize((400, 200))
		sizer.Add(self.listBox, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

		# Buttons
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.allBtn = wx.Button(self, label=_("すべて選択(&A)"))
		self.allBtn.Bind(wx.EVT_BUTTON, self.onSelectAll)
		btnSizer.Add(self.allBtn, flag=wx.ALL, border=5)

		self.openBtn = wx.Button(self, wx.ID_OK, label=_("開く(&O)"))
		self.openBtn.Bind(wx.EVT_BUTTON, self.onOpen)
		btnSizer.Add(self.openBtn, flag=wx.ALL, border=5)

		self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label=_("キャンセル(&C)"))
		btnSizer.Add(self.cancelBtn, flag=wx.ALL, border=5)

		sizer.Add(btnSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		self.SetSizer(sizer)
		sizer.Fit(self)
		self.CenterOnParent()

		# Select first item by default
		if self.listBox.GetCount() > 0:
			self.listBox.SetSelection(0)
		self.listBox.SetFocus()

	def onSelectAll(self, evt):
		"""Select all items"""
		for i in range(self.listBox.GetCount()):
			self.listBox.SetSelection(i)

	def onOpen(self, evt):
		"""Get selected files and close"""
		selections = self.listBox.GetSelections()
		self.selected_files = [self.volume_list[i][1] for i in selections]
		self.EndModal(wx.ID_OK)

	def GetSelectedFiles(self):
		"""Return list of selected file paths"""
		return self.selected_files


def open_in_braille_editor(file_path, parent=None):
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
		extracted_files = []  # List of tuples (display_name, file_path)

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

					# Use original name for display
					extracted_files.append((name, bes_path))

		if not extracted_files:
			ui.message(_("BESファイルが見つかりませんでした"))
			return False

		# Sort by name
		extracted_files.sort(key=lambda x: x[0])

		if len(extracted_files) == 1:
			# Only one file, open directly
			subprocess.Popen([editor_path, extracted_files[0][1]], shell=True)
		else:
			# Multiple files, show selection dialog
			dlg = VolumeSelectionDialog(parent, extracted_files)
			if dlg.ShowModal() == wx.ID_OK:
				selected = dlg.GetSelectedFiles()
				for bes_file in selected:
					subprocess.Popen([editor_path, bes_file], shell=True)
				if len(selected) > 1:
					ui.message(_("{}個のファイルを開きました。").format(len(selected)))
			dlg.Destroy()

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
