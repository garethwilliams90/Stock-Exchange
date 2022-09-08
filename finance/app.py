#API KEY: pk_4ac5e49ea1814a2cbceba806daa5575d
import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


import datetime
datetime_object = datetime.datetime.now()

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "GET":

        user_dict = db.execute("SELECT username FROM users WHERE username = ?", session["user_id"])
        username = user_dict[0]["username"]
        # Define current user
        #current_user = db.execute("SELECT username FROM users WHERE username = ?", username)

        # Ease of access for current portfolio
        current_portfolio = username+"_portfolio"
        curr_port = db.execute("SELECT * FROM ?", current_portfolio)

        # Define the total portfolio value
        value = db.execute("SELECT SUM(order_price) FROM ?", current_portfolio)

        # Define cash spent
        cash_spent_dict = db.execute("SELECT SUM(order_price) FROM ?", current_portfolio)
        cash_spent = cash_spent_dict[0]['SUM(order_price)']

        # Define the user's available cash
        cash_dict = db.execute("SELECT cash FROM users WHERE username = ?", username)
        cash = cash_dict[0]['cash']

        if not cash_spent:
            cash_spent = 0
            av_cash = cash
        av_cash = cash - cash_spent

        # Condition before they have bought any stock
        port_val = value[0]["SUM(order_price)"]
        if not port_val:
            port_val = 0
        else:
            port_val = int(value[0]["SUM(order_price)"])

        # Get information from the total portfolio that is updated each time buy and sell are called
        copy_portfolio = username+"_copy"
        total_port = db.execute("SELECT * FROM ?", copy_portfolio)

        # Take them to index.html to view portfolio
        return render_template("index.html", port_val=port_val, total_port=total_port, av_cash=av_cash)





@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # Display buy.html page when requested
    if request.method == "GET":
        return render_template("buy.html")

    # When the buy now button is submitted - want to run our checks then take them to index page to show portfolio
    if request.method == "POST":

        # First we need to get the information submitted from the POST action
        symbol = request.form.get("symbol").upper()
        holdings = float(request.form.get("shares"))


        user_dict = db.execute("SELECT username FROM users WHERE username = ?", session["user_id"])
        username = user_dict[0]["username"]

        # Define the available cash the user has
        available_cash = db.execute("SELECT cash FROM users WHERE username = ?", username)
        av_cash = available_cash[0]["cash"]

        # Run checks
        # First check: did they enter number of stocks
        if not holdings:
            return apology("please enter the number of stocks you wish to purchase", 400)

        # Second check: did they enter a stock code
        if not symbol:
            return apology("please enter a stock symbol", 400)

        # Third check: did they enter a VALID stock code
        if not lookup(symbol):
            return apology("please enter a valid stock symbol", 400)

        # Fourth check: Did they enter a postive integer amount of stocks
        if holdings < 0:
            return apology("please enter a positive integer of stocks")

        # Define the order total
        order_price = int(lookup(symbol)["price"]) * (holdings)
        # Fith check: Do they have enough money to pay for the stock order
        if order_price > av_cash:
            return apology("sorry, you do not have enough money for this order", 400)

        # If all is good - then take them to the portfolio - index.hmtl
        else:
            # Easy access to the current user's portfolio table
            current_port = str(username)+"_portfolio"

            # Current portfolio COPY
            current_copy = str(username)+"_copy"

            # Insert the new purchases into their portfolio
            db.execute("INSERT INTO ? (symbol, holdings, order_price, date) VALUES (?, ?, ?, ?)", current_port, symbol, holdings, order_price, datetime_object)

            # Lets check for the symbol in the copy table
            # SQL statement that returns true or false if the symbol is in the table
            copy_check = db.execute("SELECT symbol FROM ? WHERE symbol = ?", current_copy, symbol)
            if not copy_check:
                db.execute("INSERT INTO ? (symbol, holdings, order_price, date) VALUES (?, ?, ?, ?)", current_copy, symbol, 0, 0, datetime_object)

            db.execute("UPDATE ? SET holdings = holdings + ?, order_price = order_price + ? WHERE symbol = ?", current_copy, holdings, order_price, symbol)

            # Finally lets update the users cash
            db.execute("UPDATE users SET cash = cash - ? WHERE username = ?", order_price, username)


            # Redirect to index.html
            return redirect("/")





@app.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":

        user_dict = db.execute("SELECT username FROM users WHERE username = ?", session["user_id"])
        username = user_dict[0]["username"]

        # Ease of access for current portfolio
        current_portfolio = username+"_portfolio"
        curr_port = db.execute("SELECT * FROM ? ORDER BY date DESC", current_portfolio)

        return render_template("history.html", curr_port=curr_port)

    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = request.form.get("username")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # Return the stock quote form to request stocks
    if request.method == "GET":
        return render_template("quote.html")

    # Submit the form when POST
    if request.method == "POST":
        stock_code = request.form.get("symbol")
        stock_num = request.form.get("number")

        # If they forgot to enter something return apology
        if not stock_code or not stock_num:
            return apology("must enter stock code and number of stocks", 400)
        # Negative number of stocks
        elif int(stock_num) < 0:
            return apology("cannot enter a negative number of stocks", 400)

        # Use lookup function to check if stock code is valid
        if not lookup(stock_code):
            return apology("stock code was not found, please enter a valid stock code", 400)
        else:
            # Display the stock information to the user: Stock code, price, and stock name
            return render_template("quoted.html", name=lookup(stock_code)["name"], symbol=lookup(stock_code)["symbol"],  price = lookup(stock_code)["price"], order_price = (lookup(stock_code)["price"] * int(stock_num)))

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # When requested via GET, show the user a form to submit
    if request.method == "GET":
        return render_template("register.html")

    # When form is submitted via POST, check for errors, if no errors, add the new user into the new users table
    if request.method == "POST":
        reg_pass = request.form.get("password")
        reg_user = request.form.get("username")
        reg_ver = request.form.get("confirmation")

        # Forgot to enter something
        if not reg_pass or not reg_user:
            return apology("must provide username and password", 400)
        elif not reg_ver:
            return apology("please confirm your password", 400)
        # Password and verification need to match
        elif reg_pass != reg_ver:
            return apology("passwords do not match", 400)
        # Username already exists inside the database
        elif db.execute("SELECT username FROM users WHERE username = ?", reg_user):
            return apology("username already exists", 400)

        # Generate a hash of the password to add to database for security
        reg_hash = generate_password_hash(reg_pass,method='pbkdf2:sha256',salt_length=8)

        # Add new user into users database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", reg_user, reg_hash)

        # Create a table for our user's portfolio
        db.execute("CREATE TABLE ? (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, symbol TEXT NOT NULL, holdings NUMERIC NOT NULL, order_price NUMERIC NOT NULL, date DATETIME NOT NULL)", reg_user + "_portfolio")

        # Create a copy of table above that is updated for buy and sell instead of INSERT INTO
        db.execute("CREATE TABLE ? (transaction_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, symbol TEXT NOT NULL, holdings NUMERIC NOT NULL, order_price NUMERIC NOT NULL, date DATETIME NOT NULL)", reg_user + "_copy")

        # Then log user in
        session["user_id"] = reg_user

        user_dict = db.execute("SELECT username FROM users WHERE username = ?", reg_user)
        #username = user_dict[0]["username"]
        #session["username"] = username
        return redirect("/") # REDIRECT TO LOGGED IN PAGE SO ITS EASIER TO KNOW IF LOGGED IN


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Display sell.html when requested
    if request.method == "GET":
        return render_template("sell.html")

    # When Sell Now button press - run our checks then add to database
    if request.method == "POST":

        # Lets get information about the stock code and amount of shares
        symbol = request.form.get("symbol")
        holdings = float(request.form.get("number"))

        # Define the order total (negative number!)
        order_price = -1 * (int(lookup(symbol)["price"]) * (holdings))

        user_dict = db.execute("SELECT username FROM users WHERE username = ?", session["user_id"])
        username = user_dict[0]["username"]

        # Ease of access for current portfolio
        current_portfolio = username+"_portfolio"
        curr_port = db.execute("SELECT * FROM ?", current_portfolio)

        # Current portfolio COPY
        current_copy = username+"_copy"

        # Define the available cash the user has
        available_cash = db.execute("SELECT cash FROM users WHERE username = ?", username)

        # Run checks
        # First check: did they enter number of stocks
        if not holdings:
            return apology("please enter the number of stocks you wish to purchase", 400)

        # Second check: did they enter a stock code
        if not symbol:
            return apology("please enter a stock symbol", 400)

        # Third check: did they enter a VALID stock code
        if not lookup(symbol):
            return apology("please enter a valid stock symbol", 400)

        # Fourth check: Did they enter a postive integer amount of stocks
        if holdings < 0:
            return apology("please enter a positive integer of stocks")

        # Fith check: Is selling number less than the amount they own
        # Define current_holdings
        current_holdings_dict = db.execute("SELECT holdings FROM ? WHERE symbol = ?", current_portfolio, symbol)
        current_holdings = current_holdings_dict[0]['holdings']
        if holdings > current_holdings:
            return apology("sorry, you cannot sell more stocks than you own", 400)

        # If all is good - then take them to the portfolio - index.hmtl
        else:
            # Easy access to the current user's portfolio table
            current_port = str(username)+"_portfolio"

            # Insert the new purchases into their portfolio
            db.execute("INSERT INTO ? (symbol, holdings, order_price, date) VALUES (?, ?, ?, ?)", current_port, symbol, holdings, order_price, datetime_object)

            # Lets check for the symbol in the copy table
            # SQL statement that returns true or false if the symbol is in the table
            copy_check = db.execute("SELECT symbol FROM ? WHERE symbol = ?", current_copy, symbol)
            if not copy_check:
                db.execute("INSERT INTO ? (symbol, holdings, order_price, date) VALUES (?, ?, ?, ?)", current_copy, symbol, 0, 0, datetime_object)

            db.execute("UPDATE ? SET holdings = holdings - ?, order_price = order_price + ? WHERE symbol = ?", current_copy, holdings, order_price, symbol)

            # Finally lets update the users cash
            db.execute("UPDATE users SET cash = cash - ? WHERE username = ?", order_price, username)


            # Redirect to index.html
            return redirect("/")



@app.route("/settings", methods=["GET","POST"])
def settings():
    """Settings Page to change password"""

    if request.method == "GET":
        return render_template("settings.html")

    if request.method == "POST":


        user_dict = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        username = user_dict[0]["username"]

        # Define current user
        current_user = db.execute("SELECT username FROM users WHERE username = ?", session["user_id"])
        current_hash_dict = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])
        current_hash = current_hash_dict[0]['hash']

        # Lets get username pass and new password
        username = request.form.get("user")
        current = request.form.get("current")
        new = request.form.get("new")

        # Returns a string from the password entered
        current_password = generate_password_hash(current, method='pbkdf2:sha256', salt_length=16)

        # Returns a string for new password
        new_hash = generate_password_hash(new, method='pbkdf2:sha256', salt_length=16)

        # Usual checks to see if they entered info correctly
        if not username or not current or not new:
            return apology("please enter all three fields", 400)

        # Check entered username against the one in database
        if username != session["user_id"]:
            return apology("incorrect username", 400)

        # Check the entered password against the one stored in the database
        if not check_password_hash(current_password, current):
            return apology("password you entered, does not match", 400)

        else:
            # Now update the password in the database and return to homepage
            db.execute("UPDATE users SET hash = ? WHERE username = ?", new_hash, username)

            # Redirect user to default page
            return redirect("/")