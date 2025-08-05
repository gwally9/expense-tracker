from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# Database setup
def init_db():
    conn = sqlite3.connect('spending.db')
    cursor = conn.cursor()
    
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
    
    # Insert default categories if they don't exist
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

def get_db_connection():
    conn = sqlite3.connect('spending.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    
    # Get recent expenses
    recent_expenses = conn.execute('''
        SELECT e.*, c.color 
        FROM expenses e 
        LEFT JOIN categories c ON e.category = c.name 
        ORDER BY e.date DESC, e.created_at DESC 
        LIMIT 10
    ''').fetchall()
    
    # Get spending summary for current month
    current_month = datetime.now().strftime('%Y-%m')
    monthly_total = conn.execute('''
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM expenses 
        WHERE strftime('%Y-%m', date) = ?
    ''', (current_month,)).fetchone()['total']
    
    # Get category totals for current month
    category_totals = conn.execute('''
        SELECT e.category, SUM(e.amount) as total, c.color
        FROM expenses e
        LEFT JOIN categories c ON e.category = c.name
        WHERE strftime('%Y-%m', e.date) = ?
        GROUP BY e.category
        ORDER BY total DESC
    ''', (current_month,)).fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                         recent_expenses=recent_expenses,
                         monthly_total=monthly_total,
                         category_totals=category_totals,
                         current_month=datetime.now().strftime('%B %Y'))

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        description = request.form['description']
        date = request.form['date']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO expenses (amount, category, description, date)
            VALUES (?, ?, ?, ?)
        ''', (amount, category, description, date))
        conn.commit()
        conn.close()
        
        flash('Expense added successfully!', 'success')
        return redirect(url_for('index'))
    
    # Get categories for the form
    conn = get_db_connection()
    categories = conn.execute('SELECT name FROM categories ORDER BY name').fetchall()
    conn.close()
    
    return render_template('add_expense.html', 
                         categories=categories,
                         today=datetime.now().date())

@app.route('/expenses')
def expenses():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get filter parameters
    category_filter = request.args.get('category', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    conn = get_db_connection()
    
    # Build query with filters
    query = '''
        SELECT e.*, c.color 
        FROM expenses e 
        LEFT JOIN categories c ON e.category = c.name 
        WHERE 1=1
    '''
    params = []
    
    if category_filter:
        query += ' AND e.category = ?'
        params.append(category_filter)
    
    if date_from:
        query += ' AND e.date >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND e.date <= ?'
        params.append(date_to)
    
    query += ' ORDER BY e.date DESC, e.created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    expenses = conn.execute(query, params).fetchall()
    
    # Get total count for pagination
    count_query = 'SELECT COUNT(*) as count FROM expenses WHERE 1=1'
    count_params = []
    
    if category_filter:
        count_query += ' AND category = ?'
        count_params.append(category_filter)
    
    if date_from:
        count_query += ' AND date >= ?'
        count_params.append(date_from)
    
    if date_to:
        count_query += ' AND date <= ?'
        count_params.append(date_to)
    
    total_count = conn.execute(count_query, count_params).fetchone()['count']
    
    # Get categories for filter dropdown
    categories = conn.execute('SELECT name FROM categories ORDER BY name').fetchall()
    
    conn.close()
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('expenses.html',
                         expenses=expenses,
                         categories=categories,
                         page=page,
                         total_pages=total_pages,
                         has_prev=has_prev,
                         has_next=has_next,
                         category_filter=category_filter,
                         date_from=date_from,
                         date_to=date_to)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    
    flash('Expense deleted successfully!', 'success')
    return redirect(request.referrer or url_for('expenses'))

@app.route('/analytics')
def analytics():
    conn = get_db_connection()
    
    # Get monthly spending for the last 6 months
    monthly_data = conn.execute('''
        SELECT strftime('%Y-%m', date) as month,
               SUM(amount) as total
        FROM expenses
        WHERE date >= date('now', '-6 months')
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    ''').fetchall()
    
    # Get category breakdown for current month
    current_month = datetime.now().strftime('%Y-%m')
    category_data = conn.execute('''
        SELECT category, SUM(amount) as total, AVG(amount) as avg_amount, COUNT(*) as count
        FROM expenses
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    ''', (current_month,)).fetchall()
    
    # Get daily spending for current month
    daily_data = conn.execute('''
        SELECT date, SUM(amount) as total
        FROM expenses
        WHERE strftime('%Y-%m', date) = ?
        GROUP BY date
        ORDER BY date
    ''', (current_month,)).fetchall()
    
    conn.close()
    
    return render_template('analytics.html',
                         monthly_data=monthly_data,
                         category_data=category_data,
                         daily_data=daily_data,
                         current_month=datetime.now().strftime('%B %Y'))

# API endpoints for charts
@app.route('/api/monthly_data')
def api_monthly_data():
    conn = get_db_connection()
    data = conn.execute('''
        SELECT strftime('%Y-%m', date) as month,
               SUM(amount) as total
        FROM expenses
        WHERE date >= date('now', '-6 months')
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in data])

@app.route('/api/category_data')
def api_category_data():
    current_month = datetime.now().strftime('%Y-%m')
    conn = get_db_connection()
    data = conn.execute('''
        SELECT e.category, SUM(e.amount) as total, c.color
        FROM expenses e
        LEFT JOIN categories c ON e.category = c.name
        WHERE strftime('%Y-%m', e.date) = ?
        GROUP BY e.category
        ORDER BY total DESC
    ''', (current_month,)).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in data])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

# HTML Templates (create these files in a 'templates' folder)

# templates/base.html
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spending Tracker</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .category-badge {
            border-radius: 20px;
            padding: 5px 12px;
            color: white;
            font-weight: 500;
        }
        .expense-card {
            transition: transform 0.2s;
        }
        .expense-card:hover {
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-wallet me-2"></i>Spending Tracker
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('index') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('add_expense') }}">Add Expense</a>
                <a class="nav-link" href="{{ url_for('expenses') }}">All Expenses</a>
                <a class="nav-link" href="{{ url_for('analytics') }}">Analytics</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Save this as a complete Flask application
# You'll need to create the templates folder and save the HTML templates separately