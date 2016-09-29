#!/usr/bin/env python

import argparse, csv, multiprocessing, time, random
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count())
parser.add_argument('--num_rows', type=int, default=1000)
args = parser.parse_args()

csv.field_size_limit(200*1000)

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

    worker_pool = multiprocessing.Pool(args.num_processes)
    canons = nikons = 0
    results = []
    for i in range(args.num_processes):
        res = worker_pool.apply_async(process_some_rows, (start_indices[i], end_indices[i]))
        results.append(res)
    for res in results:
        (canons_here, nikons_here) = res.get()
        canons += canons_here
        nikons += nikons_here

    worker_pool.close()
    worker_pool.join()
    print "Canons: %s" % canons
    print "Nikons: %s" % nikons

if __name__ == '__main__':
    main()

