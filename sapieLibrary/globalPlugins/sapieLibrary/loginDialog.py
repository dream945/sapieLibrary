# -*- coding: utf-8 -*-
# Login Dialog for Sapie Library

import wx
import gui

class LoginDialog(wx.Dialog):
	"""Dialog for entering Sapie Library credentials"""

	def __init__(self, parent, config):
		"""
		Initialize login dialog

		Args:
			parent: Parent window
			config: Configuration object for storing credentials
		"""
		super(LoginDialog, self).__init__(
			parent,
			title="サピエ図書館ログイン",
			style=wx.DEFAULT_DIALOG_STYLE
		)

		self.config = config
		self.username = ""
		self.password = ""
		self.remember = False

		# Create GUI
		self._create_ui()

		# Load saved credentials if available
		self._load_saved_credentials()

		# Set focus to first field
		self.usernameText.SetFocus()

	def _create_ui(self):
		"""Create the user interface"""
		mainSizer = wx.BoxSizer(wx.VERTICAL)

		# Create helper for consistent spacing
		helper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

		# Username field
		self.usernameText = helper.addLabeledControl(
			"サピエID:",
			wx.TextCtrl
		)

		# Password field
		self.passwordText = helper.addLabeledControl(
			"パスワード:",
			wx.TextCtrl,
			style=wx.TE_PASSWORD
		)

		# Remember credentials checkbox
		self.rememberCheckbox = helper.addItem(
			wx.CheckBox(self, label="認証情報を保存する")
		)

		# Add buttons
		buttonSizer = helper.addDialogDismissButtons(
			gui.guiHelper.ButtonHelper(wx.HORIZONTAL)
		)

		# Login button
		self.loginButton = buttonSizer.addButton(
			self,
			id=wx.ID_OK,
			label="ログイン(&L)"
		)
		self.loginButton.SetDefault()
		self.loginButton.Bind(wx.EVT_BUTTON, self.onLogin)

		# Cancel button
		cancelButton = buttonSizer.addButton(
			self,
			id=wx.ID_CANCEL,
			label="キャンセル(&C)"
		)
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)

		# Finalize
		mainSizer.Add(helper.sizer, border=10, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CenterOnScreen()

	def _load_saved_credentials(self):
		"""Load saved credentials from config if available"""
		try:
			if self.config["saveCredentials"]:
				username = self.config["username"]
				password = self.config["password"]

				if username:
					self.usernameText.SetValue(username)
				if password:
					# Decode password (basic encoding, not encryption)
					try:
						import base64
						decoded_password = base64.b64decode(password.encode()).decode()
						self.passwordText.SetValue(decoded_password)
					except:
						pass

				self.rememberCheckbox.SetValue(True)
		except:
			pass

	def onLogin(self, event):
		"""Handle login button click"""
		# Get values
		self.username = self.usernameText.GetValue().strip()
		self.password = self.passwordText.GetValue()
		self.remember = self.rememberCheckbox.GetValue()

		# Validate input
		if not self.username:
			gui.messageBox(
				"サピエIDを入力してください。",
				"入力エラー",
				wx.OK | wx.ICON_ERROR
			)
			self.usernameText.SetFocus()
			return

		if not self.password:
			gui.messageBox(
				"パスワードを入力してください。",
				"入力エラー",
				wx.OK | wx.ICON_ERROR
			)
			self.passwordText.SetFocus()
			return

		# Save credentials if requested
		if self.remember:
			try:
				self.config["saveCredentials"] = True
				self.config["username"] = self.username

				# Encode password (basic encoding, not encryption)
				import base64
				encoded_password = base64.b64encode(self.password.encode()).decode()
				self.config["password"] = encoded_password
			except Exception as e:
				# If save fails, continue anyway
				pass
		else:
			# Clear saved credentials
			try:
				self.config["saveCredentials"] = False
				self.config["username"] = ""
				self.config["password"] = ""
			except:
				pass

		# Close dialog with OK result
		self.EndModal(wx.ID_OK)

	def onCancel(self, event):
		"""Handle cancel button click"""
		self.EndModal(wx.ID_CANCEL)

	def get_credentials(self):
		"""
		Get entered credentials

		Returns:
			tuple: (username: str, password: str)
		"""
		return (self.username, self.password)
