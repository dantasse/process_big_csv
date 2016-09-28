#!/usr/bin/env python

# Multiprocessing with Pool, take four.

import argparse, csv, multiprocessing, time, random
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count()-1)
parser.add_argument('--num_rows', type=int, default=1000)
args = parser.parse_args()

csv.field_size_limit(200*1000) # There are some big fields in YFCC100M.

def process_some_rows(start_row, end_row):
    reader = csv.reader(open(args.input_file), delimiter='\t')
    for i in range(start_row):
        reader.next()

    canons_here = nikons_here = 0
    for i in range(end_row - start_row):
        row = reader.next()
        if row[7].lower().startswith('canon'):
            canons_here += 1
        elif row[7].lower().startswith('nikon'):
            nikons_here += 1
    return canons_here, nikons_here
    
def main():
    start_indices = [i * args.num_rows / args.num_processes for i in range(args.num_processes)]
    end_indices = start_indices[1:] + [args.num_rows]
    # so, if num_processes is 3 and num_rows is 1000, we have [0, 333, 666] and
    # [333, 666, 1000]

    worker_pool = multiprocessing.Pool(args.num_processes)
    canons = nikons = 0
    for i in range(args.num_processes):
        (canons_here, nikons_here) = worker_pool.apply(process_some_rows, (start_indices[i], end_indices[i]))
        canons += canons_here
        nikons += nikons_here
    worker_pool.close() # No more jobs for this pool.
    worker_pool.join() # Wait in this process until all the workers finish.
    print "Canons: %s" % canons
    print "Nikons: %s" % nikons

if __name__ == '__main__':
    main()

