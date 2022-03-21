import os
from anki.storage import Collection
import json
from tempfile import gettempdir
from bs4 import BeautifulSoup
from celery import Celery
from zipfile import ZipFile
from models import User, Cards, Decks, DeckCard, db
from gramex.services import SMTPMailer
from flask import Flask

with open('.secrets.json', 'r') as fin:
    secrets = json.load(fin)

mailer = SMTPMailer(
    "gmail",
    email="deshpande.jaidev@gmail.com",
    password=secrets['gmail-password'],
)

op = os.path
app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost")


def create_app():
    flask_app = Flask(__name__)
    flask_app.config["SECRET_KEY"] = "h3110w041d"
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite3"
    flask_app.config["SECURITY_PASSWORD_SALT"] = "bcrypt"
    flask_app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"] = "Authentication-Token"
    # app.config['SECURITY_LOGIN_URL'] = '/login'
    flask_app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "login.html"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


def _mkdir(path):
    if not op.isdir(path):
        os.makedirs(path)


@app.task
def anki_import(name, buff, user):
    flask_app = create_app()
    db.init_app(flask_app)
    with flask_app.app_context():
        email = User.query.get(user).email
    tempdir = gettempdir()

    with ZipFile(buff) as z:
        z.extract("collection.anki2", tempdir)
        with z.open("media") as m:
            media = json.load(m)
        path = op.join(tempdir, "collection.anki2")
        deck = Collection(path)
        os.remove(path)
        notes = deck.find_notes("")
        noteFields = [deck.getNote(i).fields for i in notes]
        backs = [f[-1] for f in noteFields]
        frontImages = [BeautifulSoup(f[0]).find("img").attrs["src"] for f in noteFields]
        media = {v: k for k, v in media.items()}
        uploads_dir = op.join("static/uploads", email)
        _mkdir(uploads_dir)
        for frontImage in frontImages:
            img = z.read(media[frontImage])
            with open(op.join(uploads_dir, frontImage), "wb") as fout:
                fout.write(img)

    cards = []
    with flask_app.app_context():
        # Insert cards
        for frontImage, back in zip(frontImages, backs):
            card = Cards(user=user, front="", image=frontImage, back=back)
            db.session.add(card)
            db.session.commit()
            cards.append(card)

        # insert deck
        deck = Decks(name=name, user=user)
        db.session.add(deck)
        db.session.commit()

        # Make card-deck pairs
        deckcards = [DeckCard(deck=deck.id, card=c.id) for c in cards]
        for deckcard in deckcards:
            db.session.add(deckcard)
            db.session.commit()

    os.remove(buff)
    return name


@app.task
def notify_import(deck_name, email):
    mailer.mail(to=email, subject="Your deck is ready!", body="Your deck is ready.")
