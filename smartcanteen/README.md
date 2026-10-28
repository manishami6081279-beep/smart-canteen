# Smart Canteen Preorder System — Django + MySQL

Your existing HTML/CSS/JS/images, now running on a Django backend with a MySQL database.

---

## 1. What is where?

```
smartcanteen/                  <- project folder (open this in VS Code)
├── manage.py                  <- Django's command tool (you run commands with it)
├── requirements.txt           <- Python packages to install
├── .env.example               <- copy to ".env" and put your DB password there
├── smartcanteen/              <- project settings
│   ├── settings.py            <- MySQL connection, static files, login settings
│   └── urls.py                <- main URL table
├── canteen/                   <- the application (all the logic)
│   ├── models.py              <- database tables
│   ├── views.py               <- what happens on each page
│   ├── forms.py               <- validation rules
│   ├── urls.py                <- page addresses (/menu/, /login/ ...)
│   ├── admin.py               <- admin site setup
│   ├── tests.py               <- 36 automated tests
│   └── management/commands/seed_menu.py  <- loads your food items into MySQL
├── templates/canteen/         <- your HTML pages, turned into Django templates
├── static/
│   ├── css/                   <- your original CSS files (+ canteen.css, small additions)
│   ├── js/                    <- canteen.js (qty buttons + cart), contact.js
│   └── images/                <- your food images
└── media/                     <- food images used by the database (filled by seed_menu)
```

### Where did each original file go?

| Original file | Now |
|---|---|
| `homepage.html` | `templates/canteen/homepage.html` → URL `/` |
| `canreg.html` | `templates/canteen/canreg.html` → `/register/` |
| `canteenlogin.html` | `templates/canteen/canteenlogin.html` → `/login/` |
| `menu.html` | `templates/canteen/menu.html` → `/menu/` |
| `breakefast.html` | `breakefast.html` → `/breakfast/` |
| `LUNCH.HTML` | `lunch.html` → `/lunch/` (lower-case, so it also works on Linux) |
| `snacks.html`, `beverages.html`, `dessert.html` | same names → `/snacks/`, `/beverages/`, `/desserts/` |
| `todayspecial.html` | same name → `/todays-special/` |
| `placeorder.html` | same name → `/place-order/` |
| `token.html` | same name → `/token/` |
| `feedback.html`, `contact.html`, `about.html` | same names → `/feedback/`, `/contact/`, `/about/` |
| `*.css` | `static/css/` (unchanged, except 2 tiny edits below) |
| `*.png` | `static/images/` (2 files renamed: `veg roll.png` → `veg_roll.png`, `samosa (2).png` → `samosa.png`) |
| `canteennav.html` | not used (it was an unused stub linking to a non-existing `home.html`) |

---

## 2. Install the prerequisites (once)

1. **Python 3.10 or newer** — https://www.python.org/downloads/ (Windows: tick *"Add Python to PATH"*).
2. **MySQL Server 8.x** — https://dev.mysql.com/downloads/installer/ (remember the `root` password you set).

Check:

```bash
python --version
mysql --version
```

---

## 3. Create the MySQL database

Open a MySQL prompt (`mysql -u root -p`) and run:

```sql
CREATE DATABASE smart_canteen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'canteen_user'@'localhost' IDENTIFIED BY 'CHOOSE_A_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON smart_canteen_db.* TO 'canteen_user'@'localhost';
GRANT ALL PRIVILEGES ON `test\_smart\_canteen\_db`.* TO 'canteen_user'@'localhost';  -- only needed to run the tests
FLUSH PRIVILEGES;
EXIT;
```

(`utf8mb4` lets the database store the ₹ symbol and emojis safely.)
Using a separate `canteen_user` is safer than using `root` inside your project.

---

## 4. Set up Python

Open a terminal **inside the `smartcanteen` folder** and run:

```bash
# create a private Python environment
python -m venv venv

# activate it
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# install the packages
pip install -r requirements.txt
```

`requirements.txt` installs **Django**, **mysqlclient** (the MySQL driver), **Pillow** (needed for image fields) and **python-dotenv** (reads your `.env` file).

> **`mysqlclient` fails to install?** (common on Windows/macOS)
> Open `requirements.txt`, delete the `mysqlclient` line, add `PyMySQL>=1.1`, and run `pip install -r requirements.txt` again. The project detects it automatically (see `smartcanteen/__init__.py`) — nothing else to change.
> On Ubuntu/Debian: `sudo apt install pkg-config libmysqlclient-dev build-essential python3-dev` first.

---

## 5. Give Django the database password (never hard-code it)

Copy `.env.example` to `.env`:

```bash
copy .env.example .env         # Windows
cp .env.example .env           # macOS / Linux
```

Open `.env` and fill in your values:

```
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=any-long-random-text
DB_NAME=smart_canteen_db
DB_USER=canteen_user
DB_PASSWORD=the_password_you_chose_in_step_3
DB_HOST=127.0.0.1
DB_PORT=3306
```

`settings.py` reads these with `os.environ.get(...)`, so no password is written in the code. `.env` is listed in `.gitignore`, so it won't be uploaded to GitHub.

The database block in `smartcanteen/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "smart_canteen_db"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
```

---

## 6. Create the tables and load the menu

```bash
python manage.py migrate          # creates all tables in MySQL
python manage.py seed_menu        # inserts your 40 food items (+ copies their images)
python manage.py createsuperuser  # your admin login for /admin/
```

(The migration files are already included in `canteen/migrations/`, so you do **not** need `makemigrations`. You only need it if you later change `models.py`:
`python manage.py makemigrations` then `python manage.py migrate`.)

### Verify the database connection

```bash
python manage.py check --database default
python manage.py showmigrations canteen
python manage.py dbshell          # opens a MySQL prompt on smart_canteen_db
```

Inside `dbshell` try:

```sql
SHOW TABLES;
SELECT name, category, price FROM canteen_fooditem LIMIT 5;
```

You should see the `canteen_*` tables and your food items. If Django can't connect, it prints `OperationalError (1045 / 2002 ...)` — see *Troubleshooting* below.

---

## 7. Run the website

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ — and the admin site at http://127.0.0.1:8000/admin/.

Typical flow to try: **Register → Login → Menu → Add to cart → Place Order → Token → Feedback**.

---

## 8. How each feature works

### Registration (`/register/`)
1. `canreg.html` now posts to Django (`method="post"` + `{% csrf_token %}`).
2. `RegistrationForm` in `forms.py` validates every field: name (letters only), UID (4–20 letters/digits, **unique**, case-insensitive), mobile (10 digits starting 6–9), year (1–4), department (one of your 7), password (min 6 characters, not too common, must match the confirmation).
3. If valid, two rows are saved **in one transaction**:
   - `auth_user` — Django's user table: `username` = UID, `password` = **hashed** (PBKDF2), never plain text.
   - `canteen_studentprofile` — name, UID, mobile, year, department, `registered_at` (filled automatically).
4. Success → redirect to the login page with a green message. Errors → the form re-appears with red messages under each field and your typed values kept.

> **Why password fields were added:** your original registration form had no password, but login needs one, so *Password* and *Confirm Password* were added.

### Login / logout (`/login/`, `/logout/`)
- The login form now asks for **UID Number + Password** (your original had Username + Email + Password; the UID *is* the username, and e-mail isn't collected at registration, so the Email box was removed so that registration and login stay consistent).
- `authenticate()` checks the hash; `login()` creates a **session** (stored in the `django_session` table, cookie in the browser).
- Wrong details → "Invalid UID number or password." (the same message for both cases, so nobody can discover which UIDs exist).
- Pages `menu`, category pages, today's special, place order, token and feedback use `@login_required`; if you are not logged in you are sent to `/login/?next=...` and returned to the page after logging in.
- Logout is a small POST form (the **LOGOUT** button on the home page, or *Logout* in the top-right corner of other pages).
- Public pages: home, about, contact, register, login.

### Menu pages (database-driven)
- Table `canteen_fooditem`: name, category, veg/non-veg, price, image, **is_available**, is_popular, display order.
- Each page loops over the database rows, e.g. `{% for item in items %}` inside your original `<div style="display:flex;gap:80px">`, so your CSS (which targets that exact markup) still applies.
- Mark an item unavailable in `/admin/` → its card turns grey, shows "Currently unavailable", and it can't be added.
- Change a price in `/admin/` → every page updates immediately. **POPULAR ITEMS** on the home page = items with *is_popular* ticked.
- The home-page **Search** box now works (it opens `/menu/?q=...`).

### Cart (`canteen_cartitem`)
- The `+` / `−` buttons are the same as before (now in `static/js/canteen.js`).
- **Add to cart** sends the item and quantity to `/cart/add/` (using `fetch`, with the CSRF token), which saves it in MySQL **for the logged-in student**. So the cart survives logout, refresh, or switching computers — the old `localStorage` cart did not.
- Like your original page, adding the same item again replaces its quantity.
- The Cart counter in the top-right corner updates immediately. Items can be removed with the ✖ button on the Place Order page.

### Place order → Token
- `/place-order/` shows the cart (read from MySQL) with the total, plus your original fields: name, department, pick-up time, date, payment method. Name and department are pre-filled from the student's profile.
- Server-side checks: date not in the past; time between 8:00 AM and 5:00 PM (the canteen hours from your contact page) and later than now if today; items still available.
- Prices are **always re-read from the database**, never trusted from the browser. Name/price are copied into `canteen_orderitem`, so old orders stay correct if prices change later.
- A token such as **TKN001** is generated (restarts at 1 each day; a database unique rule + retry loop prevents two students getting the same token). The cart is then emptied and you land on the token page. A student can only open their **own** tokens.
- Payment method (Cash/UPI/Card) is only **recorded** — no real online payment is integrated.
- In `/admin/` → *Orders* you can change an order's status (Pending → Preparing → Ready → Completed); students see it on the token page.

### Feedback and Contact
- Feedback (login required) is saved in `canteen_feedback` (rating, taste/quantity/hygiene ticks, comments). The token page's button pre-fills the token number.
- Contact messages (anyone) are saved in `canteen_contactmessage`. Your original JavaScript checks still run first (`static/js/contact.js`).

---

## 9. Everything I changed in your original files

Kept exactly: layouts, colours, fonts, images, class names, CSS files, button text, inline `display:flex` structure.

| Change | Why |
|---|---|
| `href="menu.html"` etc. → `{% url 'menu' %}` | Django page addresses |
| `src="idly.png"` → `{{ item.image.url }}` / `{% static %}` | images come from the database / static folder |
| Hard-coded food cards → `{% for item in items %}` loops | menu comes from MySQL |
| `canreg.html`: added `name=` to every input; first radio (CSE) had no name/value; submit button was *outside* the `<form>`; `type="uid num"` → `text`; `<label="name">` → `<label for="name">`; wrapped radios in `<div class="dept">` (your CSS already had a `.dept` rule for it); added password fields | form could not submit anything before |
| `canteenlogin.html`: removed Email box, UID instead of username; removed the broken `<script>function</script>` | it caused a JavaScript error |
| `todayspecial.html`: removed the broken script at the bottom (`count display=...`) | it was a syntax error; added a *Place Order* button like the other menu pages |
| `breakefast.html` / `menu.html`: fixed `width="170 height="160"` quote | broken attribute |
| `snacks.html`: removed stray `>` after the price | typo |
| `feedback.html`: removed the nested `<form>` and gave inputs names/values | nested forms are invalid HTML |
| `contact.html`: tidied nested `<html>` tags; one form that really posts | your page looked the same but now saves |
| `homepage.html`: tidied the `<nav>` tags that were placed inside `<head>`; same visual order | invalid HTML |
| `placeorder.html` / `token.html`: `localStorage` cart / token counter replaced by server data | localStorage can't be shared or trusted |
| `homepage1.css`: `url(idly.png)` → `url(../images/idly.png)`; `canreg1.css`: password inputs added to the input styles | new folder layout / new fields |
| Spelling in food names: *Sandwitch, Veg Role, Ice Icream, Milk Shacke* → *Sandwich, Veg Roll, Ice Cream, Milk Shake*; *syatem/strudents* in About | typos — to revert, edit the item in `/admin/` |
| **Kothu Parotta** had no price in your page → set to **₹80** | please change in `/admin/` if wrong |

New small things (don't affect your designs): a little top-right bar (Home / Cart / Logout) on inner pages, green/red message banners, `static/css/canteen.css`.

---

## 10. Managing the canteen (admin site)

Go to `/admin/` and log in with the superuser. You can add/edit foods (upload a new photo, set price, tick *available*), see students, orders, feedback and contact messages.

To add a **new food**: Admin → Food items → Add. Choose a category (use **Today's Special** for the special page; for **Lunch** also choose *Veg* or *Non-Veg*).

---

## 11. Run the automated tests (optional)

```bash
python manage.py test canteen
```
This creates a temporary `test_smart_canteen_db` (that is why step 3 grants that permission), runs 36 tests (registration, duplicate UID, login, protected pages, cart, orders, tokens, feedback, contact) and removes it.

---

## 12. Troubleshooting

| Message | Fix |
|---|---|
| `Access denied for user ... (1045)` | wrong `DB_USER` / `DB_PASSWORD` in `.env` |
| `Unknown database 'smart_canteen_db' (1049)` | run the `CREATE DATABASE` command in step 3 |
| `Can't connect to MySQL server (2002 / 2003)` | MySQL service isn't running; check `DB_HOST` / `DB_PORT` |
| `Error loading MySQLdb module` / `mysqlclient` build error | see the note in step 4 (use PyMySQL) |
| `ModuleNotFoundError: No module named 'PIL'` | `pip install Pillow` (is the venv activated?) |
| `django.db.utils.OperationalError: ... caching_sha2_password` with PyMySQL | `pip install cryptography` |
| Pages open but food images are missing | run `python manage.py seed_menu` (it copies images into `media/food/`) and keep `DJANGO_DEBUG=True` |
| Menu is empty | you skipped `seed_menu` |
| "CSRF verification failed" | open the site as `127.0.0.1:8000` or `localhost:8000` consistently, and don't use VS Code *Live Server* (port 5501) — Django must serve the pages itself |

> **Important:** because Django now serves the pages, don't open the `.html` files directly or with Live Server any more. Always use `python manage.py runserver`.

---

## 13. Before putting it on a real server

Set `DJANGO_DEBUG=False`, a long random `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=yourdomain`, run `python manage.py collectstatic`, serve `/static/` and `/media/` with a web server (Nginx) or WhiteNoise, and run Django with gunicorn/uWSGI behind HTTPS.
