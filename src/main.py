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
	
	def is_task_known(self, thema: str, task: Task) -> bool:
		for task_json in self._index["tasks"]:
			if task_json["name"] == task.name and task_json["thema"] == thema:
				return True
		return False
	
	def register_task(self, thema: str, task: Task) -> None:
		self._index["tasks"].append({
			"name": task.name,
			"thema": thema,
			"registered": datetime.now().isoformat(),
		})

async def check_lonet(channel) -> None:
	lernplan = get_lernplan()
	print(f"Checking lonet ({datetime.now()})")
	for thema, tasks in lernplan.themen.items():
		for task in tasks:
			print(f"task: {task.name} ({thema})")
			if index.is_task_known(thema, task):
				print(f"(known)")
				continue # it's a known task, no need to print again
			index.register_task(thema, task)
			
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
			embed.set_footer(text="Hinzugefügt am " + datetime.strftime(datetime.now(), "%d.%m.%Y %H:%S"))
			await channel.send(embed=embed)
	print("Done checking lonet")
	
	index.save("index.json")

client = discord.Client()
logger = logging.getLogger()
is_activated = False
periodic_chart_interval = 10 * 60 # in seconds

async def periodically_check(channel):
	while True:
		try:
			await check_lonet(channel)
		except Exception as e:
			await channel.send(f"An error occurred: {e}")
			logger.exception("Exception duh")
		await asyncio.sleep(periodic_chart_interval)

@client.event
async def on_message(msg):
	global is_activated
	
	if msg.content == "lonet activate":
		if is_activated:
			await msg.channel.send("Bot is already started :thinking:")
		else:
			is_activated = True
			await msg.channel.send("Bot was started")
			await periodically_check(msg.channel)

@client.event
async def on_ready():
	print(f"{client.user} has connected to Discord!")

index = Index.open("index.json")
with open("secret/token.txt") as f:
	token = f.read().strip()
client.run(token)
