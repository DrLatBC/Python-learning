import random
import math
import questionary
from questionary import Choice

MAIN_MENU = [
     Choice("[1] Buy worker", value = "buy_workers"),
     Choice("[2] Skip turn", value = "skip"),
     Choice("Quit", value = "quit")
]

STUPID_NICKNAMES = [
    "bro",
    "dawg",
    "homie",
    "big dawg",
    "doogan",
    "broganheimer",
    "dude",
    "dudeski",
    "bro beans",
    "playa",
    "foo",
    "mashed brotato",
    "bruv",
    "pal",
    "buddy",
    "guy",


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
MESSAGES = {
    "goodbye": [
        "I didn't want to play with you anyways, {nick}",
        "Some say this is the only way to win",
        "You weren't going to win anyways, {nick}.",
        "This is why no one will remember your name, {nick}"
    ],
    "range_high": [
        "Nah, {nick}, you're trying to guess the moon",
        "Aim lower, {nick}, this ain't limbo.",
        "Your brain rot is winning, too high.",
        "You're having a laugh, {nick}.",
        "Relax, {nick}, we're not counting stars.",
        "Too high, {nick}. This isn't the stock market.",
    ],
    "range_low": [
        "We don't do negatives here, {nick}.",
        "It has to be higher than 1, {nick}.",
        "You're an idiot, no negatives.",
        "Stop being dumb",
        "Can't even count to zero, sad",
        "A positive and a negative walk into a bar. The bartender says...we don't serve negatives here.",
    ],
    "unknown_option_insult": [
        "That's not even a number, {nick}.",
        "Are you typing with your elbows?",
        "Fuck off.",
        "Invalid input. Pretend you can read and try again.",
    ],
    "unknown_option_helpful": [
        "I don't know what that means, {nick}. Why don't you try again?",
        "Try using one of the options above!",
        "Not sure what that means, {nick}. Try typing a number or one of the listed options.",
        "That ain't valid, {nick}. Pick a difficulty or drop a number instead."
    ],
    "game_over": [
        "Game over, {nick}. Number was {secret}.. what's so hard about that?",
        "Your goose is cooked, {nick}. Should have guessed {secret}",
        "Pack it up. It was {secret}, why not just guess that on the first try, {nick}?",
        "Skill issue. Obviously it was {secret}, {nick}.",
        "Get fucked, {nick}. It was {secret} the whole time",
        "Out of lives, {nick}. The number {secret} was laughing at you the whole time.",
        "You lose, {nick}. It's {secret}—and you still couldn't find it.",
    ],
    "mythic": [
        "Legendary run, {nick}. You cracked the code like a god.",
        "That was cleaner than a world-record speedrun, {nick}.",
        "Peak gamer instincts. Mythic tier achieved, {nick}.",
    ],
    "clean": [
        "Sharp guessing, {nick}. Almost pro tier.",
        "No wasted moves, {nick}. That was smooth as hell.",
        "You made that look easy, {nick}. Clean run.",
    ],
    "solid": [
        "Respectable work, {nick}. You held it together.",
        "Not perfect, but solid enough, {nick}.",
        "That's a textbook clear, {nick}. Nothing flashy, nothing sloppy.",
    ],
    "messy": [
        "Messy, {nick}, but hey—you still got there.",
        "Like watching someone parallel park for five minutes, {nick}.",
        "Not pretty, {nick}. A win's a win, though.",
    ],
    "clown": [
        "Embarrassing, {nick}. Pure clown show.",
        "Bro, {nick}, I lost brain cells watching that.",
        "Send in the circus music, {nick}. You're the act.",
    ],
    "too_poor": [
    "You're broke as hell, {nick}. Come back with some cash.",
    "Not enough money, {nick}. This isn't a charity.",
    "Keep dreaming, {nick}—your wallet's empty.",
    "You can't afford that, {nick}. Maybe try begging?",
]
}
state = {
     "money": 10,
     "income": 0,
     "workers": 0,
     "turn": 0,
}


message_ix = {reason: 0 for reason in MESSAGES}

def say_line(reason, **ctx):
    i = message_ix[reason] % len(MESSAGES[reason])
    template = MESSAGES[reason][i]
    print(template.format(nick=random.choice(STUPID_NICKNAMES), **ctx))
    message_ix[reason] += 1

def get_int(prompt, low = 1, high = None, allow_default = None, allow_preset = False, number_expected = False):
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
def tick(state, tick_amount = 1):
     temp_income = ((state["income"]) * tick_amount)
     state["money"] = state["money"] + temp_income
     state["turn"] = state["turn"] + tick_amount
     return state

def ask_action(prompt, menu_options = MAIN_MENU):
     result = questionary.select(
          prompt,
          choices = menu_options
     ).ask()
     return result
def handle_buy_workers(state, worker_buy_amount = 1, worker_buy_cost = 10, worker_income_amount = 10):
     worker_total_cost = worker_buy_amount * worker_buy_cost
     if state["money"] >= worker_total_cost:
          state["workers"] = state["workers"] + worker_buy_amount
          state["money"] = state["money"] - worker_total_cost
          state["income"] = state["income"] + (worker_buy_amount* worker_income_amount)
          return (state, "ok")
     else:
          say_line("too_poor")
          return (state, "too poor")
     
def handle_skip(state):
     skip_time = get_int("How many days do you want to skip?: ")
     state = tick(state, tick_amount = skip_time)
     return (state, "Time passes")
def print_status(state):
     print(f"Day: {state['turn']} | $: {state['money']} | Workers: {state['workers']} | Income: {state['income']}")
def handle_quit(state):
    play_again = False
    return (state, "quit")
HANDLERS = {
    "buy_workers": handle_buy_workers,
    "skip": handle_skip,
    "quit": handle_quit,
}



play_again  = True
while play_again:
    print(f"Day: {state['turn']} | $: {state['money']} | Workers: {state['workers']} | Income: {state['income']}")
    action = ask_action("Choose", MAIN_MENU)
    handler= HANDLERS[action]
    state, reason = handler(state)
    if reason == "quit":
        break
say_line("goodbye")




