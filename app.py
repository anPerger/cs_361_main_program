import os
from flask import Flask, render_template, request, flash, redirect, session
import webbrowser
from threading import Timer
from bson.json_util import dumps, loads
import json
import pymongo
from pymongo import MongoClient


app = Flask(__name__)
app.secret_key = "portfolio"

# Configuration 
app.config["SESSION_PERMANENT"] = False     # Sessions expire when the browser is closed
app.config["SESSION_TYPE"] = "filesystem"     # Store session data in files


client = MongoClient()
print(client.list_database_names())
portfolio_db = client["portfolio_project"]
users_col = portfolio_db["users"]
historic_averages = portfolio_db["historic_averages"]

# users_col.delete_one({"username": "abc"})

# bonds = {"type": "bonds", "yield": 0.05}
# stocks = {"type": "stocks", "yield": 0.1}
# inflation = {"type": "inflation", "rate": 0.025}

# historic_averages.insert_one(bonds)
# historic_averages.insert_one(stocks)
# historic_averages.insert_one(inflation)

user_data = users_col.find_one({"username": "abc"})
print(user_data)

@app.route("/")
def home():
    session["name"] = None
    return render_template("index.html")


@app.route("/fetch-account", methods=["GET", "POSt"])
def fetch_account():

    username = request.form.get("username")
    password = request.form.get("password")

    user_data = users_col.find_one({"username": username})

    if user_data:
        if password == user_data["password"]:
            session["name"] = username
            return redirect("/profile")
        else:
            error_msg = "That username and password don't match our records"
            flash(error_msg, "error")
            return redirect("/")
    else:
        error_msg = "That username and password don't match our records"
        flash(error_msg, "error")
        return redirect("/")



@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("name"):
        return redirect("/")

    username = session["name"]

    user_data = users_col.find_one({"username": username})

    return render_template("profile.html", user_data=user_data)


@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    return render_template("create-account.html")


@app.route("/profile-confirmation", methods=["GET", "POST"])
def profile_confirmation():

    username = request.form.get("username")
    password = request.form.get("password")

    user_data = users_col.find_one({"username": username})

    if user_data:
        error_msg = "That username is already in use"
        flash(error_msg, "error")
        return redirect("/create-account")
    
    users_col.insert_one({
        "username": username, "password": password, 
        "risk": "none", "horizon": 0, 
        "default_portfolio": {"name": "Default-Portfolio", "stocks": 0, "bonds": 0, "cash": 0}, "custom_portfolios": []
        })

    success_msg = "Your account has been created"
    flash(success_msg, "success")
    return redirect("/")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session["name"] = None
    return redirect("/")


@app.route("/update-profile", methods=["GET", "POST"])
def update_profile():
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    password = request.form.get("password")
    horizon = request.form.get("horizon")
    risk = request.form.get("risk")

    prior_user = users_col.find_one({"username": username})

    if not password:
        password = prior_user["password"]
    if not horizon:
        horizon = prior_user["horizon"]
    if not risk:
        risk = prior_user["risk"]

    horizon = int(horizon)

    query_filter = {"username": username}
    update_operation = {
        "$set": {"password": password, "horizon": horizon, "risk": risk}
        }

    users_col.update_one(query_filter, update_operation)

    user_data = users_col.find_one({"username": username})
    print(user_data)

    success_msg = "Your profile has been updated"
    flash(success_msg, "success")
    return redirect("/build-default-portfolio")

@app.route("/risk-survey", methods=["GET", "POST"])
def risk_survey():
    if not session.get("name"):
        return redirect("/")
    
    return render_template("risk-survey.html")

@app.route("/risk-survey-submit", methods=["GET", "POST"])
def risk_survey_submit():
    if not session.get("name"):
        return redirect("/")

    username = session["name"]
    q1 = int(request.form.get("q1"))
    q2 = int(request.form.get("q2"))
    q3 = int(request.form.get("q3"))
    q4 = int(request.form.get("q4"))
    q5 = int(request.form.get("q5"))
    q6 = int(request.form.get("q6"))
    q7 = int(request.form.get("q7"))
    q8 = int(request.form.get("q8"))
    # print(q1)
    # print(q2)
    # print(q3)
    # print(q4)
    # print(q5)
    # print(q6)
    # print(q7)
    # print(q8)

    risk_score = (q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8) 

    # print(risk_score)

    if risk_score < 13:
        user_risk = "Low"
    if (risk_score >= 13) & (risk_score < 19):
        user_risk = "Medium"
    if risk_score >= 19:
        user_risk = "High"

    query_filter = {"username": username}
    update_operation = {
        "$set": {"risk": user_risk}
        }
    users_col.update_one(query_filter, update_operation)
    

    success_msg = "Thanks for completing the survey. Based on your results you have a " + user_risk + " level of risk tolerence"
    flash(success_msg, "success")
    return redirect("/build-default-portfolio")
    

@app.route("/build-default-portfolio", methods=["GET", "POST"])
def build_default_portfolio():
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    

    user_data = users_col.find_one({"username": username})

    user_risk = user_data["risk"]
    user_horizon = user_data["horizon"]

    if user_risk == "none":
        error_msg = "Cannot build a portfolio for you without providing a risk profile"
        flash(error_msg, "error")
        return render_template("profile.html", user_data=user_data)
    if user_horizon == 0:
        error_msg = "Cannot build a portfolio for you without providing an investment time horizon"
        flash(error_msg, "error")
        return render_template("profile.html", user_data=user_data)

    if  user_risk == "High":
        if user_horizon == 1:
            stock_allocation = 0.2
            bond_allocation = 0.4
            cash_allocation = 0.4
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.6
            bond_allocation = 0.4
            cash_allocation = 0
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.8
            bond_allocation = 0.2
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 1
            bond_allocation = 0
            cash_allocation = 0
    if  user_risk == "Medium":
        if user_horizon == 1:
            stock_allocation = 0.1
            bond_allocation = 0.45
            cash_allocation = 0.45
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.45
            bond_allocation = 0.45
            cash_allocation = 0.1
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.75
            bond_allocation = 0.25
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 0.9
            bond_allocation = 0.1
            cash_allocation = 0
    if  user_risk == "Low":
        if user_horizon == 1:
            stock_allocation = 0
            bond_allocation = 0.5
            cash_allocation = 0.5
        if (user_horizon > 1) & (user_horizon <= 5):
            stock_allocation = 0.3
            bond_allocation = 0.5
            cash_allocation = 0.2
        if (user_horizon > 5) & (user_horizon <= 10):
            stock_allocation = 0.5
            bond_allocation = 0.5
            cash_allocation = 0
        if (user_horizon > 10):
            stock_allocation = 0.6
            bond_allocation = 0.4
            cash_allocation = 0

    portfolio_allocation = {"name": "Default-Portfolio", "stocks": stock_allocation, "bonds": bond_allocation, "cash": cash_allocation}

    query_filter = {"username": username}
    update_operation = {
        "$set": {"default_portfolio": portfolio_allocation}
        }


    users_col.update_one(query_filter, update_operation)


    success_msg = "A portfolio based on your investment profile has been created"
    flash(success_msg, "success")
    return redirect("/profile")


@app.route("/portfolio-list", methods=["GET", "POST"])
def portfolio_list():

    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]

    user_data = users_col.find_one({"username": username})

    default_portfolio = user_data["default_portfolio"]

    custom_portfolios = user_data["custom_portfolios"]

    return render_template("portfolio-list.html", default_portfolio=default_portfolio, custom_portfolios=custom_portfolios)



@app.route("/portfolio-view/<portfolio_name>", methods=["GET", "POST"])
def portfolio_view(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    username = session["name"]
    user_data = users_col.find_one({"username": username})

    if portfolio_name == "default-portfolio":
        portfolio = user_data["default_portfolio"]

    print(portfolio)

    return render_template("portfolio-view.html", portfolio=portfolio)


@app.route("/delete-portfolio/<portfolio_name>", methods=["GET", "POST"])
def delete_portfolio(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    
    if portfolio_name == "Default-Portfolio":
        error_msg = "You cannot delete your default portfolio. If you would like to change your default portfolio you must edit your profile investment characteristics"
        flash(error_msg, "error")
        return redirect("/profile")


@app.route("/edit-portfolio/<portfolio_name>", methods=["GET", "POST"])
def edit_portfolio(portfolio_name):
    if not session.get("name"):
        return redirect("/")
    

    if portfolio_name == "Default-Portfolio":
        error_msg = "If you would like to change your default portfolio you must edit your profile investment characteristics"
        flash(error_msg, "error")
        return redirect("/profile")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

# def open_browser():
#     webbrowser.open_new("http://127.00.1:5000")

# if __name__ == "__main__":
#     Timer(2, open_browser).start()
#     app.run()