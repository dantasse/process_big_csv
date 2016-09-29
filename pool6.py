#!/usr/bin/env python

# Multiprocessing with Pool, take four.

import argparse, csv, multiprocessing, time, random
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='yfcc100m_1k.tsv')
parser.add_argument('--num_processes', type=int, default=multiprocessing.cpu_count())
parser.add_argument('--file_size', type=int, default=484*1024)
args = parser.parse_args()

csv.field_size_limit(200*1000) # There are some big fields in YFCC100M.

def process_some_rows(start_point, end_point):
    infile = open(args.input_file)
    infile.seek(start_point)
    
    # This block is to clear out whatever partial line you're on. If your seek
    # lands you somewhere in the middle of a line, clear that line out with a
    # readline() call before you start reading it for real. (another process
    # will hit that line.) If you happen to land at the start of a line,
    # though, don't readline() because that will eat up a line that no other
    # process will get.
    # If you skip this whole block, you might just be off by one. In a lot of
    # real-world cases (and even for counting Canons and Nikons), that won't
    # matter at all.
    if start_point == 0:
        pass
    else:
        infile.seek(-1, 1) # , 1 means "relative to current location."
        if infile.read(1) != '\n':
            infile.readline() 

    canons_here = nikons_here = 0
    while True:
        row = infile.readline().split('\t')
        # We lose some of the convenience of csv.reader; so it goes.
        if row == ['']:
            break
        
        if row[7].lower().startswith('canon'):
            canons_here += 1
        elif row[7].lower().startswith('nikon'):
            nikons_here += 1
        if infile.tell() > end_point:
            break
        
    return canons_here, nikons_here
    
def main():
    start_indices = [i * args.file_size / args.num_processes for i in range(args.num_processes)]
    end_indices = start_indices[1:] + [args.file_size]

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

    worker_pool.close() # No more jobs for this pool.
    worker_pool.join() # Wait in this process until all the workers finish.
    print "Canons: %s" % canons
    print "Nikons: %s" % nikons

if __name__ == '__main__':
    main()

