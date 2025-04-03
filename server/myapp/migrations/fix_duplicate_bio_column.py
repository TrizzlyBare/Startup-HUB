from django.db import migrations


def rename_duplicate_columns(apps, schema_editor):
    """
    This function will execute raw SQL to fix the schema issues by
    renaming any duplicate bio columns that might exist.
    """
    # Check if we're using SQLite
    if schema_editor.connection.vendor == "sqlite":
        # Get the table structure
        schema_editor.execute("PRAGMA table_info('myapp_startupidea');")
        columns = schema_editor.connection.cursor().fetchall()

        # Check if bio column exists in the table
        bio_columns = [col[1] for col in columns if col[1] == "bio"]

        if len(bio_columns) > 0:
            # We need to create a new table without the bio column
            schema_editor.execute(
                """
                -- Create a temporary table without the duplicate column
                CREATE TABLE myapp_startupidea_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    stage VARCHAR(20) NOT NULL,
                    pitch TEXT NOT NULL,
                    description TEXT NOT NULL,
                    looking_for TEXT NOT NULL,
                    skills TEXT NOT NULL,
                    user_role VARCHAR(20) NOT NULL,
                    website VARCHAR(200) NOT NULL,
                    funding_stage VARCHAR(100) NOT NULL,
                    investment_needed DECIMAL NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES authen_customuser (id)
                );
                
                -- Copy data from the old table to the new table, excluding bio
                INSERT INTO myapp_startupidea_temp (
                    id, name, stage, pitch, description, looking_for, skills,
                    user_role, website, funding_stage, investment_needed,
                    created_at, updated_at, user_id
                )
                SELECT 
                    id, name, stage, pitch, description, looking_for, skills,
                    user_role, website, funding_stage, investment_needed,
                    created_at, updated_at, user_id
                FROM myapp_startupidea;
                
                -- Drop the old table
                DROP TABLE myapp_startupidea;
                
                -- Rename the new table to the original name
                ALTER TABLE myapp_startupidea_temp RENAME TO myapp_startupidea;
                
                -- Recreate any indexes (you may need to add more based on your schema)
                CREATE INDEX myapp_startupidea_user_id ON myapp_startupidea (user_id);
            """
            )


class Migration(migrations.Migration):
    """
    Migration to manually fix the duplicate 'bio' column issue in the schema.
    This approach directly manipulates the database schema to remove the duplicate column.
    """

    dependencies = [
        ("myapp", "0001_initial"),  # Replace with your last successful migration
    ]

    operations = [
        migrations.RunPython(rename_duplicate_columns),
    ]
