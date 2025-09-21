import random
import math
import questionary
from questionary import Choice
from messages import MESSAGES, STUPID_NICKNAMES

MAIN_MENU = [
     Choice("[1] Buy worker", value = "buy_workers"),
     Choice("[2] Skip turn", value = "skip"),
     Choice("Quit", value = "quit")
]
BUY_MENU = [
    Choice("[1] Intern. Income: 10 | Cost: 10", value = "Intern"),
    Choice("[2] Junior Dev. Income: 20 | Cost: 20", value = "Junior Dev"),
    Choice("[3] Middle Manager. Income: 30 | Cost: 30", value = "Middle Manager"),
    Choice("[4] Agile Coach. Income: 40 | Cost = 40", value = "Agile Coach"),
    Choice("[5] Automated Slackbot. Income: 50 | Cost = 50", value = "Automated Slackbot"),
]

RESPONSES = {
    "yes": True,
    "y": True,
    "sure": True,
    "yup": True,
    "1": True,
    "no": False,
    "nope": False,
    "naw": False,
    "2": False,
    "n": False,
}

DIFFICULTY_ALIASES = {
    "easy": "easy",
    "e": "easy",
    "medium": "medium",
    "m": "medium",
    "hard": "hard",
    "h": "hard",
    "custom": "custom",
    "c": "custom",
}


message_ix = {reason: 0 for reason in MESSAGES}

def say_line(reason, **ctx):
    i = message_ix[reason] % len(MESSAGES[reason])
    template = MESSAGES[reason][i]
    print(template.format(nick=random.choice(STUPID_NICKNAMES), **ctx))
    message_ix[reason] += 1

def get_input(prompt, low = 1, high = None, allow_default = None, allow_preset = False, number_expected = False):
    while True:
            raw = input(prompt)
            choice = raw.strip().replace(",", "").replace("_", "").lower()
            if allow_preset:
                preset = DIFFICULTY_ALIASES.get(choice)
                if preset is not None:
                    return preset
            if choice == "" and allow_default is not None: 
                return allow_default
            try:
                value = int(choice)
            except ValueError:
                if number_expected:
                     say_line("unknown_option_insult")
                else:
                     say_line("unknown_option_helpful")
                continue
            if value < low: 
                 say_line("range_low")
                 continue
            if high is not None and value > high:
                 say_line("range_high")
                 continue
            return value
class Gamestate:
    def __init__(self):
          self.money = 10
          self.turn = 0
          self.workers = {
               "Intern": {"count": 0, "income": 10, "cost": 10},
               "Junior Dev": {"count": 0, "income": 20, "cost": 20},
               "Middle Manager": {"count": 0, "income": 30, "cost": 30},
               "Agile Coach": {"count": 0, "income": 40, "cost": 40},
               "Automated Slackbot": {"count": 0, "income": 50, "cost": 50},
          }
    def get_total_income(self):
        income = 0
        for worker in self.workers.values():
             income += worker["count"] * worker["income"]
        return income
    
    def tick(self, income, turns_used):
        self.money += income * turns_used
        self.turn += turns_used
        
    def display (self):
         print(f"$: {self.money}, Turn: {self.turn} Income: {self.get_total_income()}")

    def add_worker(self, buy_amount, worker_type):
        worker = self.workers[worker_type]
        total_cost = worker["cost"] * buy_amount
        if total_cost > self.money:
            say_line("too_poor")
            return
        worker["count"] += buy_amount
        self.money -= total_cost
                      

def ask_action(prompt, menu_options = MAIN_MENU):
    result = questionary.select(
          prompt,
          choices = menu_options
     ).ask()
    return result


game = Gamestate()

while True:
    game.display()
    action = ask_action("What now?", MAIN_MENU)
    if action == "buy_workers":
        worker_type = ask_action("Who do you want to hire?", BUY_MENU)
        amount = get_input("How many?: ", low=1, number_expected=True)
        game.add_worker(amount, worker_type)

    elif action == "skip":
        skip_amount = get_input("How many turns to skip?: ", low = 1, number_expected = True)
        game.tick(game.get_total_income(), skip_amount)

    elif action == "quit":
        say_line("goodbye")
        break

