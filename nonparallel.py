#!/usr/bin/env python

import argparse, csv

parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
args = parser.parse_args()

csv.field_size_limit(200*1000)

canons = 0
nikons = 0
for row in csv.reader(open(args.input_file), delimiter='\t'):
    if row[7].lower().startswith('canon'):
        canons += 1
    elif row[7].lower().startswith('nikon'):
        nikons += 1

print "Canons: %s" % canons
print "Nikons: %s" % nikons
