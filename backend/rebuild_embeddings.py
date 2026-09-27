import sys
import time

from app.database import SessionLocal
from app.models import DocumentChunk
from app.embeddings import create_embedding
import json


# ============================================================
# CONFIGURATION
# ============================================================

BATCH_SIZE = 10


# ============================================================
# MAIN MIGRATION
# ============================================================

def rebuild_embeddings():

    print()
    print("=" * 70)
    print("DOCUMIND AI - OLLAMA EMBEDDING MIGRATION")
    print("=" * 70)
    print("Embedding model: nomic-embed-text")
    print("Expected dimensions: 768")
    print("=" * 70)
    print()

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Get all document chunks
        # ----------------------------------------------------

        chunks = (
            db.query(DocumentChunk)
            .order_by(DocumentChunk.id)
            .all()
        )

        total = len(chunks)

        print(
            f"Found {total} document chunks."
        )
        print()

        if total == 0:

            print(
                "No document chunks were found."
            )

            return

        # ----------------------------------------------------
        # Confirmation
        # ----------------------------------------------------

        print(
            "WARNING:"
        )
        print(
            "This will replace the existing embeddings "
            "with Ollama embeddings."
        )
        print()

        print(
            "Your database backup should already exist:"
        )

        print(
            "documind_backup_before_ollama_embeddings.db"
        )

        print()

        # ----------------------------------------------------
        # Process chunks
        # ----------------------------------------------------

        successful = 0
        failed = 0

        start_time = time.time()

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            print("-" * 70)

            print(
                f"Processing chunk {index}/{total}"
            )

            print(
                f"Chunk ID: {chunk.id}"
            )

            # ------------------------------------------------
            # Get chunk text
            # ------------------------------------------------

            content = (
                chunk.content
                if chunk.content
                else ""
            )

            content = content.strip()

            if not content:

                print(
                    "SKIPPED: Empty chunk content."
                )

                failed += 1

                continue

            try:

                # --------------------------------------------
                # Generate local embedding
                # --------------------------------------------

                embedding = create_embedding(
                    content
                )

                # --------------------------------------------
                # Validate dimensions
                # --------------------------------------------

                if len(embedding) != 768:

                    raise ValueError(
                        "Unexpected embedding dimensions: "
                        f"{len(embedding)}. "
                        "Expected 768."
                    )

                # --------------------------------------------
                # Store embedding
                # --------------------------------------------

                chunk.embedding = json.dumps(
                    embedding
                )

                successful += 1

                print(
                    f"SUCCESS: {len(embedding)} dimensions"
                )

                # --------------------------------------------
                # Commit every batch
                # --------------------------------------------

                if (
                    successful % BATCH_SIZE
                    == 0
                ):

                    db.commit()

                    print(
                        f"Saved batch. "
                        f"Progress: {index}/{total}"
                    )

            except Exception as error:

                failed += 1

                print(
                    "FAILED:"
                )

                print(
                    "Error type:",
                    type(error).__name__,
                )

                print(
                    "Error:",
                    str(error),
                )

                # --------------------------------------------
                # Roll back only the failed transaction
                # --------------------------------------------

                db.rollback()

        # ----------------------------------------------------
        # Final commit
        # ----------------------------------------------------

        db.commit()

        elapsed = time.time() - start_time

        print()
        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)

        print(
            "Total chunks:",
            total,
        )

        print(
            "Successful:",
            successful,
        )

        print(
            "Failed:",
            failed,
        )

        print(
            "Time:",
            f"{elapsed:.2f} seconds",
        )

        print("=" * 70)

        if failed == 0:

            print()
            print(
                "SUCCESS! All document chunks now use"
            )

            print(
                "Ollama / nomic-embed-text embeddings."
            )

            print()

        else:

            print()
            print(
                "Migration finished with some failures."
            )

            print(
                "Do NOT delete the database backup."
            )

            print()

    except KeyboardInterrupt:

        print()
        print("=" * 70)
        print("MIGRATION CANCELLED")
        print("=" * 70)
        print()
        print(
            "The database backup is still available."
        )
        print()

        db.rollback()

    except Exception as error:

        print()
        print("=" * 70)
        print("MIGRATION ERROR")
        print("=" * 70)

        print(
            "Error type:",
            type(error).__name__,
        )

        print(
            "Error:",
            str(error),
        )

        print("=" * 70)

        db.rollback()

        sys.exit(1)

    finally:

        db.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    rebuild_embeddings()