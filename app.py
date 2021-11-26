from flask import Flask, render_template, request, abort, redirect, url_for
from flask_login import LoginManager, login_user
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.secret_key = "8288975bbb4b17b4b02cbb573bc0a77be37e995440c10ad908bb43624d6d0e62"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite3"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    user_id = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)

    def is_active(self):
        return True

    def get_id(self):
        return self.user_id

    def is_authenticated(self):
        return True


class Cards(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    user = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    front = db.Column(db.String(), nullable=False)
    back = db.Column(db.String(), nullable=False)
    image = db.Column(db.String())
    tags = db.Column(db.String())


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(user_id=user_id).first()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == "POST":
        user = request.form["user_id"]
        password = request.form["password"]
        user = User.query.filter_by(user_id=user).first()
        if not user:
            abort(404, f"User {user} not found.")
        if password != user.password:
            abort(403, "Incorrect password.")
        login_user(user)
        return redirect(url_for("index"))


@app.route("/card/<string:card_id>", methods=["GET", "POST"])
def card(card_id):
    if request.method == "GET":
        if card_id == "create":
            return render_template("create-card.html")
        card_data = Cards.query.filter_by(card_id=int(card_id))
        return render_template("card.html", card_data)


if __name__ == "__main__":
    app.run(debug=True)
