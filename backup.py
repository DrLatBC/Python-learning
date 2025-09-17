import random

INSULTS = {
    "bad_range": [
        "Nah, my dude, lock the fuck in.",
        "You fucking with me or naw?",
        "....No.",
        "You're having a laugh, bruv.",
    ],
    "not_number": [
    "That's not even a number, you fuck.",
    "Are you typing with your elbows?",
    "Fuck off.",

    ]
}

insult_ix = {reason: 0 for reason in INSULTS}

def burn(reason):
    i = insult_ix[reason] % len(INSULTS[reason])
    print(INSULTS[reason][i])
    insult_ix[reason] += 1

def diff(secret,guess,difficult):
    delta = abs(secret - guess)
    ratio = delta / difficult

    if guess < 1 or guess > difficult:
        print("What the fuck are we doing here my boy?")
        return None
    elif ratio <= 0.01: 
        print("Scorching")
    elif ratio <= 0.03:
        print("Hot")
    elif ratio <= 0.10:
        print("Warm")
    elif ratio <= 0.20:
        print("Cold")
    else:
        print("Arctic, bro")
    return secret - guess
def high_low(secret, guess):
    if guess > secret:
        print("Too high, dawg")
    elif guess < secret:
        print("Too low, dawg")

def get_guess():
    while True:
        try:
            value = int(input("What is your guess?: "))
            if value <= 1:
                burn("bad_range")
                continue
            return value
        except ValueError:
            burn("not_number")
def get_difficult():
    while True:
        try: 
            value = int(input("How high do you want this go?: "))
            if value <= 1:
                burn("bad_range")
                continue    
            return value
        except ValueError:
            burn("not_number")

play_again  = True

while play_again == True:

    difficult = get_difficult()
    secret = random.randint(1, difficult)
    print("Ok, it's between 1 and " + str(difficult) + ", so go fucking nuts.")
    guess = get_guess()
    tries = 1

    while guess != secret:
        result = diff(secret, guess, difficult)
        if result is not None:
            high_low(secret,guess)
        guess = get_guess()
        tries += 1
    if tries == 1: 
        print("You got it in 1 try!")
    else:
        print("You got it after " + str(tries) + " tries, you fucking dunce.")

    play_again = (input("Play again? (y/n:) ") == "y")




