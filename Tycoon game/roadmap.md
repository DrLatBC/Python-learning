
FEATURES.md – Clean Roadmap & Progress Tracker

---

#### 🧱 Core Systems (Start Here)

* [x] Basic turn-based game loop
* [x] Worker types with count, income, and cost
* [x] Income generation system
* [x] Purchase logic with affordability checks
* [x] Turn skipping with passive income
* [x] Clean terminal display and UI feedback
* [x] Menu navigation via `questionary`
* [x] `get_input()` function for safe user input
* [x] Context-aware message system (`say_line`)

---

#### 📊 Display & Stats

* [x] `display_small()` – money, turn, income
* [x] `display_detailed()` – worker breakdown
* [ ] UI polish for all screens
* [ ] View stats from main menu
* [ ] Achievement screen (locked/unlocked)

---

#### 💾 Persistence

* [ ] Save/load system with `.json`
* [ ] Auto-save every X turns
* [ ] Manual save from main menu

---

#### 📈 Scaling & Upgrades

* [ ] Cost scaling (e.g., exponential or curve-based)
* [ ] Worker upgrades (faster, better income)
* [ ] Item upgrades (multiplier bonuses)
* [ ] Passive income multipliers (office bonuses, items)
* [ ] Display passive income multipliers
* [ ] Office expansions (unlock more worker slots)
* [ ] Prestige system (resets with bonuses)

---

#### 🕹️ Gameplay Features

* [ ] Achievements
* [ ] Random events (good/bad, resource changes)
* [ ] Player choices (branching effects, moral dilemmas)
* [ ] Daily/weekly bonuses

---

#### ⚙️ Passive Features

* [ ] Idle-style passive tick system
* [ ] Offline progress simulation (optional)
* [ ] Background loop with threading/timers

---

#### 🎁 Flavor & Polish

* [ ] Nickname generator (full list polish)
* [ ] Message variety per event type
* [ ] Unlockable worker types
* [ ] Sound/ASCII effects (optional)
* [ ] Future plans: GUI wrapper (tkinter, PySimpleGUI?)
