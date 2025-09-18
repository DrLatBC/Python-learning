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
GOODBYE = [
    "I didn't want to play with you anyways, {nick}",
    "Some say this is the only way to win",
    "You weren't going to win anyways, {nick}.",
    "This is why no one will remember your name, {nick}"
]
INSULTS = {
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
        "Not sure what that means, {nick}. Try typing a number or one of the listed options."
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


    ]
}

insult_ix = {reason: 0 for reason in INSULTS}

def burn(reason, **ctx):
    i = insult_ix[reason] % len(INSULTS[reason])
    template = INSULTS[reason][i]
    print(template.format(nick=random.choice(STUPID_NICKNAMES), **ctx))
    insult_ix[reason] += 1

def diff(secret,guess):
    return abs(secret - guess)

def high_low(secret, guess):
    if guess > secret:
       return "high"
    elif guess < secret:
        return "low"
    return "correct!"

def get_int(prompt, low = 1, high = None, allow_default = False, allow_preset = False, number_expected = False):
    while True:
            raw = input(prompt)
            choice = raw.strip().lower()
            if allow_preset:
                preset = DIFFICULTY_ALIASES.get(choice)
                if preset is not None:
                    return preset
            if choice == "" and allow_default is not False: 
                return allow_default
            try:
                value = int(choice)
            except ValueError:
                if number_expected:
                     burn("unknown_option_helpful")
                else:
                     burn("unknown_option_insult")
                continue
            if value < low: 
                 burn("range_low")
                 continue
            if high is not None and value > high:
                 burn("range_high")
                 continue
            return value



play_again  = True

while play_again:

    difficulty_choice = get_int("Pick difficulty (easy/medium/hard/custom): ", allow_preset = True)
    if difficulty_choice in DIFFICULTY_SETTINGS:
        preset = DIFFICULTY_SETTINGS[difficulty_choice]
        original_lives = preset["lives"]
        difficulty_choice = preset["max"]
    elif difficulty_choice == "custom":
         difficulty_choice = get_int("Custom it is, {nick}. What do you want for a max number?: ".format(nick=random.choice(STUPID_NICKNAMES)), number_expected = True)
    else:
        suggested = math.ceil(math.log2(difficulty_choice))
        original_lives = get_int(f"How many lives do you want? (Press enter for suggested default: {suggested}): ", allow_default = suggested, number_expected = True)
    lives = original_lives
    print(f"Ok, it's between 1 and {difficulty_choice} and you have {lives} lives, so go fucking nuts.")
    guess = get_int("What is your guess?: ", high = difficulty_choice, number_expected = True)
    secret = random.randint(1, difficulty_choice)
    tries = 1
    guess_history = []

    while guess != secret and lives > 0:
        delta = diff(secret, guess)
        direction = high_low(secret, guess)
        ratio = delta / float(difficulty_choice)
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
        guess = get_int("What is your guess?: ", high = difficulty_choice, number_expected = True)
        tries += 1
    delta = diff(secret, guess)
    direction = high_low(secret, guess)
    ratio = delta / float(difficulty_choice)
    for cutoff, label in heat_levels:
        if ratio <= cutoff:
                hot_cold = label
                break
        
    guess_history.append({"try": tries, "guess": guess, "high/low": direction, "hot/cold": hot_cold})
    if lives == 0:
        burn("game_over", secret=secret) 
    elif tries == 1:
            print("You got it in 1 try!")
    else:
            print(f"You got it after {tries} tries, you fucking dunce.")
    history = (input("Do you want to see your guess history? ")).strip().lower()
    history_input = RESPONSES.get(history, False)
    if history_input == True:
        print()
        print(f"Max number was set at: {difficulty_choice}.")
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