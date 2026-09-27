import sqlite3
from pathlib import Path


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "documind.db"


# ============================================================
# HELPERS
# ============================================================

def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    cursor = connection.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    return any(
        column[1] == column_name
        for column in columns
    )


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    cursor = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table_name,),
    )

    return cursor.fetchone() is not None


# ============================================================
# MIGRATION
# ============================================================

def migrate():
    print("=" * 70)
    print("DOCUMIND AI AUTHENTICATION DATABASE MIGRATION")
    print("=" * 70)

    if not DATABASE_PATH.exists():
        print()
        print("ERROR: documind.db was not found.")
        print("Expected location:")
        print(DATABASE_PATH)
        print()
        return

    print()
    print("Database:")
    print(DATABASE_PATH)
    print()

    connection = sqlite3.connect(
        str(DATABASE_PATH)
    )

    try:
        # ----------------------------------------------------
        # Enable foreign keys
        # ----------------------------------------------------

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        if not table_exists(
            connection,
            "users",
        ):
            print("Creating users table...")

            connection.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    created_at DATETIME
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX ix_users_id
                ON users (id)
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX ix_users_username
                ON users (username)
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX ix_users_email
                ON users (email)
                """
            )

            print("✓ users table created.")

        else:
            print("✓ users table already exists.")

        # ----------------------------------------------------
        # DOCUMENTS.USER_ID
        # ----------------------------------------------------

        if not column_exists(
            connection,
            "documents",
            "user_id",
        ):
            print("Adding documents.user_id...")

            connection.execute(
                """
                ALTER TABLE documents
                ADD COLUMN user_id INTEGER
                """
            )

            connection.execute(
                """
                CREATE INDEX ix_documents_user_id
                ON documents (user_id)
                """
            )

            print("✓ documents.user_id added.")

        else:
            print(
                "✓ documents.user_id already exists."
            )

        # ----------------------------------------------------
        # CHAT_SESSIONS.USER_ID
        # ----------------------------------------------------

        if not column_exists(
            connection,
            "chat_sessions",
            "user_id",
        ):
            print("Adding chat_sessions.user_id...")

            connection.execute(
                """
                ALTER TABLE chat_sessions
                ADD COLUMN user_id INTEGER
                """
            )

            connection.execute(
                """
                CREATE INDEX ix_chat_sessions_user_id
                ON chat_sessions (user_id)
                """
            )

            print(
                "✓ chat_sessions.user_id added."
            )

        else:
            print(
                "✓ chat_sessions.user_id already exists."
            )

        # ----------------------------------------------------
        # COMMIT
        # ----------------------------------------------------

        connection.commit()

        print()
        print("=" * 70)
        print("MIGRATION SUCCESSFUL")
        print("=" * 70)

        # ----------------------------------------------------
        # VERIFY
        # ----------------------------------------------------

        print()
        print("Verification:")

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        print()
        print("Tables:")

        for table in tables:
            print(f"  ✓ {table[0]}")

        print()

        document_count = connection.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]

        chunk_count = connection.execute(
            "SELECT COUNT(*) FROM document_chunks"
        ).fetchone()[0]

        chat_count = connection.execute(
            "SELECT COUNT(*) FROM chat_sessions"
        ).fetchone()[0]

        user_count = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        print(
            f"Users:           {user_count}"
        )

        print(
            f"Documents:       {document_count}"
        )

        print(
            f"Document chunks: {chunk_count}"
        )

        print(
            f"Chat sessions:   {chat_count}"
        )

        print()
        print(
            "Your existing documents and embeddings "
            "were preserved."
        )

    except Exception as error:

        connection.rollback()

        print()
        print("=" * 70)
        print("MIGRATION FAILED")
        print("=" * 70)

        print()
        print(
            "Error type:",
            type(error).__name__,
        )

        print(
            "Error:",
            str(error),
        )

        print()
        print(
            "Your database was not committed with "
            "the failed changes."
        )

        raise

    finally:
        connection.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    migrate()