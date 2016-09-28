# Let's Process A Hundred Million Photos Kinda Quick

Some fine folks at Yahoo Labs (RIP), spearheaded by the brilliant and kind Bart Thomee, released a data set of 100 million Flickr photos. It's called the [YFCC100M dataset](http://www.yfcc100m.org/) (Yahoo Flickr Creative Commons 100 Million). And we want to do all kinds of research with it.

Thing is, it's pretty big. Just the metadata, not even the pixels of each photo, is 49Gb, in one giant 100M-row tab-separated file. Like, not big enough that we need a cluster (though it sure doesn't hurt), but big enough that looping through it is pretty slow, and we can't load it all into memory.

## Data subsets
The main file is `yfcc100m_dataset`. Of course, being 49Gb, that's not in this repo.

`yfcc100m_1k.tsv` is the first 1000 lines of the dataset, generated with `head -n 1000 yfcc100m_dataset`. I also made a 1M-row dataset, which is about 450Mb (also not in this repo). It's nice to have a couple different data sets at different sizes while testing: the 1k one just shows if I have any crashing bugs, the 1M takes a few seconds so it gives me a clue if things are getting faster or slower, and then once I've tested it on both, I try it on the whole data set.

## Question 1: Canon vs Nikon
I hear that, among camera people, Canon vs Nikon is a kinda funny holy war, similar to vim vs emacs. (When I ask actual camera people if they care, they roll their eyes. Come to think of it, programmers roll their eyes at vim vs emacs too. But let's pretend we care.) So let's try to figure out if more people take photos with Canon or Nikon cameras in this data set.

### Approach 1: The Easy Way
Well, we can just loop through the rows and count. See `nonparallel.py`. On a cloud machine I've got:

    [~/process_big_csv]$ time ./nonparallel.py --input_file=../yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	0m7.876s

    [~/process_big_csv]$ time ./nonparallel.py --input_file=../yfcc100m_dataset
    Canons: 33593232
    Nikons: 19128465

    real    17m48.612s

Err, this is not terrible. If you only will ever have to do this task once, or if this is fast enough for you, stop reading here and just do this the easy way. 

(side note: if you are like me and often run this thing while forgetting `time`, [this sweet script](http://jakemccrary.com/blog/2015/05/03/put-the-last-commands-run-time-in-your-bash-prompt/) can automatically time everything you do.)

### Approach 2: Thinking with multiprocessing and Pools
So we can get it done single-threaded (single-process, even) in a matter of minutes. But why? The other cores are [just sitting there watching](https://twitter.com/reubenbond/status/662061791497744384?lang=en)! Let's use em.

`multiprocessing` seems to be the most popular thing to use in order to do anything parallel in python. And it seems the simplest way to do it is with a Pool. Make a function that does what you want, then `multiprocessing.Map()` it over the whole iterable. Let's try it (this is pool.py):

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

Okay! Err...

    [~/src/process_big_csv]$ ./pool.py
    Canons: 0
    Nikons: 0

Processes don't share memory. That's what makes them different than threads. So you spawn off N new processes, they all go do their thing and get different values of `canons` and `nikons`, but then when the main thread goes to print at the end it still has its own values of `canons` and `nikons`: both zero. More detail on [this stackoverflow](http://stackoverflow.com/questions/659865/python-multiprocessing-sharing-a-large-read-only-object-between-processes).

Even if they did share memory, there's mad racing going on here; different processes trying to update the same counter variables.

Let's try passing the counters around so we can actually count:

    def process_a_row(row, canons, nikons):
        if row[7].lower().startswith('canon'):
            canons += 1
        elif row[7].lower().startswith('nikon'):
            nikons += 1
        return (canons, nikons)
    ...
    def main():
        ...
        for row in rdr:
            canons, nikons = worker_pool.apply(process_a_row, (row, canons, nikons))
        ...

`apply` applies a function to the arguments you give it. (whole code is in `pool2.py`.)

    [~/src/process_big_csv]$ time ./pool2.py --input_file=yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	1m51.824s

Err... we're about 15x slower, from 7 seconds to 111. Why? Because we're not paralellizing the right thing here. We're parallelizing the computation, all that figuring out if it's a canon or a nikon, but we're not parallelizing the disk I/O, which is probably the slowest part. So we get all the overhead of throwing data between processes, and very little of the speedup. As soon as we did `for row in rdr` in `main()`, we were lost.



