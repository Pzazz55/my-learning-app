-- Study Sprint Database Schema
-- This script creates the database tables for the Study Sprint education app
-- Run this script to manually create the database schema
-- Usage: sqlite3 education_app.db < create_database.sql

-- Create exams table
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    country TEXT NOT NULL,
    subject TEXT NOT NULL,
    question_count INTEGER NOT NULL,
    time_limit INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    score INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    wrong_count INTEGER NOT NULL,
    questions_json TEXT NOT NULL,
    school_state TEXT NOT NULL DEFAULT '',
    school_district TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    question_set_id INTEGER
);

-- Create question_sets table
CREATE TABLE IF NOT EXISTS question_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_exams_student_name ON exams(student_name);
CREATE INDEX IF NOT EXISTS idx_exams_grade ON exams(grade);
CREATE INDEX IF NOT EXISTS idx_exams_subject ON exams(subject);
CREATE INDEX IF NOT EXISTS idx_exams_topic ON exams(topic);
CREATE INDEX IF NOT EXISTS idx_exams_school_district ON exams(school_district);
CREATE INDEX IF NOT EXISTS idx_exams_question_set_id ON exams(question_set_id);
CREATE INDEX IF NOT EXISTS idx_question_sets_student_name ON question_sets(student_name);
CREATE INDEX IF NOT EXISTS idx_question_sets_grade ON question_sets(grade);
CREATE INDEX IF NOT EXISTS idx_question_sets_subject ON question_sets(subject);
CREATE INDEX IF NOT EXISTS idx_question_sets_topic ON question_sets(topic);
