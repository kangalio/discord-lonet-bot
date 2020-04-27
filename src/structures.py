from typing import *
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Task:
	name: str
	description: str
	deadline: Optional[datetime]
	link: str

@dataclass
class Lernplan:
	themen: Dict[str, List[Task]] # map Themaname to a list of tasks
