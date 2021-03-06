#!/usr/bin/env python

import argparse, csv, multiprocessing, time, random
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count())
args = parser.parse_args()

csv.field_size_limit(200*1000)

def process_some_rows(reader):
    canons_here = nikons_here = 0
    for row in reader:
        if row[7].lower().startswith('canon'):
            canons_here += 1
        elif row[7].lower().startswith('nikon'):
            nikons_here += 1
    return canons_here, nikons_here
    
def main():
    rdr = csv.reader(open(args.input_file), delimiter='\t')
    worker_pool = multiprocessing.Pool(args.num_processes)
    canons = nikons = 0
    for i in range(args.num_processes):
        (canons_here, nikons_here) = worker_pool.apply(process_some_rows, (rdr,))
        canons += canons_here
        nikons += nikons_here
    worker_pool.close()
    worker_pool.join()
    print "Canons: %s" % canons
    print "Nikons: %s" % nikons

if __name__ == '__main__':
    main()

