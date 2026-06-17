import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv(override=False)

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = os.getenv("MYSQL_PORT", "3306")
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DB", "restaurant_concierge")
        
        self._initialize_db()

    def _get_connection(self, include_db=True):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database if include_db else None
        )

    def _initialize_db(self):
        try:
            conn = self._get_connection(include_db=False)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            cursor.close()
            conn.close()

            conn = self._get_connection(include_db=True)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NULL,
                    telegram_id VARCHAR(100) UNIQUE NOT NULL,
                    phone_number VARCHAR(50) NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR(50) PRIMARY KEY,
                    customer_id INT NOT NULL,
                    items TEXT NOT NULL,
                    status VARCHAR(50) DEFAULT 'Received',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id VARCHAR(50) PRIMARY KEY,
                    customer_id INT NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    guest_count INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT NOT NULL,
                    rating INT NOT NULL,
                    review TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Error:
            pass

    def get_or_create_customer(self, telegram_id: str, phone_number: str = None) -> int:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT customer_id FROM customers WHERE telegram_id = %s", (telegram_id,))
            result = cursor.fetchone()
            
            if result:
                customer_id = result[0]
                if phone_number:
                    cursor.execute(
                        "UPDATE customers SET phone_number = %s WHERE customer_id = %s AND phone_number IS NULL",
                        (phone_number, customer_id)
                    )
                    conn.commit()
                cursor.close()
                conn.close()
                return customer_id
            
            query = "INSERT INTO customers (telegram_id, phone_number) VALUES (%s, %s)"
            cursor.execute(query, (telegram_id, phone_number))
            conn.commit()
            
            new_id = cursor.lastrowid
            cursor.close()
            conn.close()
            return new_id
            
        except Error:
            return 0