import numpy as np
def generateByDistribution(pattern: dict, numToGen: int):
    ret = np.random.choice(list(pattern.keys()), numToGen, p=list(pattern.values())) 
    return ret