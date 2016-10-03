# Let's Process A Hundred Million Photos Kinda Quick in Python

tl;dr: feel free to commandeer `pool6.py` to run stuff over big text files in parallel.

Some fine folks at Yahoo Labs (RIP), spearheaded by the brilliant and kind Bart Thomee, released a data set of 100 million Flickr photos. It's called the [YFCC100M dataset](http://www.yfcc100m.org/) (Yahoo Flickr Creative Commons 100 Million). And we want to do all kinds of research with it.

Thing is, it's pretty big. Just the metadata, not even the pixels of each photo, is 49Gb, in one giant 100M-row tab-separated file. Like, not big enough that we need a cluster\*, but big enough that looping through it is pretty slow, and we can't load it all into memory.

## Data subsets
The main file is `yfcc100m_dataset`. Of course, being 49Gb, that's not in this repo. [Submit a request](http://webscope.sandbox.yahoo.com/catalog.php?datatype=i&did=67) and the fine Yahoos will give you access to it.

`yfcc100m_1k.tsv` is the first 1000 lines of the dataset, generated with `head -n 1000 yfcc100m_dataset`. I also made a 1M-row dataset, which is about 450Mb (also not in this repo). It's nice to have a couple different data sets at different sizes while testing: the 1k one just shows if I have any crashing bugs, the 1M takes a few seconds so it gives me a clue if things are getting faster or slower, and then once I've tested it on both, I try it on the whole data set.

## Our Question: Canon vs Nikon
I hear that, among camera people, Canon vs Nikon is a kinda funny holy war, similar to vim vs emacs. (When I ask actual camera people if they care, they roll their eyes. Come to think of it, programmers roll their eyes at vim vs emacs too. But let's pretend we care.) So let's try to figure out if more people take photos with Canon or Nikon cameras in this data set.

### Approach 1: Good old fashioned `for` loops
Well, we can just loop through the rows and count. See `nonparallel.py`. On my laptop:

    [~/src/process_big_csv]$ time ./nonparallel.py --input_file=yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	0m5.952s

    [~/process_big_csv]$ time ./nonparallel.py --input_file=../yfcc100m_dataset
    Canons: 33593232
    Nikons: 19128465

    real    17m48.612s

Err, this is not terrible. If you only will ever have to do this task once, or if this is fast enough for you, stop reading here and just do this the easy way. 

(side note: if you are like me and often run scripts while forgetting to time them, [this sweet script](http://jakemccrary.com/blog/2015/05/03/put-the-last-commands-run-time-in-your-bash-prompt/) can automatically time everything you do.)

### Approach 2: Thinking with multiprocessing
So we can get it done single-threaded (single-process, even) in a matter of minutes. But why? The other cores are [just sitting there watching](https://twitter.com/reubenbond/status/662061791497744384?lang=en)! Let's use em.

#### Try 2.1: jump in the pool
`multiprocessing` seems to be the most popular thing to use in order to do anything parallel in python. And it seems the simplest way to do it is with a Pool. Make a function that does what you want, then `multiprocessing.map()` it over the whole iterable. Let's try it (this is `pool.py`):

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

Okay! Uh...

    [~/src/process_big_csv]$ ./pool.py
    Canons: 0
    Nikons: 0

Processes don't share memory. That's what makes them different than threads. So you spawn off N new processes, they all go do their thing and get different values of `canons` and `nikons`, but then when the main thread goes to print at the end it still has its own values of `canons` and `nikons`: both zero. More detail on [this stackoverflow](http://stackoverflow.com/questions/659865/python-multiprocessing-sharing-a-large-read-only-object-between-processes).

Even if they did share memory, there's mad racing going on here; different processes trying to update the same counter variables. (Imagine you had two different processes incrementing `canons` at the same time. The current `canons` is 294, so they both read 294, they both add one, then they both write 295, though it should be 296. Wikipedia [has a little more detail](https://en.wikipedia.org/wiki/Race_condition#Example) if you're not familiar with the idea.)

#### Try 2.2: sharing memory even when you can't share memory

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

`apply` picks one of the worker processes in the pool and has that process apply a function to the arguments you give it. (whole code is in `pool2.py`.)

    [~/src/process_big_csv]$ time ./pool2.py --input_file=yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	1m51.824s

We're about 20x slower, at almost 2 minutes. Why? Because we're not actually parallelizing anything here. `apply()` is synchronous, and even if we throw in `apply_async` instead, we'd be parallelizing the wrong thing. We're parallelizing the computation, all that figuring out if it's a canon or a nikon, but we're not parallelizing the disk I/O, which is probably the slowest part. So we get all the overhead of starting and stopping and throwing data between processes, and very little of the speedup. As soon as we did `for row in rdr` in `main()`, we were lost.

(Plus, still race conditions.)

#### Side note: hey wait, I saw all these tutorials using Pool.map(), why isn't that just working for us now?
Yeah. Stuff like this:

    def f(x):
        return x*x

    worker_pool = multiprocessing.Pool(10)
    print worker_pool.map(f, [1, 2, 3, 4, 5])

Well, besides the fact that it's silly to use 10 processes to square 5 numbers, it's also assuming that the slow part is the computation, the stuff inside f(). For processing YFCC100M data (and most of the stuff I do), that's not true. I think Pool.map is great when you have plenty of memory but need to parallelize computation, but our computation is quick, but we need to parallelize IO and avoid having the whole file in memory.

### Approach 3: one process per processor

Ok, so parallelizing is good in theory, but generating one process per row isn't great. what if, instead, we fork off one process per processor, let each one gobble rows as fast as it can, count whichever rows it picks off, and then return the count when it's done?

#### Try 3.1: the "Hungry Hungry Hippos" approach

    def process_some_rows(reader):
        canons_here = nikons_here = 0
        for row in reader:
            if row[7].lower().startswith('canon'):
                canons_here += 1
            elif row[7].lower().startswith('nikon'):
                nikons_here += 1
        return canons_here, nikons_here
    ...
    for i in range(args.num_processes):
        (canons_here, nikons_here) = worker_pool.apply(process_some_rows, (rdr,))
        canons += canons_here
        nikons += nikons_here

(find this in `pool3.py`)

... `TypeError: can't pickle _csv.reader objects`. The error in our thinking is "let each one pick off a bunch of rows" - that's not something a csv.reader is built to do. (in a previous programming life, I would have called this "thread safe" - now it's processes instead of threads, but same basic idea.) We're getting close, though!

#### Try 3.2: You get a csv.reader! And you get a csv.reader!
Ok, so one process per processor, but let's also give each process its own `csv.reader`. To do this, we'll tell each one which row number to start and stop on.

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
    ...
    start_indices = [i * args.num_rows / args.num_processes for i in range(args.num_processes)]
    end_indices = start_indices[1:] + [args.num_rows]

    for i in range(args.num_processes):
        (canons_here, nikons_here) = worker_pool.apply(process_some_rows, (starts[i], ends[i]))
        canons += canons_here
        nikons += nikons_here

Check it in `pool4.py`.

    [~/src/process_big_csv]$ time ./pool4.py --input_file=yfcc100m_1m.tsv --num_rows=1000000
    Canons: 338748
    Nikons: 192088

    real	0m11.026s

Back out of crazy land, but still slower than `nonparallel.py`. Put in some print statements to find out why: remember, `apply()` is synchronous. So we're sort of tossing stuff to another process, but never making two processes do anything in parallel.

#### Try 3.3: if you want to do things asynchronously, use the method with `async` in the name
I hinted earlier at the existence of `apply_async()`, which would solve this last issue. Only minor changes between pool4 and pool5:

    results = []
    for i in range(args.num_processes):
        res = worker_pool.apply_async(process_some_rows, (start_indices[i], end_indices[i]))
        results.append(res)
    for res in results:
        (canons_here, nikons_here) = res.get()
        canons += canons_here
        nikons += nikons_here

Instead of just taking the return value for each worker, we have to store the result and then later call `get()` on it. The `apply_async()` starts each process working, and nothing blocks until we call `get()`.

    [~/src/process_big_csv]$ time ./pool5.py --input_file=yfcc100m_1m.tsv --num_rows=1000000
    Canons: 338748
    Nikons: 192088

    real	0m6.388s

We're almost back to our stupid nonparallel baseline! Why can't we beat it? Well, say we've got 3 processes going: one is doing rows 0-333333, one is doing rows 333334-666666, and one is doing rows 666667-1000000. Process #3 has to just skip past rows 0-666666 before even doing anything, and that takes about as long as actually reading those rows.

#### Try 3.4: `seek` and ye shall find

Looping through rows with a csv.reader is slow. Using `file.seek()` is fast. So instead of chopping it into rows, let's chop it up by bytes.

    file_size = os.path.getsize(args.input_file)
    ...
    infile = open(args.input_file)
    infile.seek(start_point)
    ...
    # Check the code for some off-by-one futzing.
    ...
    while True:
        row = infile.readline().split('\t')
        # We can't use csv.reader anymore, because there's no easy way to
        # convert between rows (which csv.reader speaks) and bytes. s'ok, it
        # wasn't buying us that much anyway.
        if row == ['']:
            break
        
        if row[7].lower().startswith('canon'):
            canons_here += 1
        elif row[7].lower().startswith('nikon'):
            nikons_here += 1
        if infile.tell() > end_point:
            break

See `pool6.py`.
 
    [~/src/process_big_csv]$ time ./pool6.py --input_file=yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	0m2.590s

Heyo! We're running in parallel! (This is with 4 processes on my 4 core laptop.)

Numbers on an 8-core computer for the whole 100M dataset:

    time ./pool6.py --input_file=../yfcc100m_dataset
    Canons: 33593232
    Nikons: 19128465

    real	3m38.840s

Remember how it used to be 17 minutes? Ok, I mean, we're not winning Nobel prizes here, but 3 minutes is a short distraction on facebook, and 17 minutes is you go get coffee and then get interrupted by someone else and your whole day is shot. I don't know, I'm excited about this, anyway :P

Oh, and Canon wins. Ok. Camera people, do you care about this at all? Nah, didn't think so.

### Advanced bonus: Queues and itertools

There's lots more fun in python multiprocessing you can get into. For example, instead of letting Python manage all your workers in a Pool, you can create them manually. Then you can use Values and Queues to communicate between them. (As you can imagine, this is better avoided if you can.) I kept a file around at `queues.py` where I tried to do this; feel free to try it, even though it's no faster than `nonparallel.py` because it doesn't parallelize the I/O.

And if you've got any groupings in your rows, like if the files are grouped by user or anything, you can iterate through them group by group using itertools. More on [this SO post](http://stackoverflow.com/questions/8717179/chunking-data-from-a-large-file-for-multiprocessing).

But for our simple task, I don't think you're going to get much better speedup than we did. So either use your newfound knowledge to save yourself time (ideally) or copy and paste `pool6.py` incessantly (more likely).

### Side note on clusters
\* this is where the asterisk from way up at the top goes

"Dan, shouldn't we put this on a cluster? fly through the [big data tunnel](http://bigdatapix.tumblr.com/post/94541047247/the-binary-tunnel-is-back-this-time-with-a-silver) and hadoop pig hive [tokatek hekaton azkaban](https://pixelastic.github.io/pokemonorbigdata/)?"

I don't think so. I've got a little experience with a hadoop cluster, and 3 minutes is short enough that you can't really run a program in much less than that. Maybe 1 minute, but that difference is not so big. Plus, in order to do things at Big Data scale, you've got to use less-flexible tools like Hive or Pig.

But I'm not sure about this. Maybe there's a way to run this medium-sized-data kind of task a lot quicker if you had infinite computers. If so, let me know.

Speaking of which, I'm this name at gmail if you have any feedback or questions. I'd welcome them.
