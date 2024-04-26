def lruStrategy(**kwargs):
    return kwargs["cache"].popitem(last=False)