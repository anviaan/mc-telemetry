import csv
import os
from datetime import datetime, timezone
from functools import wraps
from typing import Dict, Any

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

app = Flask(__name__)
# Handle reverse proxies correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


# Configuration
class Config:
    MYSQL_USERNAME = os.getenv('MYSQL_USERNAME', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'mc-telemetry')
    API_PASSWORD = os.getenv('PASSWORD', 'password')  # renamed for clarity

    # Additional configurations
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'

    # Add rate limiting configs
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"


app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Mod(db.Model):
    __tablename__ = 'mods'

    id = db.Column(db.Integer, primary_key=True)
    mod_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    mod_name = db.Column(db.String(100), nullable=False)
    telemetry = db.relationship('Telemetry', backref='mod', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'mod_id': self.mod_id,
            'mod_name': self.mod_name
        }


class Telemetry(db.Model):
    __tablename__ = 'telemetry'

    mod_id = db.Column(db.Integer, db.ForeignKey('mods.id', ondelete='CASCADE'), primary_key=True)
    game_version = db.Column(db.String(10), primary_key=True)
    mod_version = db.Column(db.String(10), primary_key=True)
    loader = db.Column(db.String(25), primary_key=True)
    count = db.Column(db.BigInteger, nullable=False, default=0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mod_id': self.mod_id,
            'game_version': self.game_version,
            'mod_version': self.mod_version,
            'loader': self.loader,
            'count': self.count
        }


# Authentication decorator
def require_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        password = request.args.get('password') or (request.get_json() or {}).get('password')
        if not password or password != app.config['API_PASSWORD']:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)

    return decorated_function


# Error handler
@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"An error occurred: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/telemetry', methods=['GET'])
def index() -> Response:
    return send_from_directory('static', 'index.html')


@app.route('/telemetry/health', methods=['GET'])
def health_check() -> tuple[Response, int]:
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': 'connected' if db.session.is_active else 'disconnected'
    }), 200


@app.route('/telemetry/mods', methods=['GET'])
def get_mods() -> tuple[Response, int]:
    try:
        mods = Mod.query.all()
        return jsonify({
            'mods': [mod.to_dict() for mod in mods],
            'count': len(mods)
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching mods: {e}")
        return jsonify({'error': 'Failed to fetch mods'}), 500


@app.route('/telemetry/mods', methods=['POST'])
@require_password
def create_mod() -> tuple[Response, int]:
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("mod_id", "mod_name")):
            return jsonify({'error': 'Missing required fields'}), 400

        mod = Mod(mod_id=data['mod_id'], mod_name=data['mod_name'])
        db.session.add(mod)
        db.session.commit()

        return jsonify({
            'message': 'Mod created successfully',
            'mod': mod.to_dict()
        }), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Mod already exists'}), 409
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating mod: {e}")
        return jsonify({'error': 'Failed to create mod'}), 500


@app.route('/telemetry/data', methods=['POST'])
def receive_telemetry() -> tuple[Response, int]:
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ("game_version", "mod_id", "mod_version", "loader")):
            return jsonify({'error': 'Missing required fields'}), 400

        mod = Mod.query.filter_by(mod_id=data['mod_id']).first()
        if not mod:
            return jsonify({'error': 'Mod not found'}), 404

        telemetry = Telemetry.query.filter_by(
            game_version=data['game_version'],
            mod_version=data['mod_version'],
            mod_id=mod.id,
            loader=data['loader']
        ).first()

        if telemetry:
            telemetry.count += 1
        else:
            telemetry = Telemetry(
                game_version=data['game_version'],
                mod_version=data['mod_version'],
                mod_id=mod.id,
                loader=data['loader'],
                count=1
            )
            db.session.add(telemetry)

        db.session.commit()

        return jsonify({
            'message': 'Telemetry data saved successfully',
            'telemetry': telemetry.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving telemetry: {e}")
        return jsonify({'error': 'Failed to save telemetry data'}), 500


@app.route('/telemetry/export/csv', methods=['GET'])
@require_password
def export_to_csv() -> Response | tuple[Response, int]:
    temp_file = None
    try:
        filename = f"telemetry_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        temp_dir = os.path.join(os.getcwd(), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, filename)

        with open(temp_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "mod_id", "game_version", "mod_version", "loader", "count"
            ])

            telemetry_data = Telemetry.query.all()

            for telemetry in telemetry_data:
                writer.writerow([
                    telemetry.mod_id,
                    telemetry.game_version,
                    telemetry.mod_version,
                    telemetry.loader,
                    telemetry.count
                ])

        response = send_file(
            temp_file,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )

        # Add headers to prevent caching
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'

        # Register a callback to delete the file after sending
        @response.call_on_close
        def cleanup():
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    app.logger.error(f"Failed to remove temporary file: {temp_file}")

        return response

    except Exception as e:
        # Clean up the file if there's an error
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass  # Ignore errors during cleanup
        app.logger.error(f"Error exporting CSV: {e}")
        return jsonify({'error': 'Failed to export data'}), 500


if __name__ == '__main__':
    app.run(debug=True)
