# match citation data with aggregated firm data (to be run before firm_merge.py)

import argparse
import sqlite3
import numpy as np
import pandas as pd

# parse input arguments
parser = argparse.ArgumentParser(description='Merge patent citation data.')
parser.add_argument('--db', type=str, default=None, help='database file to store to')
parser.add_argument('--chunk', type=int, default=10_000_000, help='chunk size for citations')
args = parser.parse_args()

# open database
con = sqlite3.connect(args.db)

# load in grant data
grants = pd.read_sql('select * from grant_firm', con, index_col='patnum')

# match and aggregates cites
def aggregate_cites(cites):
    print(len(cites))

    # match citations to firms with patnum
    cites = cites.rename(columns={'src': 'citer_pnum', 'dst': 'citee_pnum'})
    cites = cites.join(grants.add_prefix('citer_'), on='citer_pnum')
    cites = cites.join(grants.add_prefix('citee_'), on='citee_pnum')
    cites['self_cite'] = (cites['citer_firm_num'] == cites['citee_firm_num'])

    # patent level statistics
    stats = pd.DataFrame({
        'n_cited': cites.groupby('citer_pnum').size(),
        'n_citing': cites.groupby('citee_pnum').size(),
        'n_self_cited': cites.groupby('citer_pnum')['self_cite'].sum()
    }).rename_axis(index='patnum')
    stats = stats.fillna(0).astype(np.int)

    return stats

# loop ofer citation chunks (otherwise requires >32GB of RAM)
request = pd.read_sql('select * from cite', con, chunksize=args.chunk)
cite_stats = pd.concat([aggregate_cites(df) for df in request], axis=0)
cite_stats = cite_stats.groupby('patnum').sum() # since patents can span multiple chunks
cite_stats.to_sql('cite_stats', con, if_exists='replace')

# close out
con.commit()
con.close()
