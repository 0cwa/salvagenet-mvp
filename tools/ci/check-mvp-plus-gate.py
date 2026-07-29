#!/usr/bin/env python3
from pathlib import Path
import argparse,re
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(); parser.add_argument('--report-only',action='store_true'); args=parser.parse_args()
text=(root/'docs/roadmap/acceptance-ledger.md').read_text(); section=text.split('<!-- BASE-MVP-BEGIN -->',1)[1].split('<!-- BASE-MVP-END -->',1)[0]
rows=[]
for line in section.splitlines():
    m=re.match(r'\| (B\d+) \|.*\| ([A-Z-]+) \|',line)
    if m: rows.append(m.groups())
not_pass=[item for item in rows if item[1]!='PASS']
if not_pass:
    print('MVP+ BLOCKED; base statuses: '+', '.join(f'{i}={s}' for i,s in not_pass))
    raise SystemExit(0 if args.report_only else 1)
print('MVP+ gate PASS')
