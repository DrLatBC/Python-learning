import random
import math
import questionary
from questionary import Choice
from messages import MESSAGES, STUPID_NICKNAMES
import os

MAIN_MENU = [
     Choice("[1] Buy worker", value = "buy_workers"),
     Choice("[2] Skip turn", value = "skip"),
     Choice("[3] View Details", value = "details"),
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
    def get_stats(self):
        total_income = 0
        total_workers = 0
        for worker in self.workers.values():
            total_income += worker["count"] * worker["income"]
            total_workers += worker["count"]
        return {
            "income": total_income,
            "workers": total_workers,
            "money": self.money,
            "turn": self.turn
        }
    def tick(self, income, turns_used):
        self.money += income * turns_used
        self.turn += turns_used
    def add_worker(self, buy_amount, worker_type):
        worker = self.workers[worker_type]
        total_cost = worker["cost"] * buy_amount
        if total_cost > self.money:
            say_line("too_poor")
            get_input("Press enter to cotinue...", allow_default = "")
            return
        worker["count"] += buy_amount
        self.money -= total_cost
        get_input("Press enter to continue...", allow_default = "")
    
def display_game_status(game_state: Gamestate, verbose = False):
    stats = game_state.get_stats()
    income = stats["income"]
    total_workers = stats["workers"]
    turn = stats["turn"]
    money = stats["money"]
    if verbose:
        max_name_len = max(len(f"{name}:") for name in game_state.workers)
        col_width = max_name_len + 1
        table_width = 55
        header = "=== Worker Breakdown ==="
        print(header.center(table_width))
        print("-" * 55)
        for name, data in game_state.workers.items():
            label = f"{name}:"
            print(f"| {label:<{max_name_len}} {data['count']:<8,} | Income Per: {data['income']:<8,} |")
        print("-" * 55)
        print(f"| {'Total workers:':<{col_width}} {total_workers:<15,} {'':<15}|")
        print(f"| {'Total income:':<{col_width}} {income:<15,} {'':<15}|")
        print(f"| {'Turn:':<{col_width}} {turn:<15,} {'':<15}|")
        print(f"| {'Bank:':<{col_width}} {money:<15,} {'':<15}|")
        print("-" * 55)
    else:
        print(f"$: {money}, Turn: {turn} Income: {income}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def ask_action(prompt, menu_options = MAIN_MENU):
    result = questionary.select(
          prompt,
          choices = menu_options
     ).ask()
    return result


game = Gamestate()

while True:
    clear_screen()
    display_game_status(game_state=game, verbose=False)
    action = ask_action("What now?", MAIN_MENU)
    if action == "buy_workers":
        clear_screen()
        worker_type = ask_action(f"Who do you want to hire? You have $: {game.money}", BUY_MENU)
        amount = get_input("How many?: ", low=1, number_expected=True)
        game.add_worker(amount, worker_type)

    elif action == "skip":
        clear_screen()
        skip_amount = get_input("How many turns to skip?: ", low = 1, number_expected = True)
        stats = game.get_stats()
        game.tick(stats["income"], skip_amount)

    elif action == "details":
        clear_screen()
        display_game_status(game_state=game, verbose=True)
        get_input("Press enter to return...", allow_default = "")


    elif action == "quit":
        say_line("goodbye")
        break

