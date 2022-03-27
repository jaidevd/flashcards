from tempfile import NamedTemporaryFile
from datetime import datetime
import os
import json
from mimetypes import guess_type
from flask import (
    render_template,
    request,
    abort,
    redirect,
    url_for,
    make_response,
    jsonify,
)

from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    current_user,
    login_required,
    logout_user,
)
from flask_caching import Cache


from models import User, Cards, Decks, DeckCard, db, Role, History
from tasks import anki_import, notify_import, _mkdir, create_app, notify_webhook


op = os.path
app = create_app()
db.init_app(app)
cache = Cache(app)
ROOT = op.dirname(__file__)


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


@app.route("/")
@login_required
@cache.cached(timeout=60)
def index():
    if current_user.is_authenticated:
        cards = Cards.query.filter_by(user=current_user.id)
        decks = Decks.query.filter_by(user=current_user.id)
        return render_template(
            "index.html", cards=cards, decks=decks, token=request.args["auth_token"]
        )
    return redirect(url_for("login"))


@app.route("/logout/", methods=["GET"])
def logout():
    logout_user()
    return redirect("/login")


@app.route("/upload/", defaults={"filename": ""}, methods=["POST", "GET"])
@app.route("/upload/<path:filename>")
@cache.cached(timeout=3600)
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
        fpath = op.join(path, filename)
        with open(fpath, "rb") as fin:
            data = fin.read()
        mtype = guess_type(fpath)
        resp = make_response(data)
        resp.headers["Content-Type"] = mtype
        return resp


@app.route("/card/", defaults={"card_id": ""}, methods=["GET", "POST"])
@app.route("/card/<string:card_id>")
@cache.cached(timeout=3600)
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
@app.route("/deck/<int:deck_id>", methods=["GET", "POST", "DELETE"])
@login_required
@cache.cached(timeout=300)
def deck(deck_id):
    if request.method == "GET":
        deck = Decks.query.get(deck_id)
        return render_template(
            "deck.html", deck=deck, token=request.args.get("auth_token", "")
        )
    if request.method == "DELETE":
        deck = Decks.query.get(deck_id)
        db.session.delete(deck)
        deckcards = DeckCard.query.filter_by(deck=deck.id)
        for card in deckcards:
            db.session.delete(card)
        db.session.commit()
        return "", 200
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
        return "", 201


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", existing_user=False)
    if request.method == "POST":
        email = request.form["email"]
        existing_user = User.query.filter_by(email=email).first()
        if existing_user is not None:
            return render_template("signup.html", existing_user=existing_user)
        user = User(
            email=email,
            password=request.form["password-1"],
            roles=[Role.query.get(1)],
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")


@app.route("/import", methods=["POST"])
@login_required
def deck_import():
    app.logger.debug(current_user.email)
    _file = request.files["file"]
    with NamedTemporaryFile(mode="wb", delete=False) as buff:
        _file.save(buff)
    anki_import.apply_async(
        (_file.filename, buff.name, current_user.id),
        link=notify_import.s(current_user.email),
    )
    return redirect("/")


@app.route("/scores/<int:deck_id>", methods=["GET", "POST"])
@app.route("/scores/", defaults={"deck_id": ""}, methods=["POST", "GET"])
@login_required
@cache.cached(timeout=60)
def scores(deck_id):
    if request.method == "GET":
        if deck_id:
            deck_scores = History.query.filter_by(deck=deck_id)
            return jsonify(deck_scores.all())
        else:
            return jsonify([h.serialize() for h in History.query.all()])
    if request.method == "POST":
        data = json.loads(request.data)
        score = data["score"]
        deck_id = data["deck"]
        deck = Decks.query.get(deck_id)
        history = History(deck=deck.id, score=score, timestamp=datetime.now())
        db.session.add(history)
        db.session.commit()
        notify_webhook.apply_async((current_user.email, deck.name, score))
        return "", 201


@app.route("/export/<int:deck_id>", methods=["GET"])
@login_required
@cache.cached(timeout=3600)
def export(deck_id):
    exportpath = op.join(op.dirname(__file__), "exports")
    _mkdir(exportpath)
    filepath = op.join(exportpath, f"{deck_id}.zip")
    deck = Decks.query.get(deck_id)
    if not op.isfile(filepath):
        deck.export(filepath)
    with open(filepath, "rb") as fout:
        data = fout.read()
    resp = make_response(data)
    resp.headers["Content-Type"] = "application/zip"
    resp.headers["Content-Disposition"] = f'attachment; filename="{deck.name}.zip"'
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
