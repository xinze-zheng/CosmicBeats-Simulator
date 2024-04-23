import numpy as np
def generateByDistribution(pattern: dict, numToGen: int):
    return list(np.random.sample(pattern.keys(), p=pattern.values()))