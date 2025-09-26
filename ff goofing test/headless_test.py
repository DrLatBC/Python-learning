from playwright.sync_api import sync_playwright

EMAIL = "drlatbc@gmail.com"
PASSWORD = "@Tp3.1415"

def login_and_grab_csv():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # invisible browser
        page = browser.new_page()

        # Go to login page
        page.goto("https://stathead.com/users/login.cgi", wait_until="networkidle")

        # Fill login form
        page.fill('input[name="username"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)

        # Submit form
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Stats page
        page.goto("https://stathead.com/football/player-game-finder.cgi?request=1&match=player_game&order_by=pass_rating&year_min=2025&year_max=2025&week_num_season_min=1&week_num_season_max=1&ccomp%5B2%5D=gt&cval%5B2%5D=1&cstat%5B2%5D=pass_att")
        page.wait_for_load_state("networkidle")
        
        #Get CSV Table on screen
        page.hover("text=Export Data")
        page.click("text=Get table as CSV")

        csv_text = page.inner_text("pre#csv_stats")
        with open("week1.csv", "w", encoding="utf-8") as f:
            f.write(csv_text)
    

        browser.close()

if __name__ == "__main__":
    login_and_grab_csv()
