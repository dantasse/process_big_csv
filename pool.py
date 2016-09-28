#!/usr/bin/env python

# Using itertools to split a file into N parts.

import argparse, csv, collections, itertools
import multiprocessing, time
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', default=multiprocessing.cpu_count()-1)
args = parser.parse_args()

def process_a_line(line):
    print line[1]
 
if __name__ == '__main__':
    rdr = csv.reader(open(args.input_file), delimiter='\t')
    worker_pool = multiprocessing.Pool(args.num_processes)
    worker_pool.map(process_a_line, rdr)

