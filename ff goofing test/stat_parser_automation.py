import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://stathead.com/users/login.cgi"

# Example: week 1 passing stats
RESULTS_URL = ("https://stathead.com/football/player-game-finder.cgi?request=1&match=player_game&order_by=pass_rating&year_min=2025&year_max=2025&week_num_season_min=1&week_num_season_max=1&ccomp%5B2%5D=gt&cval%5B2%5D=1&cstat%5B2%5D=pass_att"
)

EMAIL = ""
PASSWORD = ""

session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Step 1: Load login page
resp = session.get(LOGIN_URL, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

# Step 2: Extract CSRF token
token_input = soup.find("input", {"name": "csrf_token"})
csrf_token = token_input["value"] if token_input else None
if not csrf_token:
    raise RuntimeError("Could not find CSRF token on login page.")

# Step 3: Login with CSRF token
payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "csrf_token": csrf_token,
}
resp = session.post(LOGIN_URL, data=payload, headers=headers)

if "Logout" not in resp.text:
    raise RuntimeError("Login failed — check email/password.")

print("✅ Logged in")

# Step 4: Fetch results page
resp = session.get(RESULTS_URL, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

# Step 5: Scrape CSV block
csv_block = soup.find("pre", id="csv_stats")

if not csv_block:
    print("❌ CSV block not found — page might still be in table mode")
    print(resp.text[:500])  # for debugging
else:
    csv_text = csv_block.get_text()
    with open("week1_passing.csv", "w", encoding="utf-8") as f:
        f.write(csv_text)
    print("✅ CSV saved: week1_passing.csv")
