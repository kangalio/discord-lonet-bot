from typing import *

import json, base64
from datetime import datetime

from html2text import html2text

import lonet
from lonet import LonetSession
from structures import Task, Lernplan


# Util function
# Extracts a substring based on prefix and postfix. Both `before` and
# `after` can be None
def extract_str(string, before, after=None):
	if before is None:
		start = 0
	else:
		before_index = string.find(before)
		if before_index == -1: return None
		start = before_index + len(before)
	
	if after is None:
		end = None
	else:
		end = string.find(after, start)
		if end == -1: end = None # Right behavior?
	
	return string[start:end]

def get_creds() -> Tuple[str, str]:
	# credit: https://stackoverflow.com/a/20570990/9946772
	def xor(data, key): 
		return bytearray(a^b for a, b in zip(*map(bytearray, [data, key])))
	with open("secret/credentials.json") as f:
		creds = json.load(f)
	username = creds["username"]
	password = xor(base64.b64decode(creds["password"]), b"doireallywanttostorecredslikethis").decode("UTF-8")
	
	return username, password

def parse_thema_tbody(session, name, table):
	tasks: List[Task] = []
	for row in table.find_all("tr")[1:]: # skip header row
		cells = row.find_all("td")
		
		task_name = cells[2].get_text()
		
		deadline_str = cells[3].string.strip()
		if deadline_str == "":
			task_deadline = None
		else:
			task_deadline = datetime.strptime(deadline_str, "%d.%M.%Y %H:%S")
		
		popup_url = cells[2].find("a")["onclick"][18:-3]
		popup_text = session.navigate(popup_url, peek=True, raw_response=True)
		html = lonet.bs(popup_text)
		
		try:
			# can be both <p> or <div>, we can't rely on that
			description_html = html.find(class_="panel")
			if description_html:
				task_description = html2text(str(description_html)).strip()
			else:
				task_description = "<no task description found>"
		except Exception:
			task_description = "<error while getting description>"
		
		task_link = extract_str(popup_text, '"l1_link":"', '"') # we gotta extract from <script> tag
		
		tasks.append(Task(task_name, task_description, task_deadline, task_link))
	
	return tasks

def get_lernplan():
	session = LonetSession()

	# login
	username, password = get_creds()
	html = session.login(username, password)
	del password # not _really_ secure but better than nothing

	# go to Klassennübersicht page
	for link in html.find_all("a"):
		if link.string and "10d" in link.string:
			html = session.navigate(link["href"])
			break

	# go to Lernplan page
	html = session.navigate(html.find(id="link_learning_plan")["href"])
	
	lernplan = Lernplan({})
	# `html` is overwritten in the following
	for option in html.find("select", {"name": "select_mapping"}).find_all("option"):
		thema = option.string
		url = option["value"]
		
		html = session.navigate(url, peek=True)
		# ~ print(html.prettify())
		table = html.find("table", class_="table_list")
		if table:
			tasks = parse_thema_tbody(session, thema, table)
		else:
			tasks = []
		
		lernplan.themen[thema] = tasks
	
	return lernplan
 
