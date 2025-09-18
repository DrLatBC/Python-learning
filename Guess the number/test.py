import random
import math

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

DIFFICULTY_SETTINGS = {
    "easy": {"lives": 20, "max": 3000},
    "medium": {"lives": 15, "max": 5000},
    "hard": {"lives": 10, "max": 10000}

}
heat_levels = [
    (0.01, "Scorching"),
    (0.03, "Hot"),
    (0.10, "Warm"),
    (0.15, "Cold"),
    (0.20, "Freezing"),
    (1.00, "Arctic"),
]
performance_levels = [
    (0.2, "mythic"),
    (0.5, "clean"),
    (0.75, "solid"),
    (1.0, "messy"),
    (float("inf"), "clown"),
]

GOODBYE = [
    "I didn't want to play with you anyways, {nick}",
    "Some say this is the only way to win",
    "You weren't going to win anyways, {nick}.",
    "This is why no one will remember your name, {nick}"
]
MESSAGES = {
    "range_high": [
        "Nah, {nick}, you're trying to guess the moon",
        "Aim lower, {nick}, this ain't limbo.",
        "Your brain rot is winning, too high.",
        "You're having a laugh, {nick}.",
        "Relax, {nick}, we’re not counting stars.",
        "Too high, {nick}. This isn’t the stock market.",
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
        "You lose, {nick}. It’s {secret}—and you still couldn’t find it.",
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
        "That’s a textbook clear, {nick}. Nothing flashy, nothing sloppy.",
    ],
    "messy": [
        "Messy, {nick}, but hey—you still got there.",
        "Like watching someone parallel park for five minutes, {nick}.",
        "Not pretty, {nick}. A win’s a win, though.",
    ],
    "clown": [
        "Embarrassing, {nick}. Pure clown show.",
        "Bro, {nick}, I lost brain cells watching that.",
        "Send in the circus music, {nick}. You’re the act.",
    ]
}



message_ix = {reason: 0 for reason in MESSAGES}

def say_line(reason, **ctx):
    i = message_ix[reason] % len(MESSAGES[reason])
    template = MESSAGES[reason][i]
    print(template.format(nick=random.choice(STUPID_NICKNAMES), **ctx))
    message_ix[reason] += 1

def diff(secret,guess):
    return abs(secret - guess)

def high_low(secret, guess):
    if guess > secret:
       return "high"
    elif guess < secret:
        return "low"
    return "correct!"

def get_int(prompt, low = 1, high = None, allow_default = None, allow_preset = False, number_expected = False):
    while True:
            raw = input(prompt)
            choice = raw.strip().lower()
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



play_again  = True

while play_again:

    max_num = get_int("Pick difficulty (easy/medium/hard/custom): ", allow_preset = True)
    if max_num in DIFFICULTY_SETTINGS:
        preset = DIFFICULTY_SETTINGS[max_num]
        original_lives = preset["lives"]
        max_num = preset["max"]
        suggested = math.ceil(math.log2(max_num))
    else:
        if max_num == "custom":
            max_num = get_int("Custom it is, {nick}. What do you want for a max number?: ".format(nick=random.choice(STUPID_NICKNAMES)), number_expected = True)
        suggested = math.ceil(math.log2(max_num))
        original_lives = get_int(f"How many lives do you want? (Press enter for suggested default: {suggested}): ", allow_default = suggested, number_expected = True)

    lives = original_lives
    secret = random.randint(1, max_num)
    print(f"Ok, it's between 1 and {max_num} and you have {lives} lives, so go fucking nuts.")
    guess = get_int("What is your guess?: ", high = max_num, number_expected = True)
    tries = 1
    guess_history = []

    while guess != secret and lives > 0:
        delta = diff(secret, guess)
        direction = high_low(secret, guess)
        ratio = delta / float(max_num)
        for cutoff, label in heat_levels:
            if ratio <= cutoff:
                hot_cold = label
                break

        if direction == "high":
            high_low_msg = f"too high, {random.choice(STUPID_NICKNAMES)}"
        elif direction == "low":
            high_low_msg = f"too low, {random.choice(STUPID_NICKNAMES)}"
        else:
            high_low_msg = ""

        hot_cold_msg = hot_cold + "..."
        msg = f"{hot_cold_msg} {high_low_msg}".strip()
        unit = "life" if lives == 1 else "lives"
        print(f"{msg}. | Lives: {lives} → {lives-1}")
        lives -= 1
        if lives == 0:
            break
        guess_history.append({"try": tries, "guess": guess, "high/low": direction, "hot/cold": hot_cold})
        guess = get_int("What is your guess?: ", high = max_num, number_expected = True)
        tries += 1
    delta = diff(secret, guess)
    direction = high_low(secret, guess)
    ratio = delta / float(max_num)
    for cutoff, label in heat_levels:
        if ratio <= cutoff:
                hot_cold = label
                break
        
    guess_history.append({"try": tries, "guess": guess, "high/low": direction, "hot/cold": hot_cold})

    if lives == 0:
        say_line("game_over", secret=secret) 
    elif tries == 1 and max_num > 50:
            print("You got it in 1 try! That's fucking amazing!")
    elif tries == 2 and max_num > 50:
            print("Not quite a hole in 1, but gahd DAMN.")
    else:
        perf_ratio = tries / suggested
        for cutoff, label in performance_levels:
             if perf_ratio <= cutoff:
                  verdict = label
                  break
        print(f"You got it in {tries} tries.")
        say_line(verdict)
         
    
    history = (input("Do you want to see your guess history? ")).strip().lower()
    history_input = RESPONSES.get(history, False)
    if history_input == True:
        print()
        print(f"Max number was set at: {max_num}.")
        print(f"Max lives was set to: {original_lives}")
        for e in guess_history:
            print(f"Attempt #{e['try']:>2} | Guess: {e['guess']:>6} | HL: {e['high/low']:>5} | Hot/Cold:  {e['hot/cold']:>4}")
    
    else:
        continue
    raw = (input("Play again? (y/n:) "))
    clean = raw.strip().lower()
    play_again = RESPONSES.get(clean, False)

if play_again == False:
    template = random.choice(GOODBYE) + "."
    print(template.format(nick=random.choice(STUPID_NICKNAMES)))