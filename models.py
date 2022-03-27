from flask_sqlalchemy import SQLAlchemy
from flask_security.models.fsqla_v2 import FsUserMixin, FsModels, FsRoleMixin
import json
from zipfile import ZipFile
import os
from datetime import datetime
from humanize import naturaldelta


op = os.path
db = SQLAlchemy()
FsModels.set_db_info(db)
db.metadata.clear()

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("users.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("roles.id")),
)


class User(db.Model, FsUserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    email = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=True)
    active = db.Column(db.Boolean(), default=True)
    roles = db.relationship(
        "Role",
        secondary=roles_users,
        backref=db.backref("users", lazy="dynamic"),
    )

    confirmed_at = property(lambda x: "")
    last_login_at = property(lambda x: "")
    current_login_at = property(lambda x: "")
    last_login_ip = property(lambda x: "")
    current_login_ip = property(lambda x: "")
    login_count = property(lambda x: "")
    tf_primary_method = property(lambda x: "")
    tf_totp_secret = property(lambda x: "")
    tf_phone_number = property(lambda x: "")
    create_datetime = property(lambda x: "")
    update_datetime = property(lambda x: "")
    username = property(lambda x: "")
    us_totp_secrets = property(lambda x: "")
    us_phone_number = property(lambda x: "")


class Role(db.Model, FsRoleMixin):
    __tablename__ = "roles"
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    permissions = property(lambda x: "")
    update_datetime = property(lambda x: "")


class Cards(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    user = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    front = db.Column(db.String(), nullable=False)
    back = db.Column(db.String(), nullable=False)
    image = db.Column(db.String())
    tags = db.Column(db.String())


class Decks(db.Model):
    __tablename__ = "decks"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    name = db.Column(db.String(), nullable=False)
    user = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def export(self, path):
        cards = self.get_cards()
        imagepath = op.join(
            op.dirname(__file__), "static", "uploads", User.query.get(self.user).email
        )
        with ZipFile(path, "w") as fout:
            cardsdata = json.dumps(
                [
                    {"id": c.id, "front": c.front, "back": c.back, "image": c.image}
                    for c in cards
                ]
            )
            fout.writestr("cards.json", cardsdata)
            for card in cards:
                fout.write(op.join(imagepath, card.image), f"images/{card.image}")

    def get_cards(self):
        cards = []
        for card in DeckCard.query.filter_by(deck=self.id).all():
            cards.append(Cards.query.get(card.card))
        return cards

    def last_reviewed(self):
        history = (
            History.query.filter_by(deck=self.id)
            .order_by(History.timestamp.desc())
            .first()
        )
        if history is None:
            return None, None
        t = history.timestamp
        ago = naturaldelta(datetime.now() - t)
        return t, ago

    def latest_score(self):
        history = (
            History.query.filter_by(deck=self.id)
            .order_by(History.timestamp.desc())
            .first()
        )
        if history:
            return history.score
        return 0

    def avg_score(self):
        history = History.query.filter_by(deck=self.id).order_by(
            History.timestamp.desc()
        )
        if history.count():
            return round(sum([k.score for k in history]) / history.count(), 2)
        return 0


class History(db.Model):
    __tablename__ = "history"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    deck = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime(), nullable=False)

    def serialize(self):
        return {k.name: self.__dict__[k.name] for k in self.__table__.columns}


class DeckCard(db.Model):
    __tablename__ = "deckcard"
    id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    deck = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)
    card = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
