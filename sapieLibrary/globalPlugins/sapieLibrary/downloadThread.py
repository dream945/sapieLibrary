# -*- coding: utf-8 -*-
# Sapie Library - Background Download Thread

import threading
import logging

log = logging.getLogger(__name__)

class DownloadThread(threading.Thread):
	"""Background thread for downloading books without blocking NVDA"""

	def __init__(self, client, bookId, downloadPath, onComplete, onError, bookFormat='BRL', s00202=None, s00215=None):
		"""
		Initialize download thread

		Args:
			client: SapieClient instance
			bookId (str): ID of the book to download
			downloadPath (str): Directory to save the file
			onComplete (callable): Callback function on success (bookId, filePath)
			onError (callable): Callback function on error (bookId, errorMsg)
			bookFormat (str): Format of the book - 'BRL' (braille) or 'DAISY'
			s00202 (str): Actual S00202 value from search results (data type code)
			s00215 (str): Actual S00215 value from search results (priority/source code)
		"""
		super().__init__()
		self.client = client
		self.bookId = bookId
		self.downloadPath = downloadPath
		self.onComplete = onComplete
		self.onError = onError
		self.bookFormat = bookFormat
		self.s00202 = s00202
		self.s00215 = s00215
		self.daemon = True  # Thread will terminate when main program exits

	def run(self):
		"""Execute download in background"""
		try:
			log.info(f"Starting download: book={self.bookId}, format={self.bookFormat}, s00202={self.s00202}, s00215={self.s00215}, path={self.downloadPath}")

			# Perform download
			success, result = self.client.download_book(self.bookId, self.downloadPath, self.bookFormat, self.s00202, self.s00215)

			if success:
				log.info(f"Download completed: {result}")
				# Call success callback
				if self.onComplete:
					self.onComplete(self.bookId, result)
			else:
				log.error(f"Download failed: {result}")
				# Call error callback
				if self.onError:
					self.onError(self.bookId, result)

		except Exception as e:
			log.error(f"Download thread error: {e}", exc_info=True)
			# Call error callback
			if self.onError:
				self.onError(self.bookId, str(e))
