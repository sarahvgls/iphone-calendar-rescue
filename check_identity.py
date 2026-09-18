import sqlite3

conn = sqlite3.connect('Calendar.sqlitedb')
cur = conn.cursor()

print('=== Identity Table Schema ===')
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

conn.close()

