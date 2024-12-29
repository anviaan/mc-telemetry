# Telemetry API

## Description

This project is a Flask-based API for managing telemetry data of game mods. It allows you to create mods, receive
telemetry data, and retrieve statistics about mod and game version usage.

## Installation

1. Clone the repository:
    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file and set the `PASSWORD` environment variable:
    ```sh
    echo "PASSWORD=your_password" > .env
    ```

5. Run the application:
    ```sh
    python app.py
    ```

## Usage

The API provides the following endpoints:

### Create a Mod

- **URL:** `/mods`
- **Method:** `POST`
- **Body:**
    ```json
    {
        "password": "your_password",
        "mod_id": "mod123",
        "mod_name": "Example Mod"
    }
    ```
- **Response:**
    ```json
    {
        "message": "Mod created successfully"
    }
    ```

### Receive Telemetry Data

- **URL:** `/telemetry`
- **Method:** `POST`
- **Body:**
    ```json
    {
        "mod_id": "mod123",
        "game_version": "1.0",
        "mod_version": "1.0"
    }
    ```
- **Response:**
    ```json
    {
        "message": "Data saved successfully"
    }
    ```

### Get Most Used Mods

- **URL:** `/statistics/mods`
- **Method:** `GET`
- **Query Parameters:** `password`
- **Response:**
    ```json
    {
        "mods": [
            {
                "mod_name": "Example Mod",
                "usage": 10
            }
        ]
    }
    ```

### Get Most Used Mod Versions

- **URL:** `/statistics/mod_versions/<mod_id>`
- **Method:** `GET`
- **Query Parameters:** `password`
- **Response:**
    ```json
    {
        "mod_versions": [
            {
                "mod_version": "1.0",
                "game_version": "1.0",
                "usage": 5
            }
        ]
    }
    ```

### Get Most Used Game Versions

- **URL:** `/statistics/game_versions`
- **Method:** `GET`
- **Query Parameters:** `password`
- **Response:**
    ```json
    {
        "game_versions": [
            {
                "game_version": "1.0",
                "usage": 10
            }
        ]
    }
    ```

### Export Telemetry Data to CSV

- **URL:** `/export/csv`
- **Method:** `GET`
- **Query Parameters:** `password`
- **Response:** CSV file download

## License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for more information.
