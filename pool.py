#!/usr/bin/env python

# multiprocessing.Pool: the simplest way to do some multiprocessing. In this
# case we are just reading in a yfcc100m file and printing out the 8th thing
# in each row: the camera name used.

# Note that this will not work.

import argparse, csv, itertools, multiprocessing
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count()-1)
args = parser.parse_args()

canons = 0
nikons = 0
def process_a_row(row):
    global canons, nikons
    if row[7].lower().startswith('canon'):
        canons += 1
    elif row[7].lower().startswith('nikon'):
        nikons += 1
 
if __name__ == '__main__':
    rdr = csv.reader(open(args.input_file), delimiter='\t')
    worker_pool = multiprocessing.Pool(args.num_processes)
    worker_pool.map(process_a_row, rdr)
    print "Canons: %s" % canons
    print "Nikons: %s" % nikons

