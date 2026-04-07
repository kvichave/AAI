"""
Creates a sample SQLite database with realistic data for demo purposes.

Tables:
  • orders       – e-commerce orders with timestamps
  • products     – product catalogue
  • customers    – customer profiles
  • page_views   – website traffic time-series

Run:  python seed_demo_db.py
      -> creates ./data/demo.db
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "demo.db")


def seed(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────────
    c.executescript("""
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS page_views;

        CREATE TABLE products (
            id          INTEGER PRIMARY KEY,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            price       REAL    NOT NULL
        );

        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            country     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            product_id  INTEGER REFERENCES products(id),
            quantity    INTEGER NOT NULL,
            total       REAL    NOT NULL,
            status      TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE page_views (
            id          INTEGER PRIMARY KEY,
            page        TEXT    NOT NULL,
            country     TEXT    NOT NULL,
            device      TEXT    NOT NULL,
            viewed_at   TEXT    NOT NULL
        );
    """)

    # ── Products ──────────────────────────────────────────────────────────────
    products = [
        ("Wireless Headphones", "Electronics", 79.99),
        ("Mechanical Keyboard",  "Electronics", 129.99),
        ("USB-C Hub",            "Electronics",  49.99),
        ("Running Shoes",        "Apparel",       89.99),
        ("Yoga Mat",             "Sports",        35.00),
        ("Coffee Maker",         "Kitchen",       59.99),
        ("Desk Lamp",            "Office",        39.99),
        ("Backpack",             "Apparel",       69.99),
        ("Water Bottle",         "Sports",        24.99),
        ("Notebook Set",         "Office",        14.99),
    ]
    c.executemany("INSERT INTO products (name, category, price) VALUES (?,?,?)", products)

    # ── Customers ─────────────────────────────────────────────────────────────
    countries = ["US", "UK", "DE", "IN", "CA", "AU", "FR", "JP"]
    base_date = datetime(2024, 1, 1)
    customers = []
    for i in range(1, 201):
        joined = base_date + timedelta(days=random.randint(0, 365))
        customers.append((
            f"Customer {i}",
            f"user{i}@example.com",
            random.choice(countries),
            joined.strftime("%Y-%m-%d"),
        ))
    c.executemany(
        "INSERT INTO customers (name, email, country, created_at) VALUES (?,?,?,?)",
        customers,
    )

    # ── Orders ────────────────────────────────────────────────────────────────
    statuses = ["completed", "completed", "completed", "pending", "cancelled"]
    orders = []
    for _ in range(1000):
        prod_id  = random.randint(1, 10)
        price    = products[prod_id - 1][2]
        qty      = random.randint(1, 5)
        dt       = base_date + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        orders.append((
            random.randint(1, 200),
            prod_id,
            qty,
            round(price * qty, 2),
            random.choice(statuses),
            dt.strftime("%Y-%m-%d %H:%M:%S"),
        ))
    c.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, total, status, created_at) VALUES (?,?,?,?,?,?)",
        orders,
    )

    # ── Page views ────────────────────────────────────────────────────────────
    pages   = ["/", "/products", "/about", "/checkout", "/blog"]
    devices = ["desktop", "mobile", "tablet"]
    views   = []
    for _ in range(5000):
        dt = base_date + timedelta(
            days=random.randint(0, 364),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        views.append((
            random.choice(pages),
            random.choice(countries),
            random.choice(devices),
            dt.strftime("%Y-%m-%d %H:%M:%S"),
        ))
    c.executemany(
        "INSERT INTO page_views (page, country, device, viewed_at) VALUES (?,?,?,?)",
        views,
    )

    conn.commit()
    conn.close()
    print(f"[OK] Demo database created at: {db_path}")
    print("     Tables: products, customers, orders, page_views")


if __name__ == "__main__":
    seed()