#!/usr/bin/env python3
"""
Stamp the Alembic version to match the current database state.

This script is useful when:
- Tables were created by Base.metadata.create_all() but migrations weren't tracked
- You need to mark existing database as up-to-date without running migrations

Usage:
    python stamp_migrations.py

Or manually with alembic:
    alembic stamp head

This marks the database as being at the latest migration version without
actually running any migrations.
"""
import subprocess
import sys

def stamp_database():
    """Stamp the database with the latest migration version"""
    try:
        print("=" * 80)
        print("Stamping Alembic Database Version")
        print("=" * 80)
        print("\nThis will mark your database as being at the latest migration")
        print("version WITHOUT running any migrations.\n")
        print("Use this only if:")
        print("  1. Your database tables already exist")
        print("  2. Migrations are failing with 'table already exists' errors")
        print("  3. You want to mark the database as up-to-date\n")

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "head"],
            capture_output=True,
            text=True,
            check=True
        )

        print("✓ Database stamped successfully!")
        if result.stdout:
            print(result.stdout)

        print("\n" + "=" * 80)
        print("Next steps:")
        print("  1. Verify: alembic current")
        print("  2. Run bot: python app/main.py")
        print("=" * 80)
        return True

    except subprocess.CalledProcessError as e:
        print("\n✗ Failed to stamp database!")
        print(f"\nError: {e}")
        if e.stdout:
            print(f"\nOutput: {e.stdout}")
        if e.stderr:
            print(f"\nError details: {e.stderr}")
        print("\n" + "=" * 80)
        print("Manual fix:")
        print("  If alembic is not installed in this environment,")
        print("  activate your virtual environment first:")
        print("    source venv/bin/activate  # Linux/Mac")
        print("    .\\venv\\Scripts\\activate   # Windows")
        print("  Then run: alembic stamp head")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = stamp_database()
    sys.exit(0 if success else 1)
