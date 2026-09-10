import concurrent.futures
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_connection

root = Path(__file__).resolve().parents[1]
out = root / 'work' / 'nursing_live'
out.mkdir(parents=True, exist_ok=True)
ids = ['810ABSN','810BBSN','810CBSN','810DBSN','810FBSN','810GBSN','810HBSN',
       '810KBSN','810MBSN','810NBSN','810QBSN','810SBSN','8875BSN']
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('select program_id, source_url from programs where program_id = any(%s)', (ids,))
        urls = dict(cur.fetchall())

def fetch(pid):
    target = out / f'{pid}.html'
    if target.exists():
        return pid, target.stat().st_size, 'cached-this-run'
    req = urllib.request.Request(urls[pid], headers={'User-Agent': 'Asteris source audit/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = response.read()
        modified = response.headers.get('Last-Modified', '')
    target.write_bytes(body)
    return pid, len(body), modified

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for result in pool.map(fetch, ids):
        print(*result)
