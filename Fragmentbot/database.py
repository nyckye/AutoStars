import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_name="shop_bot.db"):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0,
                is_blocked BOOLEAN DEFAULT 0,
                is_welcomed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_daily_bonus TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                balance_amount REAL NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                used_by_user_id INTEGER,
                FOREIGN KEY (used_by_user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS star_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recipient_username TEXT NOT NULL,
                stars_amount INTEGER NOT NULL,
                balance_spent REAL NOT NULL,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                button_text TEXT NOT NULL,
                button_url TEXT,
                button_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name, last_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, first_name, last_name))
            cursor.execute("""
                UPDATE users 
                SET username = ?, first_name = ?, last_name = ?
                WHERE user_id = ?
            """, (username, first_name, last_name, user_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def set_welcomed(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_welcomed = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
    
    def is_user_welcomed(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_welcomed FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False
        finally:
            conn.close()
    
    def is_user_blocked(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False
        finally:
            conn.close()
    
    def block_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def unblock_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_balance(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return float(result[0]) if result else 0
        finally:
            conn.close()
    
    def add_balance(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
        finally:
            conn.close()
    
    def subtract_balance(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
        finally:
            conn.close()
    
    def can_claim_daily_bonus(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT last_daily_bonus FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                return True
            last_bonus = datetime.fromisoformat(result[0])
            return datetime.now() - last_bonus >= timedelta(days=1)
        finally:
            conn.close()
    
    def claim_daily_bonus(self, user_id, amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users 
                SET balance = balance + ?, last_daily_bonus = ?
                WHERE user_id = ?
            """, (amount, datetime.now(), user_id))
            conn.commit()
        finally:
            conn.close()
    
    def add_promo_code(self, code, balance_amount):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO promo_codes (code, balance_amount) VALUES (?, ?)", (code, balance_amount))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def check_promo_code(self, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT code, balance_amount, is_used FROM promo_codes WHERE code = ?", (code,))
            result = cursor.fetchone()
            if result:
                return {"code": result[0], "balance_amount": result[1], "is_used": bool(result[2])}
            return None
        finally:
            conn.close()
    
    def use_promo_code(self, code, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE promo_codes 
                SET is_used = 1, used_at = ?, used_by_user_id = ?
                WHERE code = ? AND is_used = 0
            """, (datetime.now(), user_id, code))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_promo_code(self, code):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM promo_codes WHERE code = ?", (code,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_all_promo_codes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT code, balance_amount, is_used, created_at, used_at, used_by_user_id 
                FROM promo_codes ORDER BY created_at DESC
            """)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def add_transaction(self, user_id, trans_type, amount, description):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            """, (user_id, trans_type, amount, description))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_user_transactions(self, user_id, trans_type=None, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if trans_type:
                cursor.execute("""
                    SELECT type, amount, description, created_at 
                    FROM transactions 
                    WHERE user_id = ? AND type = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (user_id, trans_type, limit))
            else:
                cursor.execute("""
                    SELECT type, amount, description, created_at 
                    FROM transactions 
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit))
            return cursor.fetchall()
        finally:
            conn.close()
    
    def add_star_purchase(self, user_id, recipient_username, stars_amount, balance_spent, tx_hash=None, status='pending'):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO star_purchases (user_id, recipient_username, stars_amount, balance_spent, tx_hash, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, recipient_username, stars_amount, balance_spent, tx_hash, status))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def update_star_purchase(self, purchase_id, tx_hash, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE star_purchases SET tx_hash = ?, status = ? WHERE id = ?", (tx_hash, status, purchase_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_user_star_purchases(self, user_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT recipient_username, stars_amount, balance_spent, status, created_at 
                FROM star_purchases 
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            return cursor.fetchall()
        finally:
            conn.close()
    
    def create_ticket(self, user_id, subject):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO tickets (user_id, subject) VALUES (?, ?)", (user_id, subject))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_user_open_ticket(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, subject, created_at 
                FROM tickets 
                WHERE user_id = ? AND status = 'open'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def get_user_tickets(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, subject, status, created_at 
                FROM tickets 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_ticket(self, ticket_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, user_id, subject, status, created_at FROM tickets WHERE id = ?", (ticket_id,))
            return cursor.fetchone()
        finally:
            conn.close()
    
    def close_ticket(self, ticket_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tickets SET status = 'closed', closed_at = ? WHERE id = ?", (datetime.now(), ticket_id))
            conn.commit()
        finally:
            conn.close()
    
    def add_ticket_message(self, ticket_id, user_id, message):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ticket_messages (ticket_id, user_id, message)
                VALUES (?, ?, ?)
            """, (ticket_id, user_id, message))
            conn.commit()
        finally:
            conn.close()
    
    def get_ticket_messages(self, ticket_id, limit=20):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT user_id, message, created_at 
                FROM ticket_messages 
                WHERE ticket_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (ticket_id, limit))
            results = cursor.fetchall()
            return list(reversed(results))
        finally:
            conn.close()
    
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, balance, is_blocked, created_at
                FROM users ORDER BY created_at DESC
            """)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
            blocked_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM promo_codes")
            total_codes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM promo_codes WHERE is_used = 1")
            used_codes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM star_purchases WHERE status = 'completed'")
            completed_purchases = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(stars_amount) FROM star_purchases WHERE status = 'completed'")
            total_stars = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(balance) FROM users")
            total_balance = cursor.fetchone()[0] or 0
            
            return {
                "total_users": total_users,
                "blocked_users": blocked_users,
                "total_codes": total_codes,
                "used_codes": used_codes,
                "completed_purchases": completed_purchases,
                "total_stars": total_stars,
                "total_balance": total_balance
            }
        finally:
            conn.close()
    
    def get_all_open_tickets(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t.id, t.user_id, t.subject, t.created_at, u.username, u.first_name
                FROM tickets t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.status = 'open'
                ORDER BY t.created_at DESC
            """)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def add_menu_button(self, button_text, button_url=None, button_order=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO menu_buttons (button_text, button_url, button_order)
                VALUES (?, ?, ?)
            """, (button_text, button_url, button_order))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_menu_buttons(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT id, button_text, button_url 
                FROM menu_buttons 
                WHERE is_active = 1 
                ORDER BY button_order
            """)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def delete_menu_button(self, button_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM menu_buttons WHERE id = ?", (button_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def set_setting(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (key, value))
            conn.commit()
        finally:
            conn.close()
    
    def get_setting(self, key, default=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
        finally:
            conn.close()
