#!/usr/bin/env python

# Loop through a big file non-parallel-wise, just for comparison.

import argparse, csv

csv.field_size_limit(200*1000)

parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='../yfcc100m_dataset_1m.tsv')
parser.add_argument('--output_file', default='yfcc100m_filtered.csv')
args = parser.parse_args()

in_reader = csv.reader(open(args.input_file), delimiter='\t')
out_writer = csv.writer(open(args.output_file, 'w'))
for row in in_reader:
    # out_writer.writerow(row)
    if row[7].startswith('Canon'):
        out_writer.writerow(row)

