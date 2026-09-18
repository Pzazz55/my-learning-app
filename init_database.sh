#!/bin/bash
# Initialize Study Sprint Database
# This script creates the database schema using SQLite

echo "Creating Study Sprint database..."
sqlite3 education_app.db < create_database.sql

if [ $? -eq 0 ]; then
    echo "Database created successfully: education_app.db"
else
    echo "Error creating database. Make sure SQLite is installed and in your PATH."
    echo "On Ubuntu/Debian: sudo apt-get install sqlite3"
    echo "On macOS: brew install sqlite"
fi
