#!/usr/bin/env python

# multiprocessing.Pool: the simplest way to do some multiprocessing. In this
# case we are just reading in a yfcc100m file and printing out the 8th thing
# in each row: the camera name used.

import argparse, csv, itertools, multiprocessing
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count()-1)
args = parser.parse_args()

def process_a_line(line):
    print line[7]
 
if __name__ == '__main__':
    rdr = csv.reader(open(args.input_file), delimiter='\t')
    worker_pool = multiprocessing.Pool(args.num_processes)
    worker_pool.map(process_a_line, rdr)

