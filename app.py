import csv
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
username = os.getenv('MYSQL_USERNAME', 'root')
password = os.getenv('MYSQL_PASSWORD', 'root')
host = os.getenv('MYSQL_HOST', 'localhost')
port = os.getenv('MYSQL_PORT', '3306')
database = os.getenv('MYSQL_DATABASE', 'mc-telemetry')
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

PASSWORD = os.getenv('PASSWORD', 'password')

class Mod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mod_id = db.Column(db.String(50), unique=True, nullable=False)
    mod_name = db.Column(db.String(100), nullable=False)
    telemetry = db.relationship('Telemetry', backref='mod', lazy=True)


class Telemetry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mod_id = db.Column(db.Integer, db.ForeignKey('mod.id'), nullable=False)
    game_version = db.Column(db.String(10), nullable=False)
    mod_version = db.Column(db.String(10), nullable=False)
    loader = db.Column(db.String(25), nullable=False)
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())


with app.app_context():
    db.create_all()


def verify_password(data):
    if 'password' not in data or data['password'] != PASSWORD:
        return False
    return True


@app.route('/telemetry', methods=['GET'])
def index():
    return send_from_directory('static', 'index.html')


@app.route('/telemetry/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Service is up and running"}), 200


@app.route('/telemetry/mods', methods=['GET'])
def get_mods():
    mods = Mod.query.all()
    return jsonify({"mods": [{"mod_id": mod.mod_id, "mod_name": mod.mod_name} for mod in mods]}), 200


@app.route('/telemetry/mods', methods=['POST'])
def create_mod():
    data = request.get_json()

    if not verify_password(data):
        return jsonify({"error": "Incorrect password"}), 403

    if not all(k in data for k in ("mod_id", "mod_name")):
        return jsonify({"error": "Missing data"}), 400

    if Mod.query.filter_by(mod_id=data['mod_id']).first():
        return jsonify({"error": "Mod already exists"}), 400

    mod = Mod(mod_id=data['mod_id'], mod_name=data['mod_name'])
    db.session.add(mod)
    db.session.commit()

    return jsonify({"message": "Mod created successfully"}), 201


@app.route('/telemetry/data', methods=['POST'])
def receive_telemetry():
    data = request.get_json()

    if not all(k in data for k in ("game_version", "mod_id", "mod_version", "loader")):
        return jsonify({"error": "Missing data"}), 400

    mod = Mod.query.filter_by(mod_id=data['mod_id']).first()
    if not mod:
        return jsonify({"error": "Mod does not exist"}), 404

    telemetry = Telemetry(
        game_version=data['game_version'],
        mod_version=data['mod_version'],
        mod_id=mod.id,
        usage_date=datetime.now(timezone.utc),
        loader=data['loader']
    )
    db.session.add(telemetry)
    db.session.commit()

    return jsonify({"message": "Data saved successfully"}), 201


@app.route('/telemetry/export/csv', methods=['GET'])
def export_to_csv():
    password = request.args.get('password')
    if password != PASSWORD:
        return jsonify({"error": "Incorrect password"}), 403

    filename = "telemetry_data.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["id", "game_version", "mod_id", "mod_version", "loader", "usage_date"])
        for telemetry in Telemetry.query.all():
            writer.writerow([
                telemetry.id,
                telemetry.game_version,
                Mod.query.get(telemetry.mod_id).mod_id,
                telemetry.mod_version,
                telemetry.loader,
                telemetry.usage_date.strftime('%Y-%m-%d')
            ])

    return send_file(filename, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(debug=True)
