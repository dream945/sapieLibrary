# -*- coding: utf-8 -*-
# Sapie Library Addon for NVDA
# This addon allows users to search and download braille and DAISY books from Sapie Library

import sys
import os
import globalPluginHandler
import gui
from gui import settingsDialogs
import wx
import config
import addonHandler

# Add lib directory to Python path for bundled dependencies
addon_path = os.path.dirname(__file__)
lib_path = os.path.join(addon_path, "lib")
if lib_path not in sys.path:
	sys.path.insert(0, lib_path)

# Initialize addon localization
addonHandler.initTranslation()

# Configuration specification
confspec = {
	"sapieLibrary": {
		"downloadPath": "string(default='')",
		"saveCredentials": "boolean(default=False)",
		"username": "string(default='')",
		"password": "string(default='')",
		"preferredFormat": "string(default='both')",
		"autoLogin": "boolean(default=False)",
		"displayFormat": "string(default='kana')",
		"brailleEditor": "string(default='notepad.exe')"
	}
}

class SapieLibrarySettingsPanel(settingsDialogs.SettingsPanel):
	"""Settings panel for Sapie Library addon"""
	# Translators: This is the label for the Sapie Library settings panel
	title = _("サピエ図書館")

	def makeSettings(self, settingsSizer):
		"""Create settings controls"""
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Download path
		# Translators: Label for download path in settings
		self.downloadPathLabel = _("ダウンロード先フォルダ(&D):")
		self.downloadPathText = sHelper.addLabeledControl(
			self.downloadPathLabel,
			wx.TextCtrl,
			value=config.conf["sapieLibrary"]["downloadPath"]
		)

		# Browse button for download path
		# Translators: Button to browse for download folder
		self.browseButton = wx.Button(self, label=_("参照(&B)..."))
		self.browseButton.Bind(wx.EVT_BUTTON, self.onBrowse)
		sHelper.sizer.Add(self.browseButton, flag=wx.ALL, border=5)

		# Save credentials checkbox
		# Translators: Checkbox to save login credentials
		self.saveCredentialsCheckbox = sHelper.addItem(
			wx.CheckBox(self, label=_("ログイン情報を保存する(&S)"))
		)
		self.saveCredentialsCheckbox.SetValue(config.conf["sapieLibrary"]["saveCredentials"])

		# Username (only if save credentials is checked)
		# Translators: Label for username in settings
		self.usernameLabel = _("サピエID(&U):")
		self.usernameText = sHelper.addLabeledControl(
			self.usernameLabel,
			wx.TextCtrl,
			value=config.conf["sapieLibrary"]["username"]
		)

		# Password (only if save credentials is checked)
		# Translators: Label for password in settings
		self.passwordLabel = _("パスワード(&P):")
		self.passwordText = sHelper.addLabeledControl(
			self.passwordLabel,
			wx.TextCtrl,
			style=wx.TE_PASSWORD,
			value=config.conf["sapieLibrary"]["password"]
		)

		# Auto login checkbox
		# Translators: Checkbox to automatically login on startup
		self.autoLoginCheckbox = sHelper.addItem(
			wx.CheckBox(self, label=_("起動時に自動ログインする(&A)"))
		)
		self.autoLoginCheckbox.SetValue(config.conf["sapieLibrary"]["autoLogin"])

		# Display format choice
		# Translators: Label for display format selection
		displayFormatLabel = _("点字データの表示形式(&F):")
		self.displayFormatChoice = sHelper.addLabeledControl(
			displayFormatLabel,
			wx.Choice,
			choices=[_("カナで表示"), _("Unicode点字で表示"), _("外部エディタで開く")]
		)
		currentFormat = config.conf["sapieLibrary"].get("displayFormat", "kana")
		if currentFormat == "kana":
			self.displayFormatChoice.SetSelection(0)
		elif currentFormat == "braille":
			self.displayFormatChoice.SetSelection(1)
		else:  # editor
			self.displayFormatChoice.SetSelection(2)

		# External editor path
		# Translators: Label for external editor path
		externalEditorLabel = _("外部エディタ(&E):")
		self.brailleEditorText = sHelper.addLabeledControl(
			externalEditorLabel,
			wx.TextCtrl,
			value=config.conf["sapieLibrary"].get("brailleEditor", "notepad.exe")
		)

		# Browse button for external editor
		# Translators: Button to browse for external editor
		self.browseEditorButton = wx.Button(self, label=_("参照(&R)..."))
		self.browseEditorButton.Bind(wx.EVT_BUTTON, self.onBrowseEditor)
		sHelper.sizer.Add(self.browseEditorButton, flag=wx.ALL, border=5)

		# Update control states based on save credentials checkbox
		self.saveCredentialsCheckbox.Bind(wx.EVT_CHECKBOX, self.onSaveCredentialsChanged)
		self.onSaveCredentialsChanged(None)

	def onBrowse(self, evt):
		"""Handle browse button click"""
		dlg = wx.DirDialog(
			self,
			_("ダウンロード先フォルダを選択"),
			defaultPath=self.downloadPathText.GetValue(),
			style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
		)

		if dlg.ShowModal() == wx.ID_OK:
			self.downloadPathText.SetValue(dlg.GetPath())

		dlg.Destroy()

	def onSaveCredentialsChanged(self, evt):
		"""Handle save credentials checkbox change"""
		saveCredentials = self.saveCredentialsCheckbox.GetValue()
		self.usernameText.Enable(saveCredentials)
		self.passwordText.Enable(saveCredentials)
		self.autoLoginCheckbox.Enable(saveCredentials)

	def onBrowseEditor(self, evt):
		"""Handle browse button click for external editor"""
		dlg = wx.FileDialog(
			self,
			_("外部エディタを選択"),
			defaultDir=os.path.dirname(self.brailleEditorText.GetValue()) or "",
			defaultFile=os.path.basename(self.brailleEditorText.GetValue()) or "",
			wildcard=_("実行ファイル (*.exe)|*.exe|すべてのファイル (*.*)|*.*"),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		)

		if dlg.ShowModal() == wx.ID_OK:
			self.brailleEditorText.SetValue(dlg.GetPath())

		dlg.Destroy()

	def onSave(self):
		"""Save settings"""
		config.conf["sapieLibrary"]["downloadPath"] = self.downloadPathText.GetValue()
		config.conf["sapieLibrary"]["saveCredentials"] = self.saveCredentialsCheckbox.GetValue()

		if self.saveCredentialsCheckbox.GetValue():
			config.conf["sapieLibrary"]["username"] = self.usernameText.GetValue()
			config.conf["sapieLibrary"]["password"] = self.passwordText.GetValue()
			config.conf["sapieLibrary"]["autoLogin"] = self.autoLoginCheckbox.GetValue()
		else:
			# Clear credentials if not saving
			config.conf["sapieLibrary"]["username"] = ""
			config.conf["sapieLibrary"]["password"] = ""
			config.conf["sapieLibrary"]["autoLogin"] = False

		# Save display format
		formatSelection = self.displayFormatChoice.GetSelection()
		if formatSelection == 0:
			config.conf["sapieLibrary"]["displayFormat"] = "kana"
		elif formatSelection == 1:
			config.conf["sapieLibrary"]["displayFormat"] = "braille"
		else:
			config.conf["sapieLibrary"]["displayFormat"] = "editor"

		# Save braille editor path
		config.conf["sapieLibrary"]["brailleEditor"] = self.brailleEditorText.GetValue()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Main global plugin for Sapie Library addon"""

	def __init__(self):
		"""Initialize the plugin"""
		super(GlobalPlugin, self).__init__()
		# Initialize configuration
		self.loadConfig()
		# Dialog instance
		self.sapieDialog = None
		# Add menu item to Tools menu
		self.toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self.sapieMenuItem = self.toolsMenu.Append(wx.ID_ANY, _("サピエ図書館(&S)..."), _("サピエ図書館の検索ダイアログを開きます"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSapieMenu, self.sapieMenuItem)
		# Register settings panel
		settingsDialogs.NVDASettingsDialog.categoryClasses.append(SapieLibrarySettingsPanel)

	def loadConfig(self):
		"""Load addon configuration"""
		try:
			# Add our confspec to NVDA's config
			config.conf.spec["sapieLibrary"] = confspec["sapieLibrary"]
			# Get reference to our config section
			self.config = config.conf["sapieLibrary"]
		except Exception as e:
			# If config fails, use defaults
			import ui
			ui.message(_("サピエ図書館アドオンの設定読み込みに失敗しました"))

	def onSapieMenu(self, evt):
		"""Handle menu item click"""
		self._showDialog()

	def _showDialog(self):
		"""Show Sapie Library search dialog"""
		# Import here to avoid circular imports
		try:
			from . import sapieDialog

			# Check if dialog already exists and is shown
			if self.sapieDialog and self.sapieDialog.IsShown():
				# Bring existing dialog to front
				self.sapieDialog.Raise()
			else:
				# Create new dialog
				self.sapieDialog = sapieDialog.SapieDialog(gui.mainFrame)
				self.sapieDialog.Show()
		except ImportError:
			# sapieDialog module not yet implemented
			import ui
			ui.message(_("サピエ図書館ダイアログを開いています..."))
			# For now, show a simple message
			gui.messageBox(
				_("サピエ図書館アドオンは現在開発中です。\n\n機能:\n- サピエ図書館への接続\n- 点字・DAISY図書の検索\n- 選択した図書のダウンロード\n\nNVDA+Sで起動します。"),
				_("サピエ図書館"),
				wx.OK | wx.ICON_INFORMATION
			)
		except Exception as e:
			import ui
			ui.message(_("エラー: {}").format(str(e)))


	def terminate(self):
		"""Clean up when addon is terminated"""
		try:
			# Unregister settings panel
			settingsDialogs.NVDASettingsDialog.categoryClasses.remove(SapieLibrarySettingsPanel)
		except (ValueError, AttributeError):
			pass

		try:
			# Remove menu item
			if hasattr(self, 'toolsMenu') and hasattr(self, 'sapieMenuItem'):
				self.toolsMenu.Remove(self.sapieMenuItem)
			# Close dialog if open
			if self.sapieDialog:
				self.sapieDialog.Close()
				self.sapieDialog = None
		except:
			pass
		super(GlobalPlugin, self).terminate()
