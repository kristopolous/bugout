import csv, sys
csv.field_size_limit(100000000000)
rdr = csv.reader(sys.stdin)
wtr = csv.writer(sys.stdout, lineterminator='\n')
for row in rdr:
  wtr.writerow([f.replace('\n','\\n') for f in row])
