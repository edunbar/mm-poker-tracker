# Backend README.md

# Poker Analytics App - Backend

This is the backend part of the Poker Analytics App, which is built using Flask and PostgreSQL. The backend handles API requests and interacts with the database to manage game data.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [Contributing](#contributing)

## Installation

2. Create a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Set up the database:
   - Update the database connection settings in `src/config.py`.
   - Run the necessary migrations to create the database schema.

## Usage

To run the backend application, execute the following command:

```
python src/app.py
```

The application will start on `http://localhost:5000` by default.

## API Endpoints

- `POST /api/game`: Submit a new game ID.
- `GET /api/game`: Retrieve game data.

## Database Models

The database models are defined in `src/db/models.py`. They represent the structure of the database tables and their relationships.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.
