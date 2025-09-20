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
    Choice("[1] Child labor. Income: 10", value = "children"),
    Choice("[2] Little guys. Income: 20", value = "little_guys"),
    Choice("[3] Full sized adults. Income: 30", value = "full_adults"),
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
          self.money = 0
          self.turn = 0
          self.workers = {
               "intern": {"count": 0, "income": 1, "cost": 10},
               "Junior Dev": {"count": 0, "income": 1, "cost": 10},
               "Middle Manager": {"count": 0, "income": 1, "cost": 10},
               "Agile Coach": {"count": 0, "income": 1, "cost": 10},
               "Automated Slackbot": {"count": 0, "income": 1, "cost": 10},
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
            say_line("too_broke")
            return
        worker["count"] += buy_amount
        self.money -= total_cost
                      

def ask_action(prompt, menu_options = MAIN_MENU):
    result = questionary.select(
          prompt,
          choices = menu_options
     ).ask()
    return result






play_again  = True
while play_again:
    print(f"Day: {state['turn']} | $: {state['money']} | Workers: {state['workers']} | Income: {state['income']}")
    action = ask_action("Choose", MAIN_MENU)
    handler= HANDLERS[action]
    state, reason = handler(state)
    if reason == "quit":
        break
say_line("goodbye")




