import sqlite3

conn = sqlite3.connect('Calendar.sqlitedb')
cur = conn.cursor()

# Get Recurrence table schema
print('=== Recurrence Table Schema ===')
schema = cur.execute('PRAGMA table_info(Recurrence)').fetchall()
for col in schema:
    print(f'{col[1]}: {col[2]} (nullable: {not col[3]})')

print('\n=== Sample Recurrence Data (first 5 rows) ===')
sample = cur.execute('SELECT * FROM Recurrence LIMIT 5').fetchall()
if sample:
    column_names = [description[0] for description in cur.description]
    print('Columns:', ', '.join(column_names))
    for i, row in enumerate(sample):
        print(f'\nRow {i+1}:')
        for col_name, value in zip(column_names, row):
            print(f'  {col_name}: {value}')
else:
    print('No recurrence data found')

# Count total recurrences
count = cur.execute('SELECT COUNT(*) FROM Recurrence').fetchone()[0]
print(f'\nTotal recurrences: {count}')

# Check ExceptionDate table too
print('\n=== ExceptionDate Table Schema ===')
schema = cur.execute('PRAGMA table_info(ExceptionDate)').fetchall()
for col in schema:
    print(f'{col[1]}: {col[2]}')

conn.close()

# Check Identity table
print('\n=== Identity Table Schema ===')
conn = sqlite3.connect('Calendar.sqlitedb')
cur = conn.cursor()
schema = cur.execute('PRAGMA table_info(Identity)').fetchall()
for col in schema:
    print(f'{col[1]}: {col[2]}')

print('\n=== Sample Identity Data ===')
sample = cur.execute('SELECT * FROM Identity LIMIT 3').fetchall()
if sample:
    column_names = [description[0] for description in cur.description]
    print('Columns:', ', '.join(column_names))
    for i, row in enumerate(sample):
        print(f'\nRow {i+1}:')
        for col_name, value in zip(column_names, row):
            if value:
                print(f'  {col_name}: {value}')
else:
    print('No identity data found')

# Check Participant table
print('\n=== Participant Table Schema ===')
schema = cur.execute('PRAGMA table_info(Participant)').fetchall()
for col in schema:
    print(f'{col[1]}: {col[2]}')

conn.close()

