@echo off
REM Initialize Study Sprint Database
REM This script creates the database schema using SQLite

echo Creating Study Sprint database...
sqlite3 education_app.db < create_database.sql

if %ERRORLEVEL% EQU 0 (
    echo Database created successfully: education_app.db
) else (
    echo Error creating database. Make sure SQLite is installed and in your PATH.
    echo You can download SQLite from https://www.sqlite.org/download.html
)

pause
