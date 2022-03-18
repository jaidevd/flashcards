import os
import json
from flask import (
    Flask,
    render_template,
    request,
    abort,
    redirect,
    url_for,
    send_from_directory,
)

from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required,
    logout_user,
)


from models import User, Cards, Decks, DeckCard, db, Role

op = os.path


app = Flask(__name__)
app.config["SECRET_KEY"] = "h3110w041d"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite3"
app.config["SECURITY_PASSWORD_SALT"] = "bcrypt"
app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"] = "Authentication-Token"
# app.config['SECURITY_LOGIN_URL'] = '/login'
app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "login.html"
app.config["WTF_CSRF_ENABLED"] = False

db.init_app(app)
ROOT = op.dirname(__file__)


def _mkdir(path):
    if not op.isdir(path):
        os.makedirs(path)


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


@app.route("/")
@login_required
def index():
    if current_user.is_authenticated:
        cards = Cards.query.filter_by(user=current_user.id)
        decks = Decks.query.filter_by(user=current_user.id)
        return render_template("index.html", cards=cards, decks=decks)
    return redirect(url_for("login"))


@app.route("/logout/", methods=["GET"])
def logout():
    logout_user()
    return redirect("/login")


@app.route("/upload/", defaults={"filename": ""}, methods=["POST", "GET"])
@app.route("/upload/<path:filename>")
@login_required
def upload(filename):
    path = op.join(ROOT, "static", "uploads", current_user.email)
    if request.method == "POST":
        _mkdir(path)
        _file = request.files["file"]
        target = op.join(path, _file.filename)
        _file.save(target)
        return op.relpath(target, ROOT), 201
    if request.method == "GET":
        return send_from_directory(path, filename)


@app.route("/card/", defaults={"card_id": ""}, methods=["GET", "POST"])
@app.route("/card/<string:card_id>")
@login_required
def card(card_id):
    if request.method == "GET":
        if card_id == "create":
            return render_template("create-card.html")
        card_data = Cards.query.filter_by(card_id=int(card_id))
        return render_template("card.html", card_data)
    if request.method == "POST":
        if card_id:
            abort(400, "card_id not allowed when POSTing a card.")
        card = Cards(
            user=current_user.id,
            front=request.form["cardfront"],
            back=request.form["cardback"],
            image=request.form["cardimg"],
        )
        db.session.add(card)
        db.session.commit()
        return redirect("/card/create")


@app.route("/deck/", defaults={"deck_id": ""}, methods=["POST", "GET"])
@app.route("/deck/<int:deck_id>")
@login_required
def deck(deck_id):
    if request.method == "GET":
        deck = Decks.query.get(deck_id)
        return render_template("deck.html", deck=deck)
    if request.method == "POST":
        deck = Decks(name=request.form["deckname"], user=current_user.id)
        db.session.add(deck)
        db.session.commit()

        # Add cards to deck
        for card in json.loads(request.form["cards"]):
            card_id = int(card.split("-")[-1])
            card = Cards.query.get(card_id)
            if card is None:
                abort(404, f"Card with id {card_id} not found.")
            deckcard = DeckCard(deck=deck.id, card=card.id)
            db.session.add(deckcard)
            db.session.commit()
        return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
