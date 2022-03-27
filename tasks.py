import os
import logging
import requests
from anki.storage import Collection
import json
from tempfile import gettempdir
from bs4 import BeautifulSoup
from celery import Celery
from zipfile import ZipFile
from models import User, Cards, Decks, DeckCard, db
from gramex.services import SMTPMailer
from flask import Flask, render_template
from weasyprint import HTML
from datetime import datetime

with open(".secrets.json", "r") as fin:
    secrets = json.load(fin)

mailer = SMTPMailer(
    "gmail",
    email="deshpande.jaidev@gmail.com",
    password=secrets["gmail-password"],
)

op = os.path
app = Celery("tasks", broker="redis://localhost:6379/0", backend="redis://localhost")


def create_app():
    flask_app = Flask(__name__)
    flask_app.logger.setLevel(logging.DEBUG)
    flask_app.config["SECRET_KEY"] = "h3110w041d"
    flask_app.config["MAX_CONTENT_LENGTH"] = 128 * 1_000_000
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite3"
    flask_app.config["SECURITY_PASSWORD_SALT"] = "bcrypt"
    flask_app.config["SECURITY_TOKEN_AUTHENTICATION_HEADER"] = "Authentication-Token"
    # app.config['SECURITY_LOGIN_URL'] = '/login'
    flask_app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "login.html"
    flask_app.config["WTF_CSRF_ENABLED"] = False

    # Caching configuration
    flask_app.config["CACHE_TYPE"] = "RedisCache"
    flask_app.config["CACHE_KEY_PREFIX"] = "fc_"
    flask_app.config["CACHE_REDIS_HOST"] = "127.0.0.1"
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
        uploads_dir = op.join(op.dirname(__file__), "static/uploads", email)
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


@app.task
def notify_webhook(email, deck, score):
    text = f"Hello! You just scored {round(score, 2)}% on the {deck} deck!"
    if email in secrets["webhooks"]:
        url = secrets["webhooks"][email]
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"text": text}),
        )
        return resp.json(), resp.status_code
    return "No webhook for email {email}", 404


# Scheduled tasks
@app.on_after_configure.connect
def setup_email_reminders(sender, **kwargs):
    flask_app = create_app()
    db.init_app(flask_app)
    with flask_app.app_context():
        for user in User.query.all():
            sender.add_periodic_task(3600, email_reminder.s(user.email))


@app.task
def email_reminder(email):
    body = """Dear user,

    This is your periodic reminder for revising your flashcard decks.

    Login now and start learning!"""
    mailer.mail(to=email, subject="[Flashcards] Don't forget to practice!", body=body)


@app.task
def progress_report(user_id):
    flask_app = create_app()
    db.init_app(flask_app)
    with flask_app.app_context():
        user = User.query.get(user_id)
        decks = Decks.query.filter_by(user=user_id)
        html = render_template("progress-report.html", user=user, decks=decks)
        _mkdir("reports")
        reports_dir = op.join("reports", user.email)
        _mkdir(reports_dir)
        now = datetime.now().strftime("%Y-%m-%d:%H-%M%S")
        attachment = op.join(
            reports_dir, f"[FlashCards] - Progress Report - [{user.email}] - {now}.pdf"
        )
        HTML(string=html).write_pdf(attachment)
        mailer.mail(
            to=user.email,
            subject="[Flashcards] Your Progress Report",
            html=html,
            attachments=[attachment],
        )
