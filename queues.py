#!/usr/bin/env python

# Loop through the yfcc dataset. Just output something for the rows that match
# a certain criterion (say, they're in the right place).

import argparse, csv, multiprocessing

csv.field_size_limit(200*1000)

parser = argparse.ArgumentParser()
parser.add_argument('--input_file', default='../yfcc100m_dataset_1m.tsv')
parser.add_argument('--output_file', default='yfcc100m_filtered.csv')
parser.add_argument('--num_procs', type=int, default=multiprocessing.cpu_count()-1)
args = parser.parse_args()

inq = multiprocessing.Queue()
outq = multiprocessing.Queue()

in_reader = csv.reader(open(args.input_file), delimiter='\t')
def parse_input_csv():
    for row in in_reader:
        inq.put(row)
    # Got to send a STOP to cut off each one:
    for i in range(args.num_procs):
        inq.put("STOP")

def check_row():
    for row in iter(inq.get, "STOP"):
        if row[7].startswith('Canon'):
            outq.put(row)
    outq.put("STOP")

def write_output_csv():
    out_writer = csv.writer(open(args.output_file, 'w'))
    # Listen for num_procs STOP messages.
    for i in range(args.num_procs):
        for row in iter(outq.get, "STOP"):
            out_writer.writerow(row)
    

if __name__ == '__main__':
   
    in_proc = multiprocessing.Process(target=parse_input_csv)
    out_proc = multiprocessing.Process(target=write_output_csv)
    worker_procs = [multiprocessing.Process(target = check_row, args=()) for i in range(args.num_procs)]

    in_proc.start()
    out_proc.start()
    for proc in worker_procs:
        proc.start()

    in_proc.join()
    i = 0
    for proc in worker_procs:
        proc.join()
        print "Done", i
        i += 1

    out_proc.join()

