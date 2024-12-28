import csv
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///telemetry.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

PASSWORD = os.getenv('PASSWORD')


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
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())


# Crear las tablas
with app.app_context():
    db.create_all()


def verify_password(data):
    if 'password' not in data or data['password'] != PASSWORD:
        return False
    return True


@app.route('/mods', methods=['POST'])
def create_mod():
    data = request.get_json()

    if not verify_password(data):
        return jsonify({"error": "Contraseña incorrecta"}), 403

    if not all(k in data for k in ("mod_id", "mod_name")):
        return jsonify({"error": "Faltan datos"}), 400

    if Mod.query.filter_by(mod_id=data['mod_id']).first():
        return jsonify({"error": "El mod ya existe"}), 400

    mod = Mod(mod_id=data['mod_id'], mod_name=data['mod_name'])
    db.session.add(mod)
    db.session.commit()

    return jsonify({"message": "Mod creado con éxito"}), 201


@app.route('/telemetry', methods=['POST'])
def receive_telemetry():
    data = request.get_json()

    if not all(k in data for k in ("game_version", "mod_id", "mod_version")):
        return jsonify({"error": "Faltan datos"}), 400

    mod = Mod.query.filter_by(mod_id=data['mod_id']).first()
    if not mod:
        return jsonify({"error": "El mod no existe"}), 404

    telemetry = Telemetry(
        game_version=data['game_version'],
        mod_version=data['mod_version'],
        mod_id=mod.id,
        usage_date=datetime.now(timezone.utc)
    )
    db.session.add(telemetry)
    db.session.commit()

    return jsonify({"message": "Datos guardados con éxito"}), 201


@app.route('/statistics/mods', methods=['GET'])
def get_most_used_mods():
    password = request.args.get('password')
    if password != PASSWORD:
        return jsonify({"error": "Contraseña incorrecta"}), 403

    results = db.session.query(Mod.mod_name, db.func.count(Telemetry.id).label('usage')) \
        .join(Telemetry, Mod.id == Telemetry.mod_id) \
        .group_by(Mod.mod_name) \
        .order_by(db.desc('usage')) \
        .all()

    return jsonify({"mods": [{"mod_name": r[0], "usage": r[1]} for r in results]}), 200


@app.route('/statistics/mod_versions/<mod_id>', methods=['GET'])
def get_most_used_mod_versions(mod_id):
    password = request.args.get('password')
    if password != PASSWORD:
        return jsonify({"error": "Contraseña incorrecta"}), 403

    mod = Mod.query.filter_by(mod_id=mod_id).first()
    if not mod:
        return jsonify({"error": "El mod no existe"}), 404

    results = db.session.query(Telemetry.mod_version, Telemetry.game_version,
                               db.func.count(Telemetry.mod_version).label('usage')) \
        .filter(Telemetry.mod_id == mod.id) \
        .group_by(Telemetry.mod_version, Telemetry.game_version) \
        .order_by(db.desc('usage')) \
        .all()

    return jsonify({"mod_versions": [{"mod_version": r[0], "game_version": r[1], "usage": r[2]} for r in results]}), 200


@app.route('/statistics/game_versions', methods=['GET'])
def get_most_used_game_versions():
    password = request.args.get('password')
    if password != PASSWORD:
        return jsonify({"error": "Contraseña incorrecta"}), 403

    results = db.session.query(Telemetry.game_version, db.func.count(Telemetry.game_version).label('usage')) \
        .group_by(Telemetry.game_version) \
        .order_by(db.desc('usage')) \
        .all()

    return jsonify({"game_versions": [{"game_version": r[0], "usage": r[1]} for r in results]}), 200


@app.route('/export/csv', methods=['GET'])
def export_to_csv():
    password = request.args.get('password')
    if password != PASSWORD:
        return jsonify({"error": "Contraseña incorrecta"}), 403

    filename = "telemetry_data.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["id", "game_version", "mod_id", "mod_version", "usage_date"])
        for telemetry in Telemetry.query.all():
            writer.writerow([
                telemetry.id,
                telemetry.game_version,
                Mod.query.get(telemetry.mod_id).mod_id,
                telemetry.mod_version,
                telemetry.usage_date
            ])

    return send_file(filename, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(debug=True)
