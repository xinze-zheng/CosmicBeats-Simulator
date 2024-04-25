def lruStrategy(**kwargs):
    kwargs["cache"].popitem(last=False)