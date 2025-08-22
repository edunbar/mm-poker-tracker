# Poker Analytics App

## Overview
The Poker Analytics App is a web application designed to submit and analyze PokerNow game IDs. It consists of a backend built with Flask and a frontend developed using React. The application utilizes PostgreSQL as the database and React Query for efficient data fetching and state management.

## Project Structure
```
poker-analytics-app
├── backend
│   ├── src
│   │   ├── app.py
│   │   ├── db
│   │   │   └── models.py
│   │   ├── routes
│   │   │   └── game.py
│   │   └── config.py
│   ├── requirements.txt
│   └── README.md
├── frontend
│   ├── src
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── api
│   │   │   └── game.ts
│   │   ├── components
│   │   │   └── GameForm.tsx
│   │   └── hooks
│   │       └── useGameQuery.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── README.md
├── README.md
└── docker-compose.yml
```

## Backend
The backend is responsible for handling API requests and interacting with the PostgreSQL database. It is structured as follows:

- **app.py**: Entry point of the backend application.
- **db/models.py**: Defines the database models using SQLAlchemy.
- **routes/game.py**: Contains route definitions for game-related endpoints.
- **config.py**: Configuration settings for the application.
- **requirements.txt**: Lists the Python dependencies required for the backend.

## Frontend
The frontend is a React application that provides a user interface for submitting game IDs and viewing analytics. It includes:

- **App.tsx**: Main component that sets up routing and layout.
- **index.tsx**: Entry point of the React application.
- **api/game.ts**: Functions to interact with the backend API.
- **components/GameForm.tsx**: Component for submitting game IDs.
- **hooks/useGameQuery.ts**: Custom hook for fetching game data using React Query.

## Setup Instructions

### Backend
1. Navigate to the `backend` directory.
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up the PostgreSQL database and update the configuration in `config.py`.
4. Run the backend application:
   ```
   python src/app.py
   ```

### Frontend
1. Navigate to the `frontend` directory.
2. Install the required dependencies:
   ```
   npm install
   ```
3. Start the React application:
   ```
   npm start
   ```

## Docker
To run the application using Docker, use the `docker-compose.yml` file to set up the services. Run the following command in the root directory:
```
docker-compose up
```

## License
This project is licensed under the MIT License.