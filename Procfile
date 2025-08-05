# Procfile (for Heroku/Railway)
web: gunicorn app:app

# Modified app.py for cloud deployment
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

def get_db_connection():
    if USE_POSTGRES:
        # Parse DATABASE_URL for PostgreSQL
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        # Use SQLite for local development
        conn = sqlite3.connect('spending.db')
        conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # PostgreSQL schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                amount DECIMAL(10,2) NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#3498db'
            )
        ''')
        
        # Insert default categories
        default_categories = [
            ('Food & Dining', '#e74c3c'),
            ('Transportation', '#f39c12'),
            ('Shopping', '#9b59b6'),
            ('Entertainment', '#1abc9c'),
            ('Bills & Utilities', '#34495e'),
            ('Healthcare', '#e67e22'),
            ('Other', '#95a5a6')
        ]
        
        for category, color in default_categories:
            cursor.execute('''
                INSERT INTO categories (name, color) 
                VALUES (%s, %s) 
                ON CONFLICT (name) DO NOTHING
            ''', (category, color))
    else:
        # SQLite schema (same as original)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#3498db'
            )
        ''')
        
        default_categories = [
            ('Food & Dining', '#e74c3c'),
            ('Transportation', '#f39c12'),
            ('Shopping', '#9b59b6'),
            ('Entertainment', '#1abc9c'),
            ('Bills & Utilities', '#34495e'),
            ('Healthcare', '#e67e22'),
            ('Other', '#95a5a6')
        ]
        
        for category, color in default_categories:
            cursor.execute('INSERT OR IGNORE INTO categories (name, color) VALUES (?, ?)', (category, color))
    
    conn.commit()
    conn.close()

# Environment-specific configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DATABASE_URL = os.environ.get('DATABASE_URL')

# Production WSGI configuration
if __name__ == '__main__':
    init_db()
    # Use environment PORT or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# For deployment servers like Gunicorn
if __name__ != '__main__':
    init_db()
