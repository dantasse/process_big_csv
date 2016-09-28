# Let's Process A Hundred Million Photos Kinda Quick

Some fine folks at Yahoo Labs (RIP), spearheaded by the brilliant and kind Bart Thomee, released a data set of 100 million Flickr photos. It's called the [YFCC100M dataset](http://www.yfcc100m.org/) (Yahoo Flickr Creative Commons 100 Million). And we want to do all kinds of research with it.

Thing is, it's pretty big. Just the metadata, not even the pixels of each photo, is 49Gb, in one giant 100M-row tab-separated file. Like, not big enough that we need a cluster (though it sure doesn't hurt), but big enough that looping through it is pretty slow, and we can't load it all into memory.

## Data subsets
The main file is `yfcc100m_dataset`. Of course, being 49Gb, that's not in this repo.

`yfcc100m_1k.tsv` is the first 1000 lines of the dataset, generated with `head -n 1000 yfcc100m_dataset`. I also made a 1M-row dataset, which is about 450Mb (also not in this repo). It's nice to have a couple different data sets at different sizes while testing: the 1k one just shows if I have any crashing bugs, the 1M takes a few seconds so it gives me a clue if things are getting faster or slower, and then once I've tested it on both, I try it on the whole data set.

## Question 1: Canon vs Nikon
I hear that, among camera people, Canon vs Nikon is a kinda funny holy war, similar to vim vs emacs. (When I ask actual camera people if they care, they roll their eyes. Come to think of it, programmers roll their eyes at vim vs emacs too. But let's pretend we care.) So let's try to figure out if more people take photos with Canon or Nikon cameras in this data set.

### Approach 1: The Easy Way
Well, we can just loop through the rows and count. See `nonparallel.py`. On my reference machine:

    [last: 5s][~/src/process_big_csv]$ time ./nonparallel.py --input_file=yfcc100m_1m.tsv
    Canons: 338748
    Nikons: 192088

    real	0m5.845s

On a cloud machine I've got:

    [last: 0s][~/process_big_csv]$ time ./nonparallel.py --input_file=../yfcc100m_1m.tsv
    Canons: 33597
    Nikons: 19292

    real	0m0.801s

Err, this is pretty fast. If you only will ever have to do this task once, or if this is fast enough for you, stop reading here and just do this the easy way. 

(side note: yeah, I got [this sweet script that times everything I do](http://jakemccrary.com/blog/2015/05/03/put-the-last-commands-run-time-in-your-bash-prompt/))

### Approach 2: Thinking with multiprocessing and Pools
But, I mean, the other cores are [just sitting there watching](https://twitter.com/reubenbond/status/662061791497744384?lang=en). Let's use em.

`multiprocessing` seems to be the most popular thing to use in order to do anything parallel in python. And it seems the simplest way to do it is with a Pool. 
