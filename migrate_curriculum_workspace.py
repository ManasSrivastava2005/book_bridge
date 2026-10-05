"""Additive, repeatable migration. Historical plans/exams/uploads remain intact."""
from sqlalchemy import inspect, text

def migrate(connection):
    additions = {
        'academic_profiles': [('daily_minutes', 'INTEGER NOT NULL DEFAULT 60')],
        'student_exams': [('topic_ids', 'JSON NULL')],
        'syllabus_uploads': [('subject_id', 'INTEGER REFERENCES curriculum_nodes(id)')],
    }
    for table, columns in additions.items():
        existing = {column['name'] for column in inspect(connection).get_columns(table)}
        for name, definition in columns:
            if name not in existing:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
