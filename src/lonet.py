import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def bs(*args, **kwargs):
	return BeautifulSoup(*args, **kwargs, features="lxml") # change to html.parser if needed

class LonetSession:
	def __init__(self):
		import re # for sid extraction
		
		self._session = requests.Session()
		self._sid = None
		self._current_url = None
	
	def _session_wrapper(self, fn, url: str, *args, params={}, headers={}, timeout=20, **kwargs) -> requests.Response:
		headers = {**headers, "Host": "www.lo-net2.de", "Origin": "https://lo-net2.de"}
		
		try:
			response = (fn)(url, *args, headers=headers, timeout=timeout, **kwargs)
		except requests.exceptions.ConnectTimeout as e:
			# `raise from None` to suppress the useless "caused by [...] caused by [...]" clutter
			raise e from None
		
		return response
	
	def get(self, *args, **kwargs) -> requests.Response:
		return self._session_wrapper(self._session.get, *args, **kwargs)
	
	def post(self, *args, **kwargs) -> requests.Response:
		return self._session_wrapper(self._session.post, *args, **kwargs)
	
	def login(self, username: str, password: str) -> BeautifulSoup:
		import re
		
		# GET login page to acquire sid
		login_page = self.get("https://lo-net2.de/wws/100001.php").text
		sid_match = re.compile(r"sid=(\d+)").search(login_page)
		if sid_match:
			self._sid = sid_match.group(1)
		else:
			raise Exception("huh?")
		
		login_response = self.post("https://lo-net2.de/wws/100001.php", files={
			"login_nojs": (None, ""),
			"login_login": (None, username),
			"login_password": (None, password),
			"login_submit": (None, "Einloggen"),
			"language": (None, "2"),
		})
		self._current_url = login_response.url
		return bs(login_response.text)
	
	@property
	def url(self):
		return self._current_url
	
	# peek: if True, don't actually navigate, but only download the page and then go back
	def navigate(self, url, peek=False, request_fn=None, raw_response=False) -> BeautifulSoup:
		if request_fn is None:
			request_fn = lambda url: self.get(url)
		
		response = (request_fn)(urljoin(self._current_url, url))
		self._current_url = response.url
		return response.text if raw_response else bs(response.text)
