#!/usr/bin/env python3
"""Run database migration in production environment."""
import os
import sys
import subprocess

def main():
    # Set up environment variables for Cloud SQL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    print(f"Running migration with DATABASE_URL: {database_url[:50]}...")

    try:
        # Run the alembic upgrade command
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True, cwd="/app")

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("Return code:", result.returncode)

        if result.returncode == 0:
            print("Migration completed successfully!")
        else:
            print("Migration failed!")
            sys.exit(1)

    except Exception as e:
        print(f"Error running migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()