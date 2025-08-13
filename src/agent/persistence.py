import sqlite3


def create_grepo_tables(cursor):
    grepo_db_con = sqlite3.connect("grepo.db")
    grepo_db_con.execute("PRAGMA foreign_keys = ON;")

    cursor = grepo_db_con.cursor()

    # Table for `classes`
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        start_line INTEGER,
        end_line INTEGER,
        meta_info TEXT NOT NULL,
        hash TEXT NOT NULL
        ) STRICT;

        """)

    # Table for `methods`
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS methods (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        start_line INTEGER,
        end_line INTEGER,
        meta_info TEXT NOT NULL,
        hash TEXT NOT NULL

        FOREIGN KEY (class_id)
            REFERENCES classes(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
        ) STRICT;

        """)

    # Table for `functions`
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS functions (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        start_line INTEGER,
        end_line INTEGER,
        meta_info TEXT NOT NULL,
        hash TEXT NOT NULL
        ) STRICT;

        """)

    # Table for global 'references' of class,method or function
    # ----- TODO: Think more on how to do this? -----
    return
