import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='shop.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            created_at TEXT
        )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            stock INTEGER DEFAULT 0
        )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            price INTEGER,
            purchase_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS product_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            key_data TEXT,
            is_sold INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        
        self.connection.commit()
    
    def add_user(self, user_id, username):
        self.cursor.execute('INSERT OR IGNORE INTO users VALUES (?, ?, 0, ?)',
                          (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.connection.commit()
    
    def get_user(self, user_id):
        return self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    
    def add_product(self, name, description, price):
        self.cursor.execute('INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, 0)',
                          (name, description, price))
        self.connection.commit()
        return self.cursor.lastrowid
    
    def get_all_products(self):
        return self.cursor.execute('SELECT * FROM products').fetchall()
    
    def get_product(self, product_id):
        return self.cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    def delete_product(self, product_id):
        self.cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        self.cursor.execute('DELETE FROM product_keys WHERE product_id = ?', (product_id,))
        self.connection.commit()
    
    def add_product_key(self, product_id, key_data):
        self.cursor.execute('INSERT INTO product_keys (product_id, key_data) VALUES (?, ?)',
                          (product_id, key_data))
        self.cursor.execute('UPDATE products SET stock = stock + 1 WHERE id = ?', (product_id,))
        self.connection.commit()
    
    def get_available_key(self, product_id):
        key = self.cursor.execute(
            'SELECT * FROM product_keys WHERE product_id = ? AND is_sold = 0 LIMIT 1',
            (product_id,)
        ).fetchone()
        return key
    
    def mark_key_sold(self, key_id):
        self.cursor.execute('UPDATE product_keys SET is_sold = 1 WHERE id = ?', (key_id,))
        self.connection.commit()
    
    def add_purchase(self, user_id, product_id, price):
        self.cursor.execute('INSERT INTO purchases (user_id, product_id, price, purchase_date) VALUES (?, ?, ?, ?)',
                          (user_id, product_id, price, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.connection.commit()
    
    def get_stats(self):
        total_users = self.cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_purchases = self.cursor.execute('SELECT COUNT(*) FROM purchases').fetchone()[0]
        total_revenue = self.cursor.execute('SELECT SUM(price) FROM purchases').fetchone()[0] or 0
        return total_users, total_purchases, total_revenue
    
    def get_user_purchases(self, user_id):
        return self.cursor.execute('''
            SELECT p.name, pur.price, pur.purchase_date 
            FROM purchases pur 
            JOIN products p ON pur.product_id = p.id 
            WHERE pur.user_id = ?
            ORDER BY pur.purchase_date DESC
        ''', (user_id,)).fetchall()

db = Database()
