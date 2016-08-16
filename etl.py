import os
import csv
from nmid.database import Base, engine
import sqlalchemy as sa

FIELD_MAPPING = {
    "Description": "transaction_type",
    "IsAnonymous": "anonymous",
    "Amount": "amount",
    "Date Contribution": "date",
    "Memo": "memo",
    "ContribExpenditure Description": "description",
    "ContribExpenditure First Name": "first_name",
    "ContribExpenditure Middle Name": "middle_name",
    "ContribExpenditure Last Name": "last_name",
    "Suffix": "name_suffix",
    "Company Name": "company_name",
    "Address": "address",
    "City": "city",
    "State": "state",
    "Zip": "zipcode",
    "Occupation": "occupation",
    "Filing Period": "filing_period",
    "Date Added": "date_added",
}

def iterFile(path):
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        yield from reader

def rewriteKeys(row):
    
    new_row = {}
    for key in row.keys():
        try:
            new_row[FIELD_MAPPING[key]] = row[key]
        except KeyError:
            pass

    return new_row

def makeNulls(row):

    for k,v in row.items():
        if row[k] == '':
            row[k] = None
    
    return row

def insertRows(rows, table_name):
    field_names = ', '.join(rows[0].keys())
    param_names = ', '.join([':{}'.format(f) for f in rows[0].keys()])

    insert = ''' 
        INSERT INTO {table_name} (
          {field_names}
        ) VALUES (
          {param_names}
        )
        ON CONFLICT DO NOTHING
        RETURNING *
    '''.format(field_names=field_names,
               param_names=param_names,
               table_name=table_name)
    
    with engine.begin() as conn:
        inserted = conn.execute(sa.text(insert), *rows)
    
    return inserted

def getRelation(table, **query_data):
    where_clause = ' AND '.join(["{0} = :{0}".format(k) for k in \
                                                            query_data.keys()])

    rows = ''' 
        SELECT * FROM {table}
        WHERE {where_clause}
    '''.format(table=table,
               where_clause=where_clause)
    
    return engine.execute(sa.text(rows), **query_data).first()


if __name__ == "__main__":
    import sys
    import nmid.models
    
    try:
        if sys.argv[1] == 'init':
            Base.metadata.drop_all(bind=engine)
            print('dropped')
            Base.metadata.create_all(bind=engine)
            print('created')
    except IndexError:
        pass

    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
    candidates_dir = os.path.join(data_dir, 'candidates')
    pacs_dir = os.path.join(data_dir, 'pacs')

    bulk_insert = []
    inserted = 0

    for candidate_file in os.listdir(candidates_dir):
        file_path = os.path.join(candidates_dir, candidate_file)
        
        for row in iterFile(file_path):
            
            cand_dict = {
                'first_name': row['First Name'],
                'last_name': row['Last Name'],
            }

            candidate = getRelation('candidates', **cand_dict)
            
            if not candidate:
                candidate = insertRows([cand_dict], 'candidates').first()
                
                print('Created new candidate', 
                      candidate.first_name, 
                      candidate.last_name)

            row = rewriteKeys(row)
            row = makeNulls(row)
            row['candidate_id'] = candidate.candidate_id
            bulk_insert.append(row)

            if len(bulk_insert) % 10000 == 0:
                insertRows(bulk_insert, 'transactions')
                inserted += 10000
                print('Inserted', inserted, 'candidate transactions')
                bulk_insert = []
    
    if bulk_insert:
        insertRows(bulk_insert, 'transactions')
        inserted += len(bulk_insert)
        print('Inserted', inserted, 'candidates')

    bulk_insert = []
    inserted = 0
    
    for pac_file in os.listdir(pacs_dir):
        file_path = os.path.join(pacs_dir, pac_file)
        
        for row in iterFile(file_path):
            pac_dict = {'name': row['PAC Name']}

            pac = getRelation('pacs', **pac_dict)
            
            if not pac:
                pac = insertRows([pac_dict], 'pacs').first()
                print('Created new PAC', pac.name)

            row = rewriteKeys(row)
            row = makeNulls(row)
            row['pac_id'] = pac.pac_id
            bulk_insert.append(row)

            if len(bulk_insert) % 10000 == 0:
                insertRows(bulk_insert, 'transactions')
                inserted += 10000
                print('Inserted', inserted, 'pac transactions')
                bulk_insert = []
    
    if bulk_insert:
        insertRows(bulk_insert, 'transactions')
        inserted += len(bulk_insert)
        print('Inserted', inserted, 'pacs')
