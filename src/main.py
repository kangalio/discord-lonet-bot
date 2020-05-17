from __future__ import annotations
from typing import *
import os, json, logging, asyncio
from datetime import datetime

import discord

from scrape import get_lernplan
from structures import Task


class Index:
	def __init__(self):
		self._index = {
			"tasks": []
		}
	
	@staticmethod
	def open(filename: str) -> Index:
		index = Index()
		if os.path.exists(filename):
			with open(filename) as f:
				index._index = json.load(f)
		return index
	
	def save(self, filename: str) -> None:
		with open(filename, "w") as f:
			json.dump(self._index, f, indent=2)
	
	def _get_task_json(self, thema: str, task: Task) -> Optional[Any]:
		for task_json in self._index["tasks"]:
			if task_json["name"] == task.name and task_json["thema"] == thema:
				return task_json
		return None
	
	def is_task_known(self, *args, **kwargs) -> bool:
		return self._get_task_json(*args, **kwargs) is not None
	
	def get_task_creation_datetime(self, *args, **kwargs) -> Optional[datetime]:
		task = self._get_task_json(*args, **kwargs)
		if task:
			return datetime.fromisoformat(task["registered"])
		else:
			return None
	
	def register_task(self, thema: str, task: Task) -> None:
		self._index["tasks"].append({
			"name": task.name,
			"thema": thema,
			"registered": datetime.now().isoformat(),
		})

async def check_lonet(channel, refresh=False) -> None:
	lernplan = get_lernplan()
	print(f"Checking lonet ({datetime.now()})")
	
	all_tasks = []
	for thema, tasks in lernplan.themen.items():
		for task in tasks:
			print(f"task: {task.name} ({thema})")
			
			task_was_known = index.is_task_known(thema, task)
			index.register_task(thema, task)
			# if not refreshing, stop right here before this task gets written to the list of
			# outputted tasks
			if task_was_known and not refresh:
				print(f"(skipping)")
				continue
			
			creation_time = index.get_task_creation_datetime(thema, task)
			if creation_time is None:
				print("huh? this shouldn't happen")
				continue
			tuple_ = (thema, task, creation_time)
			all_tasks.append(tuple_)
	all_tasks.sort(key=lambda tuple_: tuple_[2])
	
	for thema, task, creation_time in all_tasks:
		if task.deadline:
			deadline_text = datetime.strftime(task.deadline, "%d.%M.%Y %H:%S")
		else:
			deadline_text = "---"
		
		description = task.description
		if len(description) > 2048:
			addendum = "... (Discords Nachrichtenlimit erreicht)"
			description = description[:(2048-len(addendum))] + addendum
		
		embed = discord.Embed(title=f"{thema}: {task.name}", url=task.link, description=description)
		embed.add_field(name="Fällig", value=f"**{deadline_text}**", inline=False)
		embed.set_footer(text="Hinzugefügt am " + datetime.strftime(creation_time, "%d.%m.%Y %H:%M"))
		await channel.send(embed=embed)
	print("Done checking lonet")
	
	index.save("index.json")

client = discord.Client()
logger = logging.getLogger()
is_activated = False
periodic_check_interval = 10 * 60 # in seconds

async def periodically_check(channel, refresh_on_first_run=False):
	has_refreshed = False
	while True:
		try:
			should_refresh = refresh_on_first_run and not has_refreshed
			await check_lonet(channel, refresh=should_refresh)
			has_refreshed = True
		except Exception as e:
			await channel.send(f"An error occurred: {e}")
			logger.exception("Exception duh")
		await asyncio.sleep(periodic_check_interval)

@client.event
async def on_message(msg):
	global is_activated
	
	if msg.content.startswith("lonet activate"):
		if is_activated:
			await msg.channel.send("Bot is already started :thinking:")
		else:
			is_activated = True
			await msg.channel.send("Bot was started")
			await periodically_check(msg.channel, refresh_on_first_run=("refresh" in msg.content))

@client.event
async def on_ready():
	print(f"{client.user} has connected to Discord!")
	print("Remember to activate the bot!")

index = Index.open("index.json")
with open("secret/token.txt") as f:
	token = f.read().strip()
client.run(token)
