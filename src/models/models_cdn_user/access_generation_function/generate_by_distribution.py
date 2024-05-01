import numpy as np
def generateByDistribution(**kwargs):
    ret = np.random.choice(list(kwargs['pattern'].keys()), kwargs['numToGen'], p=list(kwargs['pattern'].values())) 
    if 'probOneHitter' in kwargs:
        for i in range(len(ret)):
            if np.random.rand() < kwargs['probOneHitter']:
                ret[i] = generateRandomString(10)
    return ret

characters = np.array(list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'))

def generateRandomString(size: int):
    random_indices = np.random.randint(0, len(characters), size=size)
    return ''.join(characters[random_indices])