from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from app2 import login_required

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///storage.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    user_id = session["user_id"]

    if not session["user_id"]:
        return redirect("/login")

    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]["username"]

    cash_available = str(db.execute("SELECT cash FROM users WHERE username = ?", username)[0]["cash"])
    currency = "£"
    cash_available = currency + cash_available
    return render_template("index.html", cash_available=cash_available, username=username)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash( rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        db.execute("UPDATE users SET cash = 10000 WHERE id = ?", session["user_id"])

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        rows = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 0:
            return apology("username taken", 400)

        db.execute("INSERT INTO users (username,hash) VALUES(?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        flash("Successfully registered")
        return redirect("/login")

    else:
        return render_template("sign_in.html")

@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        user_id = session["user_id"]
        username = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]["username"]
        acc_no = db.execute("SELECT * FROM data WHERE AccountNumber = ?", request.form.get("acc_no"))
        sort_code = db.execute("SELECT * FROM data WHERE SortCode = ?", request.form.get("sort_code"))
        name = db.execute("SELECT * FROM data WHERE Name = ?", request.form.get("name"))

        if len(acc_no) == 0 or len(sort_code) == 0 or len(name) == 0:
            return apology("Please enter valid data from the provided dataset")

        else:
            rows = db.execute("SELECT * FROM data WHERE Name = ? AND AccountNumber = ? AND SortCode = ?", request.form.get("name"), request.form.get("acc_no"), request.form.get("sort_code"))
            if len(rows) != 1:
                print("doesn't work")
                return apology("The data does not match, please make sure that all the details are associated with the same account")

            else:
                value = str(db.execute("SELECT Fraud FROM data WHERE Name = ? AND AccountNumber = ? AND SortCode = ?", request.form.get("name"), request.form.get("acc_no"), request.form.get("sort_code")))[12:-3]
                print("The value is", value)
                value1 = "Y"
                if value != value1:
                    print("non-validated payment")
                    return apology("The account you were transferring money to was flagged as a fraudulent account, please try making transactions to any other accounts")
                else:
                    transact = int(request.form.get("amount"))
                    total = str(db.execute("SELECT cash FROM users WHERE username = ?", username))[10:-2]
                    total = int(total)
                    if transact > total:
                        return apology("insufficient balance")
                    else:
                        total = total-transact
                        db.execute("UPDATE users SET cash = ? WHERE username = ?", total, username)
                        return redirect("/")

    else:
        return render_template("transfer.html")



def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

