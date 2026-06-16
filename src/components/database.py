import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv(override=False)

class DatabaseManager:
    """
    Central manager for all MySQL database operations.
    Handles connection creation, table verification, and basic data persistence.
    """
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = os.getenv("MYSQL_PORT", "3306")
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DB", "restaurant_concierge")
        
        # Automatically verify and create the database and tables upon initialization
        self._initialize_db()

    def _get_connection(self, include_db=True):
        """Helper method to establish a live connection to the MySQL server."""
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database if include_db else None
        )

    def _initialize_db(self):
        """Initial check to build the database and operational tables if they do not exist."""
        try:
            conn = self._get_connection(include_db=False)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            conn.commit()
            cursor.close()
            conn.close()

            conn = self._get_connection(include_db=True)
            cursor = conn.cursor()
            
            # 1. Customers Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NULL,
                    telegram_id VARCHAR(100) UNIQUE NOT NULL,
                    phone_number VARCHAR(50) NULL
                )
            """)
            
            # 2. Orders Table
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
            
            # 3. Reservations Table
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
            
            # 4. Feedback Table
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
            print("✅ MySQL Database & Tables completely ready!")
            
        except Error as e:
            print(f"❌ Database initialization error: {e}")

    # --- CUSTOMER MANAGEMENT WORKFLOW ---
    def get_or_create_customer(self, telegram_id: str, phone_number: str = None) -> int:
        """
        Looks up a customer profile using their Telegram ID.
        Returns the existing customer_id if found, otherwise registers a new entry.
        """
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
            
            new_id = cursor.lastrowid  # Retrieve the newly generated auto-increment record ID
            cursor.close()
            conn.close()
            return new_id
            
        except Error as e:
            print(f"❌ Error processing customer record: {e}")
            return 0