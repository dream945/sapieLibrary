# -*- coding: utf-8 -*-
# Sapie Library - Main Search Dialog

import wx
import ui
import gui
import config
import logging
import addonHandler
import threading
from . import loginDialog
from . import sapieClient
from . import downloadThread

# Initialize translations
addonHandler.initTranslation()

log = logging.getLogger(__name__)

class BookDetailDialog(wx.Dialog):
	"""Dialog to display detailed book information"""

	def __init__(self, parent, title, details):
		"""
		Initialize the book detail dialog

		Args:
			parent: Parent window
			title (str): Book title
			details (dict): Dictionary of detail fields
		"""
		super(BookDetailDialog, self).__init__(
			parent,
			title=_("詳細情報: {}").format(title),
			size=(600, 500)
		)

		# Create main sizer
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Create scrolled text control to display details
		self.detailText = wx.TextCtrl(
			self,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
		)

		# Format details as readable text
		detail_lines = []
		for label, value in details.items():
			if value:  # Only show non-empty values
				detail_lines.append(f"{label}:\n  {value}\n")

		self.detailText.SetValue('\n'.join(detail_lines))

		sizer.Add(self.detailText, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

		# Add Close button
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		closeButton = wx.Button(self, wx.ID_CLOSE, _("閉じる(&C)"))
		closeButton.Bind(wx.EVT_BUTTON, self.onClose)
		buttonSizer.Add(closeButton, flag=wx.ALL, border=5)

		sizer.Add(buttonSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		self.SetSizer(sizer)
		self.detailText.SetFocus()

	def onClose(self, evt):
		"""Handle close button click"""
		self.Close()

class SapieDialog(wx.Dialog):
	"""Main dialog for searching and downloading Sapie Library books"""

	def __init__(self, parent):
		"""
		Initialize the Sapie dialog

		Args:
			parent: Parent window
		"""
		super().__init__(
			parent,
			title=_("サピエ図書館"),
			size=(800, 600),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
		)

		self.client = None
		self.searchResults = []
		self.isLoggedIn = False

		self._createControls()
		self._bindEvents()
		self.CenterOnScreen()

		# Show login panel initially, hide search panel
		self._showLoginPanel()

	def _createControls(self):
		"""Create dialog controls"""
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)

		# Login panel (initially visible)
		self.loginPanel = self._createLoginPanel()
		self.mainSizer.Add(self.loginPanel, flag=wx.EXPAND | wx.ALL, border=5)

		# Search panel (initially hidden)
		self.searchPanel = self._createSearchPanelFull()
		self.mainSizer.Add(self.searchPanel, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		# Progress bar (initially hidden)
		self.progressBar = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL)
		self.mainSizer.Add(self.progressBar, flag=wx.EXPAND | wx.ALL, border=5)
		self.progressBar.Hide()

		# Status text (always visible)
		self.statusText = wx.StaticText(self, label=_("ログインしてください"))
		self.mainSizer.Add(self.statusText, flag=wx.ALL, border=5)

		# Bottom buttons (always visible)
		bottomButtonSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Open book button
		self.openBookButton = wx.Button(self, label=_("図書を開く(&O)..."))
		self.openBookButton.Bind(wx.EVT_BUTTON, self.onOpenBook)
		bottomButtonSizer.Add(self.openBookButton, flag=wx.ALL, border=5)

		# Close button
		closeButton = wx.Button(self, wx.ID_CLOSE, _("閉じる(&C)"))
		bottomButtonSizer.Add(closeButton, flag=wx.ALL, border=5)

		self.mainSizer.Add(bottomButtonSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		self.SetSizer(self.mainSizer)

	def _createLoginPanel(self):
		"""Create login panel"""
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Title
		titleLabel = wx.StaticText(panel, label=_("サピエ図書館にログイン"))
		titleFont = titleLabel.GetFont()
		titleFont.PointSize += 2
		titleFont = titleFont.Bold()
		titleLabel.SetFont(titleFont)
		sizer.Add(titleLabel, flag=wx.ALL, border=10)

		# Load saved credentials
		conf = config.conf["sapieLibrary"]
		savedUsername = conf.get("username", "")
		savedPassword = conf.get("password", "")
		saveCredentials = conf.get("saveCredentials", False)

		# Username field
		usernameLabel = wx.StaticText(panel, label=_("サピエID(&U):"))
		sizer.Add(usernameLabel, flag=wx.ALL, border=5)

		self.usernameText = wx.TextCtrl(panel, value=savedUsername)
		sizer.Add(self.usernameText, flag=wx.EXPAND | wx.ALL, border=5)

		# Password field
		passwordLabel = wx.StaticText(panel, label=_("パスワード(&P):"))
		sizer.Add(passwordLabel, flag=wx.ALL, border=5)

		self.passwordText = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, value=savedPassword)
		sizer.Add(self.passwordText, flag=wx.EXPAND | wx.ALL, border=5)

		# Remember credentials checkbox
		self.rememberCheckbox = wx.CheckBox(panel, label=_("認証情報を保存(&R)"))
		self.rememberCheckbox.SetValue(saveCredentials)
		sizer.Add(self.rememberCheckbox, flag=wx.ALL, border=5)

		# Login button
		self.loginButtonMain = wx.Button(panel, label=_("ログイン(&L)"))
		self.loginButtonMain.SetDefault()
		sizer.Add(self.loginButtonMain, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		panel.SetSizer(sizer)
		return panel

	def _createSearchPanelFull(self):
		"""Create complete search panel with input, results, and buttons"""
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Create choicebook (dropdown selection) for different search modes
		# Using Choicebook instead of Notebook for better NVDA accessibility
		self.searchNotebook = wx.Choicebook(panel)

		# Tab 1: Regular search (点字・DAISY検索)
		self.regularSearchTab = self._createRegularSearchTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.regularSearchTab, _("点字・DAISY検索"))

		# Tab 2: Online request search (オンラインリクエスト検索)
		self.onlineRequestTab = self._createOnlineRequestSearchTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.onlineRequestTab, _("オンラインリクエスト検索"))

		# Tab 3: New arrivals (新着完成情報)
		self.newArrivalsTab = self._createNewArrivalsTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.newArrivalsTab, _("新着完成情報"))

		# Tab 4: Popular books (人気のある本)
		self.popularBooksTab = self._createPopularBooksTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.popularBooksTab, _("人気のある本"))

		# Tab 5: Detailed search (詳細検索)
		self.detailedSearchTab = self._createDetailedSearchTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.detailedSearchTab, _("詳細検索"))

		# Tab 6: Genre search (ジャンル検索)
		self.genreSearchTab = self._createGenreSearchTab(self.searchNotebook)
		self.searchNotebook.AddPage(self.genreSearchTab, _("ジャンル検索"))

		sizer.Add(self.searchNotebook, flag=wx.EXPAND | wx.ALL, border=5)

		# Results list (shared between tabs)
		resultsLabel = wx.StaticText(panel, label=_("検索結果:"))
		sizer.Add(resultsLabel, flag=wx.ALL, border=5)

		self.resultsList = wx.ListCtrl(
			panel,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL
		)
		self.resultsList.InsertColumn(0, _("タイトル"), width=300)
		self.resultsList.InsertColumn(1, _("著者"), width=150)
		self.resultsList.InsertColumn(2, _("種類"), width=100)
		self.resultsList.InsertColumn(3, _("製作館"), width=100)

		sizer.Add(self.resultsList, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		# Buttons
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.detailButton = wx.Button(panel, label=_("詳細情報(&I)"))
		self.detailButton.Enable(False)
		buttonSizer.Add(self.detailButton, flag=wx.ALL, border=5)

		self.downloadButton = wx.Button(panel, label=_("ダウンロード(&D)"))
		self.downloadButton.Enable(False)
		buttonSizer.Add(self.downloadButton, flag=wx.ALL, border=5)

		self.logoutButton = wx.Button(panel, label=_("ログアウト(&O)"))
		buttonSizer.Add(self.logoutButton, flag=wx.ALL, border=5)

		sizer.Add(buttonSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		panel.SetSizer(sizer)
		return panel

	def _createRegularSearchTab(self, parent):
		"""Create regular search tab (original search functionality)"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# First row: Title and Type selection
		firstRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Title field
		titleLabel = wx.StaticText(panel, label=_("タイトル(&T):"))
		firstRowSizer.Add(titleLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.searchText = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
		firstRowSizer.Add(self.searchText, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		# Book type choice
		typeLabel = wx.StaticText(panel, label=_("種類(&Y):"))
		firstRowSizer.Add(typeLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.typeChoice = wx.Choice(panel, choices=[_("点字"), _("DAISY")])
		self.typeChoice.SetSelection(0)  # Default to Braille
		firstRowSizer.Add(self.typeChoice, flag=wx.ALL, border=5)

		sizer.Add(firstRowSizer, flag=wx.EXPAND)

		# Second row: Author
		secondRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		authorLabel = wx.StaticText(panel, label=_("著者(&A):"))
		secondRowSizer.Add(authorLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.authorText = wx.TextCtrl(panel)
		secondRowSizer.Add(self.authorText, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		sizer.Add(secondRowSizer, flag=wx.EXPAND)

		# Third row: Data type (DAISY only) and Category
		thirdRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Data type (for DAISY) - S00201
		self.dataTypeLabel = wx.StaticText(panel, label=_("資料種別(&D):"))
		thirdRowSizer.Add(self.dataTypeLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.dataTypeChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("音声デイジー"),
			_("テキストデイジー"),
			_("マルチメディアデイジー")
		])
		self.dataTypeChoice.SetSelection(0)
		thirdRowSizer.Add(self.dataTypeChoice, flag=wx.ALL, border=5)

		# Category - S00218
		categoryLabel = wx.StaticText(panel, label=_("種別(&C):"))
		thirdRowSizer.Add(categoryLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.categoryChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("図書"),
			_("逐次刊行物"),
			_("その他")
		])
		self.categoryChoice.SetSelection(0)
		thirdRowSizer.Add(self.categoryChoice, flag=wx.ALL, border=5)

		sizer.Add(thirdRowSizer, flag=wx.EXPAND)

		# Fourth row: Include NDL checkbox and Search button
		fourthRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Include National Diet Library checkbox - S00262
		self.includeNDLCheckbox = wx.CheckBox(panel, label=_("国会図書館を含める(&N)"))
		self.includeNDLCheckbox.SetValue(True)  # Checked by default
		fourthRowSizer.Add(self.includeNDLCheckbox, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		fourthRowSizer.AddStretchSpacer()

		# Search button
		self.searchButton = wx.Button(panel, label=_("検索開始(&S)"))
		fourthRowSizer.Add(self.searchButton, flag=wx.ALL, border=5)

		sizer.Add(fourthRowSizer, flag=wx.EXPAND)

		# Bind type choice change event to update visibility
		self.typeChoice.Bind(wx.EVT_CHOICE, self._onTypeChanged)

		panel.SetSizer(sizer)
		return panel

	def _createOnlineRequestSearchTab(self, parent):
		"""Create online request search tab"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# First row: Title
		firstRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		titleLabel = wx.StaticText(panel, label=_("タイトル(&T):"))
		firstRowSizer.Add(titleLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.onlineRequestTitleText = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
		firstRowSizer.Add(self.onlineRequestTitleText, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		sizer.Add(firstRowSizer, flag=wx.EXPAND)

		# Second row: Author
		secondRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		authorLabel = wx.StaticText(panel, label=_("著者(&A):"))
		secondRowSizer.Add(authorLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.onlineRequestAuthorText = wx.TextCtrl(panel)
		secondRowSizer.Add(self.onlineRequestAuthorText, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

		sizer.Add(secondRowSizer, flag=wx.EXPAND)

		# Third row: Material type and Category
		thirdRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Material type - S00201
		materialTypeLabel = wx.StaticText(panel, label=_("資料種別(&M):"))
		thirdRowSizer.Add(materialTypeLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.onlineRequestMaterialTypeChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("点字"),
			_("音声デイジー"),
			_("テキストデイジー"),
			_("マルチメディアデイジー")
		])
		self.onlineRequestMaterialTypeChoice.SetSelection(0)
		thirdRowSizer.Add(self.onlineRequestMaterialTypeChoice, flag=wx.ALL, border=5)

		# Category - S00218
		categoryLabel = wx.StaticText(panel, label=_("種別(&C):"))
		thirdRowSizer.Add(categoryLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.onlineRequestCategoryChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("図書"),
			_("逐次刊行物"),
			_("その他")
		])
		self.onlineRequestCategoryChoice.SetSelection(0)
		thirdRowSizer.Add(self.onlineRequestCategoryChoice, flag=wx.ALL, border=5)

		sizer.Add(thirdRowSizer, flag=wx.EXPAND)

		# Fourth row: Search button
		fourthRowSizer = wx.BoxSizer(wx.HORIZONTAL)
		fourthRowSizer.AddStretchSpacer()

		# Search button
		self.onlineRequestSearchButton = wx.Button(panel, label=_("検索開始(&S)"))
		fourthRowSizer.Add(self.onlineRequestSearchButton, flag=wx.ALL, border=5)

		sizer.Add(fourthRowSizer, flag=wx.EXPAND)

		panel.SetSizer(sizer)
		return panel

	def _createNewArrivalsTab(self, parent):
		"""Create new arrivals tab"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# First row: Type selection
		typeRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		typeLabel = wx.StaticText(panel, label=_("種類(&Y):"))
		typeRowSizer.Add(typeLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.newArrivalsTypeChoice = wx.Choice(panel, choices=[_("点字"), _("DAISY")])
		self.newArrivalsTypeChoice.SetSelection(0)  # Default to Braille
		typeRowSizer.Add(self.newArrivalsTypeChoice, flag=wx.ALL, border=5)

		sizer.Add(typeRowSizer, flag=wx.EXPAND)

		# Second row: Period selection
		periodRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		periodLabel = wx.StaticText(panel, label=_("期間(&P):"))
		periodRowSizer.Add(periodLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.newArrivalsPeriodChoice = wx.Choice(panel, choices=[_("1週間"), _("1ヶ月")])
		self.newArrivalsPeriodChoice.SetSelection(0)  # Default to 1 week
		periodRowSizer.Add(self.newArrivalsPeriodChoice, flag=wx.ALL, border=5)

		periodRowSizer.AddStretchSpacer()

		# Load button
		self.newArrivalsLoadButton = wx.Button(panel, label=_("新着情報を取得(&L)"))
		periodRowSizer.Add(self.newArrivalsLoadButton, flag=wx.ALL, border=5)

		sizer.Add(periodRowSizer, flag=wx.EXPAND)

		panel.SetSizer(sizer)
		return panel

	def _createPopularBooksTab(self, parent):
		"""Create popular books tab"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Type selection row
		typeRowSizer = wx.BoxSizer(wx.HORIZONTAL)

		typeLabel = wx.StaticText(panel, label=_("ランキング種類(&Y):"))
		typeRowSizer.Add(typeLabel, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

		self.popularBooksTypeChoice = wx.Choice(panel, choices=[
			_("点字ダウンロードランキング"),
			_("デイジーダウンロードランキング"),
			_("デイジー再生ランキング"),
			_("点字オンラインリクエストランキング"),
			_("録音オンラインリクエストランキング")
		])
		self.popularBooksTypeChoice.SetSelection(0)  # Default to braille download
		typeRowSizer.Add(self.popularBooksTypeChoice, flag=wx.ALL, border=5)

		typeRowSizer.AddStretchSpacer()

		# Load button
		self.popularBooksLoadButton = wx.Button(panel, label=_("人気のある本を取得(&L)"))
		typeRowSizer.Add(self.popularBooksLoadButton, flag=wx.ALL, border=5)

		sizer.Add(typeRowSizer, flag=wx.EXPAND)

		panel.SetSizer(sizer)
		return panel

	def _createDetailedSearchTab(self, parent):
		"""Create detailed search tab with all search parameters"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# === Section 1: Search terms ===
		sizer.Add(wx.StaticText(panel, label=_("【検索語の入力】")), flag=wx.ALL, border=5)

		# Title with search method
		titleSizer = wx.BoxSizer(wx.HORIZONTAL)
		titleSizer.Add(wx.StaticText(panel, label=_("タイトル:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedTitleText = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER, size=(300, -1))
		titleSizer.Add(self.detailedTitleText, flag=wx.ALL, border=5)
		self.detailedTitleMethodChoice = wx.Choice(panel, choices=[_("すべての語を含む"), _("いずれかの語を含む")])
		self.detailedTitleMethodChoice.SetSelection(0)
		titleSizer.Add(self.detailedTitleMethodChoice, flag=wx.ALL, border=5)
		sizer.Add(titleSizer)

		# Author with search method
		authorSizer = wx.BoxSizer(wx.HORIZONTAL)
		authorSizer.Add(wx.StaticText(panel, label=_("著者:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedAuthorText = wx.TextCtrl(panel, size=(300, -1))
		authorSizer.Add(self.detailedAuthorText, flag=wx.ALL, border=5)
		self.detailedAuthorMethodChoice = wx.Choice(panel, choices=[_("すべての語を含む"), _("いずれかの語を含む")])
		self.detailedAuthorMethodChoice.SetSelection(0)
		authorSizer.Add(self.detailedAuthorMethodChoice, flag=wx.ALL, border=5)
		sizer.Add(authorSizer)

		# Keyword with search method
		keywordSizer = wx.BoxSizer(wx.HORIZONTAL)
		keywordSizer.Add(wx.StaticText(panel, label=_("キーワード:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedKeywordText = wx.TextCtrl(panel, size=(300, -1))
		keywordSizer.Add(self.detailedKeywordText, flag=wx.ALL, border=5)
		self.detailedKeywordMethodChoice = wx.Choice(panel, choices=[_("すべての語を含む"), _("いずれかの語を含む")])
		self.detailedKeywordMethodChoice.SetSelection(0)
		keywordSizer.Add(self.detailedKeywordMethodChoice, flag=wx.ALL, border=5)
		sizer.Add(keywordSizer)

		self.detailedExcludeAbstractCheckbox = wx.CheckBox(panel, label=_("抄録からの検索を除外"))
		sizer.Add(self.detailedExcludeAbstractCheckbox, flag=wx.ALL, border=5)

		# Publisher
		publisherSizer = wx.BoxSizer(wx.HORIZONTAL)
		publisherSizer.Add(wx.StaticText(panel, label=_("出版者:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedPublisherText = wx.TextCtrl(panel, size=(300, -1))
		publisherSizer.Add(self.detailedPublisherText, flag=wx.ALL, border=5)
		sizer.Add(publisherSizer)

		# NDC, Genre, ISBN
		miscSizer = wx.BoxSizer(wx.HORIZONTAL)
		miscSizer.Add(wx.StaticText(panel, label=_("NDC:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedNDCText = wx.TextCtrl(panel, size=(100, -1))
		miscSizer.Add(self.detailedNDCText, flag=wx.ALL, border=5)
		miscSizer.Add(wx.StaticText(panel, label=_("ジャンル:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedGenreText = wx.TextCtrl(panel, size=(80, -1))
		miscSizer.Add(self.detailedGenreText, flag=wx.ALL, border=5)
		miscSizer.Add(wx.StaticText(panel, label=_("ISBN:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedISBNText = wx.TextCtrl(panel, size=(150, -1))
		miscSizer.Add(self.detailedISBNText, flag=wx.ALL, border=5)
		sizer.Add(miscSizer)

		# Braille data number, Producer ID, Holder ID
		idSizer = wx.BoxSizer(wx.HORIZONTAL)
		idSizer.Add(wx.StaticText(panel, label=_("点字データ番号:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedBrailleNumText = wx.TextCtrl(panel, size=(80, -1))
		idSizer.Add(self.detailedBrailleNumText, flag=wx.ALL, border=5)
		idSizer.Add(wx.StaticText(panel, label=_("製作館ID:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedProducerIDText = wx.TextCtrl(panel, size=(60, -1))
		idSizer.Add(self.detailedProducerIDText, flag=wx.ALL, border=5)
		idSizer.Add(wx.StaticText(panel, label=_("所蔵館ID:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedHolderIDText = wx.TextCtrl(panel, size=(60, -1))
		idSizer.Add(self.detailedHolderIDText, flag=wx.ALL, border=5)
		sizer.Add(idSizer)

		# Checkboxes
		self.detailedHasContentCheckbox = wx.CheckBox(panel, label=_("コンテンツの存在する資料のみ検索"))
		sizer.Add(self.detailedHasContentCheckbox, flag=wx.ALL, border=5)
		self.detailedOnlineRequestCheckbox = wx.CheckBox(panel, label=_("オンラインリクエスト可能な資料のみ検索"))
		sizer.Add(self.detailedOnlineRequestCheckbox, flag=wx.ALL, border=5)
		self.detailedIncludeNDLCheckbox = wx.CheckBox(panel, label=_("国会図書館を含める"))
		self.detailedIncludeNDLCheckbox.SetValue(True)
		sizer.Add(self.detailedIncludeNDLCheckbox, flag=wx.ALL, border=5)

		# === Section 2: Search criteria ===
		sizer.Add(wx.StaticText(panel, label=_("【検索対象の指定】")), flag=wx.ALL, border=5)

		# Material type
		matTypeSizer = wx.BoxSizer(wx.HORIZONTAL)
		matTypeSizer.Add(wx.StaticText(panel, label=_("資料種別:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedMaterialTypeChoice = wx.Choice(panel, choices=[
			_("すべて"), _("【点字】すべて"), _("点字データのみ"), _("点字のみ"),
			_("【録音】すべて"), _("カセットテープのみ"), _("音声デイジーのみ"), _("オーディオブック等"),
			_("音声解説"), _("【墨字】すべて"), _("テキストデータのみ"), _("拡大文字のみ"),
			_("テキストデイジーのみ"), _("マルチメディアデイジー"), _("映像資料"), _("【その他】")
		])
		self.detailedMaterialTypeChoice.SetSelection(0)
		matTypeSizer.Add(self.detailedMaterialTypeChoice, flag=wx.ALL, border=5)
		self.detailedDaisyOnlyCheckbox = wx.CheckBox(panel, label=_("デイジーのみ対象"))
		matTypeSizer.Add(self.detailedDaisyOnlyCheckbox, flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		sizer.Add(matTypeSizer)

		# Braille detail
		brailleDetailSizer = wx.BoxSizer(wx.HORIZONTAL)
		brailleDetailSizer.Add(wx.StaticText(panel, label=_("点字資料種別詳細:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedBrailleNoAbbrevCheckbox = wx.CheckBox(panel, label=_("英語略字なし"))
		brailleDetailSizer.Add(self.detailedBrailleNoAbbrevCheckbox, flag=wx.ALL, border=5)
		self.detailedBrailleAbbrevCheckbox = wx.CheckBox(panel, label=_("英語略字あり"))
		brailleDetailSizer.Add(self.detailedBrailleAbbrevCheckbox, flag=wx.ALL, border=5)
		self.detailedKanBrailleCheckbox = wx.CheckBox(panel, label=_("漢点字"))
		brailleDetailSizer.Add(self.detailedKanBrailleCheckbox, flag=wx.ALL, border=5)
		self.detailedRokutenCheckbox = wx.CheckBox(panel, label=_("六点漢字"))
		brailleDetailSizer.Add(self.detailedRokutenCheckbox, flag=wx.ALL, border=5)
		sizer.Add(brailleDetailSizer)

		# Catalog type, Category, Target
		row1Sizer = wx.BoxSizer(wx.HORIZONTAL)
		row1Sizer.Add(wx.StaticText(panel, label=_("目録種別:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedCatalogTypeChoice = wx.Choice(panel, choices=[_("サピエ目録"), _("出版")])
		self.detailedCatalogTypeChoice.SetSelection(0)
		row1Sizer.Add(self.detailedCatalogTypeChoice, flag=wx.ALL, border=5)
		row1Sizer.Add(wx.StaticText(panel, label=_("種別:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedCategoryChoice = wx.Choice(panel, choices=[_("すべて"), _("図書"), _("逐次刊行物"), _("その他")])
		self.detailedCategoryChoice.SetSelection(0)
		row1Sizer.Add(self.detailedCategoryChoice, flag=wx.ALL, border=5)
		row1Sizer.Add(wx.StaticText(panel, label=_("対象:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedTargetChoice = wx.Choice(panel, choices=[_("すべて"), _("一般"), _("児童")])
		self.detailedTargetChoice.SetSelection(0)
		row1Sizer.Add(self.detailedTargetChoice, flag=wx.ALL, border=5)
		sizer.Add(row1Sizer)

		# Loan format
		loanSizer = wx.BoxSizer(wx.HORIZONTAL)
		loanSizer.Add(wx.StaticText(panel, label=_("貸出形態:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedLoanFormatChoice = wx.Choice(panel, choices=[
			_("すべて"), _("点字（普通）"), _("点字（L）"), _("FD"), _("カセット"), _("CD"),
			_("MD"), _("拡大文字"), _("点訳絵本"), _("触る絵本"), _("墨字"), _("DVD"), _("その他")
		])
		self.detailedLoanFormatChoice.SetSelection(0)
		loanSizer.Add(self.detailedLoanFormatChoice, flag=wx.ALL, border=5)
		sizer.Add(loanSizer)

		# Production status, Graphic, Audio compression
		row2Sizer = wx.BoxSizer(wx.HORIZONTAL)
		row2Sizer.Add(wx.StaticText(panel, label=_("製作状況:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedProductionStatusChoice = wx.Choice(panel, choices=[_("すべて"), _("完成"), _("製作途中"), _("着手")])
		self.detailedProductionStatusChoice.SetSelection(0)
		row2Sizer.Add(self.detailedProductionStatusChoice, flag=wx.ALL, border=5)
		row2Sizer.Add(wx.StaticText(panel, label=_("グラフィック:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedGraphicChoice = wx.Choice(panel, choices=[_("すべて"), _("DOS"), _("Win"), _("エーデル"), _("その他")])
		self.detailedGraphicChoice.SetSelection(0)
		row2Sizer.Add(self.detailedGraphicChoice, flag=wx.ALL, border=5)
		row2Sizer.Add(wx.StaticText(panel, label=_("音声圧縮:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedAudioCompChoice = wx.Choice(panel, choices=[_("すべて"), _("MP2"), _("MP3"), _("ADPCM"), _("PCM")])
		self.detailedAudioCompChoice.SetSelection(0)
		row2Sizer.Add(self.detailedAudioCompChoice, flag=wx.ALL, border=5)
		sizer.Add(row2Sizer)

		# === Section 3: Date ranges ===
		sizer.Add(wx.StaticText(panel, label=_("【期間の範囲指定】")), flag=wx.ALL, border=5)

		# Original publication date
		origPubSizer = wx.BoxSizer(wx.HORIZONTAL)
		origPubSizer.Add(wx.StaticText(panel, label=_("原本出版年月(6桁):")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedOrigPubFromText = wx.TextCtrl(panel, size=(70, -1))
		origPubSizer.Add(self.detailedOrigPubFromText, flag=wx.ALL, border=5)
		origPubSizer.Add(wx.StaticText(panel, label=_("～")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedOrigPubToText = wx.TextCtrl(panel, size=(70, -1))
		origPubSizer.Add(self.detailedOrigPubToText, flag=wx.ALL, border=5)
		sizer.Add(origPubSizer)

		# Braille/Audio publication year
		braillePubSizer = wx.BoxSizer(wx.HORIZONTAL)
		braillePubSizer.Add(wx.StaticText(panel, label=_("点録出版年(4桁):")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedBraillePubFromText = wx.TextCtrl(panel, size=(60, -1))
		braillePubSizer.Add(self.detailedBraillePubFromText, flag=wx.ALL, border=5)
		braillePubSizer.Add(wx.StaticText(panel, label=_("～")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedBraillePubToText = wx.TextCtrl(panel, size=(60, -1))
		braillePubSizer.Add(self.detailedBraillePubToText, flag=wx.ALL, border=5)
		sizer.Add(braillePubSizer)

		# Completion date
		completeSizer = wx.BoxSizer(wx.HORIZONTAL)
		completeSizer.Add(wx.StaticText(panel, label=_("完成予定日(8桁):")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedCompleteFromText = wx.TextCtrl(panel, size=(90, -1))
		completeSizer.Add(self.detailedCompleteFromText, flag=wx.ALL, border=5)
		completeSizer.Add(wx.StaticText(panel, label=_("～")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedCompleteToText = wx.TextCtrl(panel, size=(90, -1))
		completeSizer.Add(self.detailedCompleteToText, flag=wx.ALL, border=5)
		sizer.Add(completeSizer)

		# === Section 4: Display count ===
		displaySizer = wx.BoxSizer(wx.HORIZONTAL)
		displaySizer.Add(wx.StaticText(panel, label=_("表示件数:")), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self.detailedDisplayCountChoice = wx.Choice(panel, choices=["50", "100", "200", "300"])
		self.detailedDisplayCountChoice.SetSelection(0)
		displaySizer.Add(self.detailedDisplayCountChoice, flag=wx.ALL, border=5)
		sizer.Add(displaySizer)

		# Search button
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		btnSizer.AddStretchSpacer()
		self.detailedSearchButton = wx.Button(panel, label=_("検索開始(&S)"))
		btnSizer.Add(self.detailedSearchButton, flag=wx.ALL, border=5)
		sizer.Add(btnSizer, flag=wx.EXPAND|wx.ALL, border=5)

		panel.SetSizer(sizer)
		return panel

	def _createGenreSearchTab(self, parent):
		"""Create genre search tab with hierarchical genre selection"""
		panel = wx.Panel(parent)
		sizer = wx.BoxSizer(wx.VERTICAL)

		# Main genre selection
		mainGenreLabel = wx.StaticText(panel, label=_("メインジャンル:"))
		sizer.Add(mainGenreLabel, flag=wx.ALL, border=5)

		self.genreMainChoice = wx.Choice(panel, choices=[
			_("文学"),  # 01
			_("哲学・心理・宗教"),  # 02
			_("歴史・伝記"),  # 03
			_("地理・紀行"),  # 04
			_("政治・法律・経済・統計"),  # 05
			_("福祉"),  # 06
			_("社会・教育・風俗習慣・国防"),  # 07
			_("医学"),  # 08
			_("自然科学"),  # 09
			_("技術・コンピュータ"),  # 10
			_("家庭・手芸・料理・育児"),  # 11
			_("農林水産業・商業・運輸・通信"),  # 12
			_("美術・音楽・演劇・スポーツ・娯楽"),  # 13
			_("言語"),  # 14
			_("総記"),  # 15
			_("絵本・紙芝居の製作"),  # 16
			_("マンガの製作")  # 17
		])
		self.genreMainChoice.SetSelection(0)
		sizer.Add(self.genreMainChoice, flag=wx.ALL | wx.EXPAND, border=5)

		# Load subgenres button
		self.genreLoadSubgenresButton = wx.Button(panel, label=_("サブジャンル取得(&L)"))
		sizer.Add(self.genreLoadSubgenresButton, flag=wx.ALL, border=5)

		# Subgenre selection
		subGenreLabel = wx.StaticText(panel, label=_("サブジャンル:"))
		sizer.Add(subGenreLabel, flag=wx.ALL, border=5)

		self.genreSubChoice = wx.Choice(panel, choices=[_("サブジャンルを取得してください")])
		self.genreSubChoice.SetSelection(0)
		self.genreSubChoice.Enable(False)
		sizer.Add(self.genreSubChoice, flag=wx.ALL | wx.EXPAND, border=5)

		# Store subgenre codes mapping
		self.genreSubgenreCodes = []

		# Material type selection
		materialLabel = wx.StaticText(panel, label=_("資料種別:"))
		sizer.Add(materialLabel, flag=wx.ALL, border=5)

		self.genreMaterialTypeChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("【点字】すべて"),
			_("点字データのみ"),
			_("点字のみ"),
			_("【録音】すべて"),
			_("カセットテープのみ"),
			_("音声デイジーのみ"),
			_("オーディオブック等"),
			_("音声解説"),
			_("【墨字】すべて"),
			_("テキストデータのみ"),
			_("拡大文字のみ"),
			_("テキストデイジーのみ"),
			_("マルチメディアデイジー"),
			_("映像資料"),
			_("【その他】")
		])
		self.genreMaterialTypeChoice.SetSelection(0)
		sizer.Add(self.genreMaterialTypeChoice, flag=wx.ALL | wx.EXPAND, border=5)

		# Filters - using StaticText label instead of StaticBoxSizer for accessibility
		sizer.Add(wx.StaticText(panel, label=_("【絞り込み条件】")), flag=wx.ALL, border=5)

		# Has content checkbox
		self.genreHasContentCheckbox = wx.CheckBox(panel, label=_("コンテンツ登録のある資料のみ"))
		sizer.Add(self.genreHasContentCheckbox, flag=wx.ALL, border=5)

		# DAISY only checkbox
		self.genreDaisyOnlyCheckbox = wx.CheckBox(panel, label=_("デイジーのみ"))
		sizer.Add(self.genreDaisyOnlyCheckbox, flag=wx.ALL, border=5)

		# Production status
		prodStatusLabel = wx.StaticText(panel, label=_("製作状況:"))
		sizer.Add(prodStatusLabel, flag=wx.ALL, border=5)

		self.genreProductionStatusChoice = wx.Choice(panel, choices=[
			_("すべて"),
			_("完成"),
			_("製作途中"),
			_("着手")
		])
		self.genreProductionStatusChoice.SetSelection(0)
		sizer.Add(self.genreProductionStatusChoice, flag=wx.ALL | wx.EXPAND, border=5)

		# Original publication date range
		origPubLabel = wx.StaticText(panel, label=_("原本出版年月（YYYYMM）:"))
		sizer.Add(origPubLabel, flag=wx.ALL, border=5)

		origPubSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.genreOrigPubFromText = wx.TextCtrl(panel, size=(80, -1))
		origPubSizer.Add(self.genreOrigPubFromText, flag=wx.ALL, border=5)
		origPubSizer.Add(wx.StaticText(panel, label=_("〜")), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
		self.genreOrigPubToText = wx.TextCtrl(panel, size=(80, -1))
		origPubSizer.Add(self.genreOrigPubToText, flag=wx.ALL, border=5)
		sizer.Add(origPubSizer, flag=wx.EXPAND)

		# Completion date range
		completeLabel = wx.StaticText(panel, label=_("完成（予定）日（YYYYMMDD）:"))
		sizer.Add(completeLabel, flag=wx.ALL, border=5)

		completeSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.genreCompleteFromText = wx.TextCtrl(panel, size=(80, -1))
		completeSizer.Add(self.genreCompleteFromText, flag=wx.ALL, border=5)
		completeSizer.Add(wx.StaticText(panel, label=_("〜")), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
		self.genreCompleteToText = wx.TextCtrl(panel, size=(80, -1))
		completeSizer.Add(self.genreCompleteToText, flag=wx.ALL, border=5)
		sizer.Add(completeSizer, flag=wx.EXPAND)

		# Search button
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		btnSizer.AddStretchSpacer()
		self.genreSearchButton = wx.Button(panel, label=_("検索開始(&S)"))
		btnSizer.Add(self.genreSearchButton, flag=wx.ALL, border=5)
		sizer.Add(btnSizer, flag=wx.EXPAND | wx.ALL, border=5)

		panel.SetSizer(sizer)
		return panel

	def _showLoginPanel(self):
		"""Show login panel and hide search panel"""
		self.loginPanel.Show()
		self.searchPanel.Hide()
		self.Layout()
		# Always set focus to username field
		self.usernameText.SetFocus()

	def _showSearchPanel(self):
		"""Hide login panel and show search panel"""
		self.loginPanel.Hide()
		self.searchPanel.Show()
		self._updateSearchFields()  # Update field visibility based on type
		self.Layout()
		self.searchText.SetFocus()

	def _onTypeChanged(self, evt):
		"""Handle search type change"""
		self._updateSearchFields()

	def _updateSearchFields(self):
		"""Update search field visibility based on selected type"""
		typeIndex = self.typeChoice.GetSelection()
		isDaisy = (typeIndex == 1)  # 0=Braille, 1=DAISY

		# Show/hide data type field (DAISY only)
		self.dataTypeLabel.Show(isDaisy)
		self.dataTypeChoice.Show(isDaisy)

		self.Layout()

	def _showProgress(self):
		"""Show progress bar in pulse mode"""
		self.progressBar.Show()
		self.progressBar.Pulse()
		self.Layout()

	def _hideProgress(self):
		"""Hide progress bar"""
		self.progressBar.Hide()
		self.Layout()

	def _updateProgress(self):
		"""Update progress bar (pulse animation)"""
		if self.progressBar.IsShown():
			self.progressBar.Pulse()

	def _bindEvents(self):
		"""Bind event handlers"""
		# Login panel events
		self.Bind(wx.EVT_BUTTON, self.onLoginMain, self.loginButtonMain)
		self.passwordText.Bind(wx.EVT_TEXT_ENTER, self.onLoginMain)

		# Regular search panel events
		self.Bind(wx.EVT_BUTTON, self.onSearch, self.searchButton)
		self.searchText.Bind(wx.EVT_TEXT_ENTER, self.onSearch)

		# Online request search panel events
		self.Bind(wx.EVT_BUTTON, self.onOnlineRequestSearch, self.onlineRequestSearchButton)
		self.onlineRequestTitleText.Bind(wx.EVT_TEXT_ENTER, self.onOnlineRequestSearch)

		# New arrivals panel events
		self.Bind(wx.EVT_BUTTON, self.onNewArrivalsLoad, self.newArrivalsLoadButton)

		# Popular books panel events
		self.Bind(wx.EVT_BUTTON, self.onPopularBooksLoad, self.popularBooksLoadButton)

		# Detailed search panel events
		self.Bind(wx.EVT_BUTTON, self.onDetailedSearch, self.detailedSearchButton)
		self.detailedTitleText.Bind(wx.EVT_TEXT_ENTER, self.onDetailedSearch)

		# Genre search panel events
		self.Bind(wx.EVT_BUTTON, self.onLoadGenreSubgenres, self.genreLoadSubgenresButton)
		self.Bind(wx.EVT_BUTTON, self.onGenreSearch, self.genreSearchButton)

		# Shared events
		self.Bind(wx.EVT_BUTTON, self.onDetail, self.detailButton)
		self.Bind(wx.EVT_BUTTON, self.onDownload, self.downloadButton)
		self.Bind(wx.EVT_BUTTON, self.onLogout, self.logoutButton)
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onResultSelected, self.resultsList)

		# Close event
		self.Bind(wx.EVT_BUTTON, self.onClose, id=wx.ID_CLOSE)
		self.Bind(wx.EVT_CLOSE, self.onClose)

	def _performLogin(self, username, password):
		"""
		Perform login with given credentials in background thread

		Args:
			username (str): Sapie user ID
			password (str): Sapie password
		"""
		def loginThread():
			"""Background thread for login"""
			try:
				# Initialize client
				if not self.client:
					self.client = sapieClient.SapieClient()

				success, message = self.client.login(username, password)

				# Call UI update on main thread
				wx.CallAfter(self._onLoginComplete, success, message, username)

			except Exception as e:
				log.error(f"Login thread error: {e}", exc_info=True)
				wx.CallAfter(self._onLoginError, str(e))

		# Show progress and disable login button
		self._showProgress()
		self.setStatus(_("ログイン中..."))
		self.loginButtonMain.Enable(False)

		# Start login thread
		thread = threading.Thread(target=loginThread, daemon=True)
		thread.start()

		# Start progress animation timer
		self.progressTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
		self.progressTimer.Start(100)  # Update every 100ms

	def _onProgressTimer(self, evt):
		"""Update progress bar animation"""
		self._updateProgress()

	def _onLoginComplete(self, success, message, username):
		"""
		Handle login completion on main thread

		Args:
			success (bool): Whether login succeeded
			message (str): Login result message
			username (str): Username used for login
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.loginButtonMain.Enable(True)

		if success:
			self.isLoggedIn = True
			self.setStatus(_("ログイン成功"))
			ui.message(_("ログインしました"))

			# Save credentials if checkbox is checked
			if self.rememberCheckbox.GetValue():
				try:
					config.conf["sapieLibrary"]["username"] = username
					config.conf["sapieLibrary"]["password"] = self.passwordText.GetValue()
					config.conf["sapieLibrary"]["saveCredentials"] = True
					log.info("Credentials saved to config")
				except Exception as e:
					log.error(f"Failed to save credentials: {e}", exc_info=True)
			else:
				# Clear saved credentials
				try:
					config.conf["sapieLibrary"]["username"] = ""
					config.conf["sapieLibrary"]["password"] = ""
					config.conf["sapieLibrary"]["saveCredentials"] = False
				except Exception as e:
					log.error(f"Failed to clear credentials: {e}", exc_info=True)

			# Switch to search panel
			self._showSearchPanel()
		else:
			self.setStatus(_("ログイン失敗"))
			wx.MessageBox(
				message,
				_("ログインエラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onLoginError(self, error_msg):
		"""
		Handle login error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.loginButtonMain.Enable(True)

		self.setStatus(_("ログインエラー"))
		wx.MessageBox(
			f"ログインエラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def onLoginMain(self, evt):
		"""Handle main login button click"""
		username = self.usernameText.GetValue().strip()
		password = self.passwordText.GetValue()

		# Validate input
		if not username:
			wx.MessageBox(
				_("サピエIDを入力してください。"),
				_("入力エラー"),
				wx.OK | wx.ICON_WARNING
			)
			self.usernameText.SetFocus()
			return

		if not password:
			wx.MessageBox(
				_("パスワードを入力してください。"),
				_("入力エラー"),
				wx.OK | wx.ICON_WARNING
			)
			self.passwordText.SetFocus()
			return

		# Perform login
		self._performLogin(username, password)

	def onLogout(self, evt):
		"""Handle logout button click"""
		if self.client:
			self.client.close()
			self.client = None

		self.isLoggedIn = False
		self.setStatus(_("ログアウトしました"))
		ui.message(_("ログアウトしました"))

		# Clear search results
		self.resultsList.DeleteAllItems()
		self.searchResults = []

		# Switch back to login panel
		self._showLoginPanel()

	def onSearch(self, evt):
		"""Handle regular search button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("検索する前にログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		title = self.searchText.GetValue().strip()
		author = self.authorText.GetValue().strip()

		# Require at least one search term
		if not title and not author:
			wx.MessageBox(
				_("タイトルまたは著者を入力してください。"),
				_("入力エラー"),
				wx.OK | wx.ICON_WARNING
			)
			self.searchText.SetFocus()
			return

		# Determine book type
		typeIndex = self.typeChoice.GetSelection()
		if typeIndex == 0:
			bookType = "braille"
		else:
			bookType = "daisy"

		# Get data type (DAISY only) - S00201
		dataTypeIndex = self.dataTypeChoice.GetSelection()
		dataType = ""
		if bookType == "daisy" and dataTypeIndex > 0:
			# Map index to S00201 value: 1=22 (audio), 2=33 (text), 3=42 (multimedia)
			dataTypeMap = {"1": "22", "2": "33", "3": "42"}
			dataType = dataTypeMap.get(str(dataTypeIndex), "")

		# Get category - S00218
		categoryIndex = self.categoryChoice.GetSelection()
		category = ""
		if categoryIndex > 0:
			# Map index to S00218 value: 1=1 (book), 2=2 (serial), 3=3 (other)
			category = str(categoryIndex)

		# Get include NDL flag - S00262
		includeNDL = self.includeNDLCheckbox.GetValue()

		# Perform search in background thread
		search_params = {
			"title": title,
			"author": author,
			"data_type": dataType,
			"category": category,
			"include_ndl": includeNDL
		}
		self._performSearch(bookType, search_params)

	def onOnlineRequestSearch(self, evt):
		"""Handle online request search button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("検索する前にログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		title = self.onlineRequestTitleText.GetValue().strip()
		author = self.onlineRequestAuthorText.GetValue().strip()

		# Require at least one search term
		if not title and not author:
			wx.MessageBox(
				_("タイトルまたは著者を入力してください。"),
				_("入力エラー"),
				wx.OK | wx.ICON_WARNING
			)
			self.onlineRequestTitleText.SetFocus()
			return

		# Get material type - S00201
		materialTypeIndex = self.onlineRequestMaterialTypeChoice.GetSelection()
		materialType = ""
		if materialTypeIndex > 0:
			# Map index to S00201 value: 1=11 (braille), 2=22 (audio DAISY), 3=33 (text DAISY), 4=42 (multimedia DAISY)
			materialTypeMap = {"1": "11", "2": "22", "3": "33", "4": "42"}
			materialType = materialTypeMap.get(str(materialTypeIndex), "")

		# Get category - S00218
		categoryIndex = self.onlineRequestCategoryChoice.GetSelection()
		category = ""
		if categoryIndex > 0:
			# Map index to S00218 value: 1=1 (book), 2=2 (serial), 3=3 (other)
			category = str(categoryIndex)

		# Perform online request search in background thread
		search_params = {
			"title": title,
			"author": author,
			"material_type": materialType,
			"category": category
		}
		self._performOnlineRequestSearch(search_params)

	def onNewArrivalsLoad(self, evt):
		"""Handle new arrivals load button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("ログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Determine book type
		typeIndex = self.newArrivalsTypeChoice.GetSelection()
		if typeIndex == 0:
			bookType = "braille"
		else:
			bookType = "daisy"

		# Determine period
		periodIndex = self.newArrivalsPeriodChoice.GetSelection()
		if periodIndex == 1:
			period = "month"
		else:
			period = "week"

		# Perform new arrivals retrieval in background thread
		self._performNewArrivalsLoad(bookType, period)

	def onPopularBooksLoad(self, evt):
		"""Handle popular books load button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("ログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Determine ranking type based on selection
		typeIndex = self.popularBooksTypeChoice.GetSelection()
		# Mapping: 0=braille_download, 1=daisy_download, 2=daisy_play, 3=braille_request, 4=daisy_request
		ranking_types = [
			"braille_download",      # 0: 点字ダウンロードランキング
			"daisy_download",        # 1: デイジーダウンロードランキング
			"daisy_play",            # 2: デイジー再生ランキング
			"braille_request",       # 3: 点字オンラインリクエストランキング
			"daisy_request"          # 4: 録音オンラインリクエストランキング
		]

		rankingType = ranking_types[typeIndex] if typeIndex < len(ranking_types) else "braille_download"

		# Perform popular books retrieval in background thread
		self._performPopularBooksLoad(rankingType)

	def onDetailedSearch(self, evt):
		"""Handle detailed search button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("検索する前にログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Collect all search parameters
		search_params = {}

		# Search terms
		search_params["title"] = self.detailedTitleText.GetValue().strip()
		search_params["title_method"] = str(self.detailedTitleMethodChoice.GetSelection() + 1)
		search_params["author"] = self.detailedAuthorText.GetValue().strip()
		search_params["author_method"] = str(self.detailedAuthorMethodChoice.GetSelection() + 1)
		search_params["keyword"] = self.detailedKeywordText.GetValue().strip()
		search_params["keyword_method"] = str(self.detailedKeywordMethodChoice.GetSelection() + 1)
		search_params["exclude_abstract"] = "1" if self.detailedExcludeAbstractCheckbox.GetValue() else ""
		search_params["publisher"] = self.detailedPublisherText.GetValue().strip()
		search_params["ndc"] = self.detailedNDCText.GetValue().strip()
		search_params["genre"] = self.detailedGenreText.GetValue().strip()
		search_params["isbn"] = self.detailedISBNText.GetValue().strip()
		search_params["braille_num"] = self.detailedBrailleNumText.GetValue().strip()
		search_params["producer_id"] = self.detailedProducerIDText.GetValue().strip()
		search_params["holder_id"] = self.detailedHolderIDText.GetValue().strip()

		# Checkboxes
		search_params["has_content"] = "1" if self.detailedHasContentCheckbox.GetValue() else ""
		search_params["online_request"] = "1" if self.detailedOnlineRequestCheckbox.GetValue() else ""
		search_params["include_ndl"] = "5" if self.detailedIncludeNDLCheckbox.GetValue() else ""

		# Material type
		matTypeIdx = self.detailedMaterialTypeChoice.GetSelection()
		matTypeMap = ["", "1", "11", "12", "2", "21", "22", "23", "24", "3", "31", "32", "33", "42", "5", "9"]
		search_params["material_type"] = matTypeMap[matTypeIdx] if matTypeIdx < len(matTypeMap) else ""
		search_params["daisy_only"] = "1" if self.detailedDaisyOnlyCheckbox.GetValue() else ""

		# Braille detail
		braille_details = []
		if self.detailedBrailleNoAbbrevCheckbox.GetValue():
			braille_details.append("11")
		if self.detailedBrailleAbbrevCheckbox.GetValue():
			braille_details.append("12")
		if self.detailedKanBrailleCheckbox.GetValue():
			braille_details.append("13")
		if self.detailedRokutenCheckbox.GetValue():
			braille_details.append("14")
		search_params["braille_detail"] = ",".join(braille_details)

		# Catalog type
		search_params["catalog_type"] = str(self.detailedCatalogTypeChoice.GetSelection() + 1)

		# Category
		catIdx = self.detailedCategoryChoice.GetSelection()
		search_params["category"] = str(catIdx) if catIdx > 0 else ""

		# Target
		targetIdx = self.detailedTargetChoice.GetSelection()
		search_params["target"] = str(targetIdx) if targetIdx > 0 else ""

		# Loan format
		loanIdx = self.detailedLoanFormatChoice.GetSelection()
		loanMap = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "12", "99"]
		search_params["loan_format"] = loanMap[loanIdx] if loanIdx < len(loanMap) else ""

		# Production status
		prodIdx = self.detailedProductionStatusChoice.GetSelection()
		search_params["production_status"] = str(prodIdx) if prodIdx > 0 else ""

		# Graphic
		graphIdx = self.detailedGraphicChoice.GetSelection()
		search_params["graphic"] = str(graphIdx) if graphIdx > 0 else ""

		# Audio compression
		audioIdx = self.detailedAudioCompChoice.GetSelection()
		search_params["audio_comp"] = str(audioIdx) if audioIdx > 0 else ""

		# Date ranges
		search_params["orig_pub_from"] = self.detailedOrigPubFromText.GetValue().strip()
		search_params["orig_pub_to"] = self.detailedOrigPubToText.GetValue().strip()
		search_params["braille_pub_from"] = self.detailedBraillePubFromText.GetValue().strip()
		search_params["braille_pub_to"] = self.detailedBraillePubToText.GetValue().strip()
		search_params["complete_from"] = self.detailedCompleteFromText.GetValue().strip()
		search_params["complete_to"] = self.detailedCompleteToText.GetValue().strip()

		# Display count
		displayIdx = self.detailedDisplayCountChoice.GetSelection()
		displayMap = ["50", "100", "200", "300"]
		search_params["display_count"] = displayMap[displayIdx]

		# Require at least one search term
		has_search_term = any([
			search_params["title"], search_params["author"], search_params["keyword"],
			search_params["publisher"], search_params["ndc"], search_params["genre"],
			search_params["isbn"], search_params["braille_num"], search_params["producer_id"],
			search_params["holder_id"], search_params["orig_pub_from"], search_params["orig_pub_to"],
			search_params["braille_pub_from"], search_params["braille_pub_to"],
			search_params["complete_from"], search_params["complete_to"]
		])

		if not has_search_term:
			wx.MessageBox(
				_("少なくとも1つの検索条件を入力してください。"),
				_("入力エラー"),
				wx.OK | wx.ICON_WARNING
			)
			self.detailedTitleText.SetFocus()
			return

		self._performDetailedSearch(search_params)

	def onLoadGenreSubgenres(self, evt):
		"""Handle load subgenres button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("サブジャンルを取得する前にログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Get selected main genre (1-17)
		genreIdx = self.genreMainChoice.GetSelection()
		genre_code = f"{genreIdx + 1:02d}"  # Format as 01-17

		self._performLoadSubgenres(genre_code)

	def onGenreSearch(self, evt):
		"""Handle genre search button click"""
		if not self.client or not self.client.is_logged_in():
			wx.MessageBox(
				_("検索する前にログインしてください。"),
				_("ログインが必要"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Check if subgenre is selected
		if not self.genreSubChoice.IsEnabled() or self.genreSubChoice.GetSelection() < 0:
			wx.MessageBox(
				_("サブジャンルを取得・選択してください。"),
				_("サブジャンル未選択"),
				wx.OK | wx.ICON_WARNING
			)
			return

		# Get selected subgenre code
		subgenreIdx = self.genreSubChoice.GetSelection()
		if subgenreIdx >= len(self.genreSubgenreCodes):
			wx.MessageBox(
				_("サブジャンルが正しく選択されていません。"),
				_("選択エラー"),
				wx.OK | wx.ICON_ERROR
			)
			return

		subgenre_code = self.genreSubgenreCodes[subgenreIdx]

		# Get material type
		materialIdx = self.genreMaterialTypeChoice.GetSelection()
		materialMap = ["", "1", "11", "12", "2", "21", "22", "23", "24", "3", "31", "32", "33", "42", "5", "9"]
		material_type = materialMap[materialIdx] if materialIdx < len(materialMap) else ""

		# Get filters
		has_content = self.genreHasContentCheckbox.GetValue()
		daisy_only = self.genreDaisyOnlyCheckbox.GetValue()

		# Get production status
		prodStatusIdx = self.genreProductionStatusChoice.GetSelection()
		production_status = str(prodStatusIdx) if prodStatusIdx > 0 else ""

		# Get date ranges
		orig_pub_from = self.genreOrigPubFromText.GetValue().strip()
		orig_pub_to = self.genreOrigPubToText.GetValue().strip()
		complete_from = self.genreCompleteFromText.GetValue().strip()
		complete_to = self.genreCompleteToText.GetValue().strip()

		# Perform search
		self._performGenreSearch(subgenre_code, material_type, has_content, production_status,
		                         orig_pub_from, orig_pub_to, complete_from, complete_to, daisy_only)

	def _performSearch(self, bookType, search_params):
		"""
		Perform search in background thread

		Args:
			bookType (str): Type of book to search for ("braille" or "daisy")
			search_params (dict): Search parameters including title, author, etc.
		"""
		def searchThread():
			"""Background thread for search"""
			try:
				success, results = self.client.search(bookType, search_params)

				# Call UI update on main thread
				wx.CallAfter(self._onSearchComplete, success, results)

			except Exception as e:
				log.error(f"Search thread error: {e}", exc_info=True)
				wx.CallAfter(self._onSearchError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("検索中..."))
		self.searchButton.Enable(False)

		# Start search thread
		thread = threading.Thread(target=searchThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onSearchComplete(self, success, results):
		"""
		Handle search completion on main thread

		Args:
			success (bool): Whether search succeeded
			results (list or str): Search results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.searchButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"検索完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の結果が見つかりました"))
		else:
			self.setStatus(_("検索失敗"))
			wx.MessageBox(
				results,  # Error message
				_("検索エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onSearchError(self, error_msg):
		"""
		Handle search error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.searchButton.Enable(True)
		self.onlineRequestSearchButton.Enable(True)

		self.setStatus(_("検索エラー"))
		wx.MessageBox(
			f"検索エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performDetailedSearch(self, search_params):
		"""
		Perform detailed search in background thread

		Args:
			search_params (dict): Detailed search parameters
		"""
		def searchThread():
			"""Background thread for detailed search"""
			try:
				success, results = self.client.detailed_search(search_params)

				# Call UI update on main thread
				wx.CallAfter(self._onDetailedSearchComplete, success, results)

			except Exception as e:
				log.error(f"Detailed search thread error: {e}", exc_info=True)
				wx.CallAfter(self._onDetailedSearchError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("詳細検索中..."))
		self.detailedSearchButton.Enable(False)

		# Start search thread
		thread = threading.Thread(target=searchThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onDetailedSearchComplete(self, success, results):
		"""
		Handle detailed search completion on main thread

		Args:
			success (bool): Whether search succeeded
			results (list or str): Search results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.detailedSearchButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"詳細検索完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の結果が見つかりました"))
		else:
			self.setStatus(_("詳細検索失敗"))
			wx.MessageBox(
				results,  # Error message
				_("詳細検索エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onDetailedSearchError(self, error_msg):
		"""
		Handle detailed search error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.detailedSearchButton.Enable(True)

		self.setStatus(_("詳細検索エラー"))
		wx.MessageBox(
			f"詳細検索エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performLoadSubgenres(self, genre_code):
		"""
		Load subgenres for selected main genre in background thread

		Args:
			genre_code (str): Main genre code (01-17)
		"""
		def loadThread():
			"""Background thread for loading subgenres"""
			try:
				success, subgenres = self.client.get_genre_subgenres(genre_code)

				# Call UI update on main thread
				wx.CallAfter(self._onLoadSubgenresComplete, success, subgenres)

			except Exception as e:
				log.error(f"Load subgenres thread error: {e}", exc_info=True)
				wx.CallAfter(self._onLoadSubgenresError, str(e))

		# Show progress and disable button
		self._showProgress()
		self.setStatus(_("サブジャンル取得中..."))
		self.genreLoadSubgenresButton.Enable(False)

		# Start load thread
		thread = threading.Thread(target=loadThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onLoadSubgenresComplete(self, success, subgenres):
		"""
		Handle load subgenres completion on main thread

		Args:
			success (bool): Whether loading succeeded
			subgenres (list or str): List of tuples (code, name) or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.genreLoadSubgenresButton.Enable(True)

		if success and subgenres:
			# Update subgenre choice with loaded subgenres
			subgenre_names = [name for code, name in subgenres]
			self.genreSubgenreCodes = [code for code, name in subgenres]

			self.genreSubChoice.Clear()
			self.genreSubChoice.AppendItems(subgenre_names)
			self.genreSubChoice.SetSelection(0)
			self.genreSubChoice.Enable(True)

			self.setStatus(_(f"サブジャンル取得完了: {len(subgenres)}件"))
			ui.message(_(f"{len(subgenres)}件のサブジャンルが見つかりました"))
		elif success and not subgenres:
			self.setStatus(_("サブジャンルが見つかりませんでした"))
			wx.MessageBox(
				_("このジャンルにはサブジャンルがありません。"),
				_("サブジャンルなし"),
				wx.OK | wx.ICON_INFORMATION
			)
		else:
			self.setStatus(_("サブジャンル取得失敗"))
			wx.MessageBox(
				subgenres,  # Error message
				_("サブジャンル取得エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onLoadSubgenresError(self, error_msg):
		"""
		Handle load subgenres error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.genreLoadSubgenresButton.Enable(True)

		self.setStatus(_("サブジャンル取得エラー"))
		wx.MessageBox(
			f"サブジャンル取得エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performGenreSearch(self, subgenre_code, material_type="", has_content=False, production_status="",
	                        orig_pub_from="", orig_pub_to="", complete_from="", complete_to="", daisy_only=False):
		"""
		Perform genre search in background thread

		Args:
			subgenre_code (str): Subgenre code (e.g., "0101")
			material_type (str): Material type code
			has_content (bool): Only materials with content
			production_status (str): Production status
			orig_pub_from (str): Original publication date from
			orig_pub_to (str): Original publication date to
			complete_from (str): Completion date from
			complete_to (str): Completion date to
			daisy_only (bool): DAISY only
		"""
		def searchThread():
			"""Background thread for genre search"""
			try:
				success, results = self.client.genre_search(subgenre_code, material_type, has_content,
				                                            production_status, orig_pub_from, orig_pub_to,
				                                            complete_from, complete_to, daisy_only)

				# Call UI update on main thread
				wx.CallAfter(self._onGenreSearchComplete, success, results)

			except Exception as e:
				log.error(f"Genre search thread error: {e}", exc_info=True)
				wx.CallAfter(self._onGenreSearchError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("ジャンル検索中..."))
		self.genreSearchButton.Enable(False)

		# Start search thread
		thread = threading.Thread(target=searchThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onGenreSearchComplete(self, success, results):
		"""
		Handle genre search completion on main thread

		Args:
			success (bool): Whether search succeeded
			results (list or str): Search results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.genreSearchButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"ジャンル検索完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の結果が見つかりました"))
		else:
			self.setStatus(_("ジャンル検索失敗"))
			wx.MessageBox(
				results,  # Error message
				_("ジャンル検索エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onGenreSearchError(self, error_msg):
		"""
		Handle genre search error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.genreSearchButton.Enable(True)

		self.setStatus(_("ジャンル検索エラー"))
		wx.MessageBox(
			f"ジャンル検索エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performOnlineRequestSearch(self, search_params):
		"""
		Perform online request search in background thread

		Args:
			search_params (dict): Search parameters including title, author, material_type, category
		"""
		def searchThread():
			"""Background thread for online request search"""
			try:
				success, results = self.client.search_online_request(search_params)

				# Call UI update on main thread
				wx.CallAfter(self._onOnlineRequestSearchComplete, success, results)

			except Exception as e:
				log.error(f"Online request search thread error: {e}", exc_info=True)
				wx.CallAfter(self._onOnlineRequestSearchError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("オンラインリクエスト検索中..."))
		self.onlineRequestSearchButton.Enable(False)

		# Start search thread
		thread = threading.Thread(target=searchThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onOnlineRequestSearchComplete(self, success, results):
		"""
		Handle online request search completion on main thread

		Args:
			success (bool): Whether search succeeded
			results (list or str): Search results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.onlineRequestSearchButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"オンラインリクエスト検索完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の結果が見つかりました"))
		else:
			self.setStatus(_("オンラインリクエスト検索失敗"))
			wx.MessageBox(
				results,  # Error message
				_("検索エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onOnlineRequestSearchError(self, error_msg):
		"""
		Handle online request search error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.onlineRequestSearchButton.Enable(True)

		self.setStatus(_("オンラインリクエスト検索エラー"))
		wx.MessageBox(
			f"オンラインリクエスト検索エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performNewArrivalsLoad(self, bookType, period):
		"""
		Perform new arrivals retrieval in background thread

		Args:
			bookType (str): Type of book to retrieve ("braille" or "daisy")
			period (str): Time period ("week" or "month")
		"""
		def loadThread():
			"""Background thread for new arrivals load"""
			try:
				success, results = self.client.get_new_arrivals(bookType, period)

				# Call UI update on main thread
				wx.CallAfter(self._onNewArrivalsLoadComplete, success, results)

			except Exception as e:
				log.error(f"New arrivals load thread error: {e}", exc_info=True)
				wx.CallAfter(self._onNewArrivalsLoadError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("新着情報を取得中..."))
		self.newArrivalsLoadButton.Enable(False)

		# Start load thread
		thread = threading.Thread(target=loadThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onNewArrivalsLoadComplete(self, success, results):
		"""
		Handle new arrivals load completion on main thread

		Args:
			success (bool): Whether load succeeded
			results (list or str): Load results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.newArrivalsLoadButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"新着情報取得完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の新着情報が見つかりました"))
		else:
			self.setStatus(_("新着情報取得失敗"))
			wx.MessageBox(
				results,  # Error message
				_("エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onNewArrivalsLoadError(self, error_msg):
		"""
		Handle new arrivals load error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.newArrivalsLoadButton.Enable(True)

		self.setStatus(_("新着情報取得エラー"))
		wx.MessageBox(
			f"新着情報取得エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _performPopularBooksLoad(self, bookType):
		"""
		Perform popular books retrieval in background thread

		Args:
			bookType (str): Type of book to retrieve ("braille" or "daisy")
		"""
		def loadThread():
			"""Background thread for popular books load"""
			try:
				success, results = self.client.get_popular_books(bookType)

				# Call UI update on main thread
				wx.CallAfter(self._onPopularBooksLoadComplete, success, results)

			except Exception as e:
				log.error(f"Popular books load thread error: {e}", exc_info=True)
				wx.CallAfter(self._onPopularBooksLoadError, str(e))

		# Clear previous results and show progress
		self.resultsList.DeleteAllItems()
		self.searchResults = []
		self._showProgress()
		self.setStatus(_("人気のある本を取得中..."))
		self.popularBooksLoadButton.Enable(False)

		# Start load thread
		thread = threading.Thread(target=loadThread, daemon=True)
		thread.start()

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

	def _onPopularBooksLoadComplete(self, success, results):
		"""
		Handle popular books load completion on main thread

		Args:
			success (bool): Whether load succeeded
			results (list or str): Load results or error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.popularBooksLoadButton.Enable(True)

		if success:
			self.searchResults = results
			self._displayResults(results)
			self.setStatus(_(f"人気のある本取得完了: {len(results)}件"))
			ui.message(_(f"{len(results)}件の人気のある本が見つかりました"))
		else:
			self.setStatus(_("人気のある本取得失敗"))
			wx.MessageBox(
				results,  # Error message
				_("エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def _onPopularBooksLoadError(self, error_msg):
		"""
		Handle popular books load error on main thread

		Args:
			error_msg (str): Error message
		"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.popularBooksLoadButton.Enable(True)

		self.setStatus(_("人気のある本取得エラー"))
		wx.MessageBox(
			f"人気のある本取得エラー: {error_msg}",
			_("エラー"),
			wx.OK | wx.ICON_ERROR
		)

	def _displayResults(self, results):
		"""
		Display search results in the list

		Args:
			results (list): List of book dictionaries
		"""
		self.resultsList.DeleteAllItems()

		for i, book in enumerate(results):
			index = self.resultsList.InsertItem(i, book.get('title', ''))
			self.resultsList.SetItem(index, 1, book.get('author', ''))
			self.resultsList.SetItem(index, 2, book.get('type', ''))
			# Show production library for online request results
			if book.get('is_online_request', False):
				self.resultsList.SetItem(index, 3, book.get('production_lib', ''))
			else:
				self.resultsList.SetItem(index, 3, '')

		# Select first item if available
		if results:
			self.resultsList.Select(0)
			self.resultsList.SetFocus()

	def onResultSelected(self, evt):
		"""Handle result list item selection"""
		selectedIndex = self.resultsList.GetFirstSelected()

		# Enable download button only if:
		# 1. A result is selected
		# 2. The result is NOT an online request (online requests can't be downloaded)
		if selectedIndex >= 0 and selectedIndex < len(self.searchResults):
			book = self.searchResults[selectedIndex]
			is_online_request = book.get('is_online_request', False)
			self.downloadButton.Enable(not is_online_request)

			# Enable detail button for all results (will check parameters when clicked)
			self.detailButton.Enable(True)
		else:
			self.downloadButton.Enable(False)
			self.detailButton.Enable(False)

	def onDownload(self, evt):
		"""Handle download button click"""
		selectedIndex = self.resultsList.GetFirstSelected()
		if selectedIndex < 0:
			return

		if selectedIndex >= len(self.searchResults):
			return

		book = self.searchResults[selectedIndex]

		# Get download path from config
		downloadPath = config.conf["sapieLibrary"].get("downloadPath", "")

		if not downloadPath:
			# Prompt for download folder
			dlg = wx.DirDialog(
				self,
				_("ダウンロード先フォルダを選択"),
				style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
			)

			if dlg.ShowModal() == wx.ID_OK:
				downloadPath = dlg.GetPath()
				# Save for next time
				config.conf["sapieLibrary"]["downloadPath"] = downloadPath
			else:
				dlg.Destroy()
				return

			dlg.Destroy()

		# Show progress bar and disable download button
		self._showProgress()
		self.downloadButton.Enable(False)
		self.setStatus(_(f"ダウンロード中: {book.get('title', '')}"))
		ui.message(_("ダウンロードを開始しました"))

		# Start progress animation timer if not already running
		if not hasattr(self, 'progressTimer') or not self.progressTimer.IsRunning():
			self.progressTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self._onProgressTimer, self.progressTimer)
			self.progressTimer.Start(100)  # Update every 100ms

		# Start download in background thread
		thread = downloadThread.DownloadThread(
			self.client,
			book.get('id', ''),
			downloadPath,
			self._onDownloadComplete,
			self._onDownloadError,
			book.get('format', 'BRL'),  # Pass format for DAISY vs Braille
			book.get('s00202', None),  # Pass actual S00202 value from search results
			book.get('s00215', None)   # Pass actual S00215 value (priority/source)
		)
		thread.start()

	def _onDownloadComplete(self, bookId, filePath):
		"""
		Callback for download completion

		Args:
			bookId (str): Book ID
			filePath (str): Downloaded file path
		"""
		wx.CallAfter(self._downloadCompleteUI, bookId, filePath)

	def _downloadCompleteUI(self, bookId, filePath):
		"""UI update for download completion"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.downloadButton.Enable(True)

		self.setStatus(_("ダウンロード完了"))
		ui.message(_(f"ダウンロード完了: {filePath}"))

		# Store file path and show view options dialog
		self._lastDownloadedFile = filePath

		def showViewDialog():
			dlg = ViewOptionsDialog(self, filePath)
			dlg.ShowModal()
			dlg.Destroy()

		wx.CallLater(500, showViewDialog)

	def _onDownloadError(self, bookId, errorMsg):
		"""
		Callback for download error

		Args:
			bookId (str): Book ID
			errorMsg (str): Error message
		"""
		wx.CallAfter(self._downloadErrorUI, bookId, errorMsg)

	def _downloadErrorUI(self, bookId, errorMsg):
		"""UI update for download error"""
		# Stop progress timer and hide progress bar
		if hasattr(self, 'progressTimer'):
			self.progressTimer.Stop()
		self._hideProgress()
		self.downloadButton.Enable(True)

		self.setStatus(_("ダウンロードエラー"))
		wx.MessageBox(
			errorMsg,
			_("ダウンロードエラー"),
			wx.OK | wx.ICON_ERROR
		)

	def setStatus(self, text):
		"""
		Update status text

		Args:
			text (str): Status message
		"""
		self.statusText.SetLabel(text)
		log.info(f"Status: {text}")

	def onDetail(self, evt):
		"""Handle detail button click"""
		try:
			selectedIndex = self.resultsList.GetFirstSelected()

			if selectedIndex < 0:
				ui.message(_("項目が選択されていません"))
				return

			if selectedIndex >= len(self.searchResults):
				ui.message(_("インデックスエラー"))
				return

			book = self.searchResults[selectedIndex]
			s00221 = book.get('s00221', '')
			s00222 = book.get('s00222', '')

			# S00222 (Book ID) is required, S00221 (Search ID) is optional
			if not s00222:
				ui.message(_("この図書の詳細情報を取得できません"))
				gui.messageBox(
					_(f"この図書の詳細情報を取得できません（図書IDが見つかりません）。"),
					_("詳細情報エラー"),
					wx.OK | wx.ICON_WARNING
				)
				return

			# Show progress and disable button
			self.detailButton.Enable(False)
			self.setStatus(_(f"詳細情報を取得中: {book.get('title', '')}"))
			ui.message(_("詳細情報を取得しています..."))

			# Fetch details in background thread
			def fetch_details():
				try:
					success, result = self.client.get_book_details(s00221, s00222)
					wx.CallAfter(self._onDetailComplete, success, result, book)
				except Exception as e:
					log.error(f"Error fetching details: {e}")
					wx.CallAfter(self._onDetailComplete, False, str(e), book)

			import threading
			thread = threading.Thread(target=fetch_details)
			thread.daemon = True
			thread.start()

		except Exception as e:
			log.error(f"Error in onDetail: {e}", exc_info=True)
			ui.message(_("エラーが発生しました"))
			gui.messageBox(
				_(f"詳細情報の取得中にエラーが発生しました:\n{str(e)}"),
				_("エラー"),
				wx.OK | wx.ICON_ERROR
			)
			self.detailButton.Enable(True)

	def _onDetailComplete(self, success, result, book):
		"""Handle detail fetch completion"""
		self.detailButton.Enable(True)

		if success:
			# Show detail dialog
			dlg = BookDetailDialog(self, book.get('title', ''), result)
			dlg.ShowModal()
			dlg.Destroy()
			self.setStatus(_("詳細情報を取得しました"))
		else:
			self.setStatus(_("詳細情報の取得に失敗しました"))
			gui.messageBox(
				_(f"詳細情報の取得に失敗しました:\n{result}"),
				_("エラー"),
				wx.OK | wx.ICON_ERROR
			)

	def onOpenBook(self, evt):
		"""Handle open book button click"""
		from . import bookViewer
		bookViewer.browse_and_open_book(self)

	def onClose(self, evt):
		"""Handle dialog close"""
		# Stop progress timer if running
		if hasattr(self, 'progressTimer') and self.progressTimer.IsRunning():
			self.progressTimer.Stop()

		# Close client connection
		if self.client:
			self.client.close()
			self.client = None

		self.Destroy()


class ViewOptionsDialog(wx.Dialog):
	"""Dialog asking if user wants to view a book"""

	def __init__(self, parent, filePath, is_new_download=True):
		super(ViewOptionsDialog, self).__init__(
			parent,
			title=_("図書を開く"),
			style=wx.DEFAULT_DIALOG_STYLE
		)
		self.filePath = filePath

		# Detect book type
		from . import bookViewer
		self.bookType = bookViewer.get_book_type(filePath)

		sizer = wx.BoxSizer(wx.VERTICAL)

		# Message
		import os
		filename = os.path.basename(filePath)
		if is_new_download:
			if self.bookType == "daisy":
				msg_text = _("DAISYのダウンロードが完了しました。\nブラウザで開きますか？\n\n{}").format(filename)
			else:
				msg_text = _("ダウンロードが完了しました。\nこの図書を閲覧しますか？")
		else:
			if self.bookType == "daisy":
				msg_text = _("このDAISYをブラウザで開きますか？\n\n{}").format(filename)
			else:
				msg_text = _("この図書を閲覧しますか？\n\n{}").format(filename)
		msg = wx.StaticText(self, label=msg_text)
		sizer.Add(msg, flag=wx.ALL, border=10)

		# Buttons
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.yesBtn = wx.Button(self, wx.ID_YES, label=_("はい(&Y)"))
		self.yesBtn.Bind(wx.EVT_BUTTON, self.onYes)
		btnSizer.Add(self.yesBtn, flag=wx.ALL, border=5)

		self.noBtn = wx.Button(self, wx.ID_NO, label=_("いいえ(&N)"))
		self.noBtn.Bind(wx.EVT_BUTTON, self.onNo)
		btnSizer.Add(self.noBtn, flag=wx.ALL, border=5)

		sizer.Add(btnSizer, flag=wx.ALIGN_CENTER | wx.ALL, border=10)

		self.SetSizer(sizer)
		sizer.Fit(self)
		self.CenterOnParent()
		self.yesBtn.SetFocus()

	def onYes(self, evt):
		"""Open the book using display format from settings"""
		# Get parent before closing
		parent = self.GetParent()
		filePath = self.filePath
		bookType = self.bookType
		self.Close()
		try:
			from . import bookViewer

			if bookType == "daisy":
				# Open DAISY in browser
				bookViewer.open_daisy(filePath)
			else:
				# Get display format from settings
				displayFormat = config.conf["sapieLibrary"].get("displayFormat", "kana")

				if displayFormat == "editor":
					# Open raw braille file in external editor
					bookViewer.open_in_braille_editor(filePath, parent=parent)
				else:
					# Convert and open in notepad
					convert_to_kana = (displayFormat == "kana")
					bookViewer.open_book(filePath, convert_to_kana=convert_to_kana, parent=parent)
		except Exception as e:
			ui.message(_("図書を開けませんでした"))

	def onNo(self, evt):
		"""Close without opening"""
		self.Close()
