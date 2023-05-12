from flask import Flask, render_template, redirect, request
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin
from flask_user.signals import user_registered
from action_network import ActionNetwork
from tasks import process_emailer
import os
import uuid

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI =  os.environ.get("SQLALCHEMY_DATABASE_URI")   # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False    # Avoids SQLAlchemy warning

    # Flask-Mail SMTP server settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")


    # Flask-User settings
    USER_APP_NAME = "Action Network Apps"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = True        # Enable email authentication
    USER_ENABLE_USERNAME = False    # Disable username authentication
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = os.environ.get("USER_EMAIL_SENDER_EMAIL")

    # Celery
    CELERY_BROKER_URL='redis://redis:6379',
    CELERY_RESULT_BACKEND='redis://redis:6379'

app = Flask(__name__)
app.config.from_object(__name__+'.ConfigClass')

# Initialize Flask-BabelEx
babel = Babel(app)

# Init database
db = SQLAlchemy(app)

migrate = Migrate(app, db)

# Define the User data-model.
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    email = db.Column(db.String(255, collation='NOCASE'), nullable=False, unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False, server_default='')

    # User information
    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')

    # Define the relationship to Role via UserRoles
    roles = db.relationship('Role', secondary='user_roles')

    # Action Network Keys
    action_network_keys = db.relationship('ActionNetworkCredential', backref='users', lazy=True)

# Define the Role data-model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

# Setup Flask-User and specify the User data-model
user_manager = UserManager(app, db, User)

# Define Action Network Credential
class ActionNetworkCredential(db.Model):
    __tablename__ = 'action_network_credential'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    key = db.Column(db.String, nullable=False)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "key": self.key
        }
    
class RollingEmailer(db.Model):
    __tablename__ = 'rolling_emailer'
    id = db.Column(db.Integer, primary_key=True)
    prefix = db.Column(db.String)
    trigger_tag_id = db.Column(db.String)
    target_view = db.Column(db.String)
    message_view = db.Column(db.String)
    end_tag_id = db.Column(db.String)

    # Name of .env variable
    action_network_api_key = db.Column(db.String)

    # Webhook address to trigger
    webhook = db.Column(db.String, default=str(uuid.uuid4()))

    def to_dict(self, public=False):
        if public:
            return {
                'id': self.id,
                'prefix': self.prefix
            }
        else:
            return {
                'id': self.id,
                'prefix': self.prefix,
                'trigger_tag_id': self.trigger_tag_id,
                'target_view': self.target_view,
                'message_view': self.message_view,
                'end_tag_id': self.end_tag_id,
                'action_network_api_key': self.action_network_api_key,
                'webhook': self.webhook
            }

# Create all database tables
with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return "Hello world"

@user_registered.connect_via(app)
def _after_registration_hook(sender, user, **extra):
    print(f"User registered: {user.email}")
    users = User.query.all()
    print(f"Users in system: {len(users)}")
    if len(users) == 1:
        add_role(user, "Admin")

# def setup():
#     users = User.query.all()
#     if len(users) != 0:
#         return redirect("/")
    

@app.route("/members")
@roles_required('Admin')
def manage_members():
    users = User.query.all()
    return render_template("members.html", users=users)

@app.route("/make_admin/<int:id>")
@roles_required('Admin')
def make_admin(id):
    user = User.query.get(id)
    add_role(user, "Admin")
    return redirect("/members")

def add_role(user, role_name):
    if not Role.query.filter(Role.name == role_name).first():
        role = Role(name=role_name)
        db.session.add(role)
    else:
        role = Role.query.filter(Role.name == role_name).first()
    user.roles.append(role)
    db.session.commit()

@app.route("/action_network_credentials", methods=["POST", "GET"])
@roles_required('Admin')
def action_network_credentials():
    print(current_user.action_network_keys)
    if request.method == "GET":
        return [key.to_dict() for key in current_user.action_network_keys]
    if request.method == "POST":
        body = request.json
        key = ActionNetworkCredential(
            name=body.get("name"),
            key=body.get("key"),
            created_by_id=current_user.id
        )
        db.session.add(key)
        db.session.commit()
        return key.to_dict()

@app.route("/tags/<int:key_id>")
@roles_required('Admin')
def get_action_network_tags(key_id):
    key_db = ActionNetworkCredential.query.get(key_id)
    key = os.environ.get(key_db.key)
    an = ActionNetwork(key=key)
    tags = [
        {
            "id": tag["id"],
            "name": tag["name"]
        } for tag in an.get_all("tags")
    ]
    return tags

@app.route("/rolling_emailer", methods=["POST", "GET"])
@roles_required('Admin')
def rolling_emailers():
    if request.method == "GET":
        emailers = RollingEmailer.query.all()
        return render_template("rolling_emailers.html", emailers=emailers)
    elif request.method == "POST":
        if request.content_type == "application/json":
            body = request.json
        else:
            body = request.form.to_dict()
        print(body)
        if body.get('id'):
            emailer = RollingEmailer.query.get(body['id'])
        else:
            emailer = RollingEmailer()
        for attr in ["prefix", "trigger_tag_id", "target_view", "message_view", "end_tag_id", "action_network_api_key"]:
            if body.get(attr):
                setattr(emailer, attr, body.get(attr))
        db.session.add(emailer)
        db.session.commit()
        if request.content_type == "application/json":
            return emailer.to_dict()
        else:
            return redirect("/rolling_emailer")

# Process latest tags
@app.route("/rolling_emailer/<int:id>/run")
@roles_required('Admin')
def rolling_emailer(id):
    emailer = RollingEmailer.query.get(id)
    process_emailer.delay(emailer.to_dict())
    return redirect("/rolling_emailer")

@app.route("/rolling_emailer/<int:id>/delete")
@roles_required('Admin')
def rolling_emailer_delete(id):
    emailer = RollingEmailer.query.get(id)
    db.session.delete(emailer)
    db.session.commit()
    return redirect("/rolling_emailer")

@app.route("/rolling_emailer/hook/<string:webhook>")
def rolling_emailer_hook(webhook):
    emailer = RollingEmailer.query.filter_by(webhook=webhook).first()
    process_emailer.delay(emailer.to_dict())
    return emailer.to_dict(public=True)


if __name__ == "__main__":
    app.run(debug=True)
