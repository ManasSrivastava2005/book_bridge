from sqlalchemy import inspect,text

def migrate(c):
    for table,fields in {'study_members':[('left_at','TIMESTAMP NULL'),('last_seen_at','TIMESTAMP NULL'),('role',"VARCHAR(20) NOT NULL DEFAULT 'MEMBER'")],'study_messages':[('reply_to_id','INTEGER REFERENCES study_messages(id)'),('edited_at','TIMESTAMP NULL'),('deleted_at','TIMESTAMP NULL')]}.items():
        existing={column['name'] for column in inspect(c).get_columns(table)}
        for name,definition in fields:
            if name not in existing:c.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
    c.execute(text("UPDATE study_members SET role='OWNER' WHERE EXISTS (SELECT 1 FROM study_rooms WHERE study_rooms.id=study_members.room_id AND study_rooms.owner_id=study_members.user_id)"))
