import threading

import numpy as np

from collections import OrderedDict

from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode
from src.nodes.itopology import ITopology
from src.simlogging.ilogger import ILogger
from src.sim.imanager import EManagerReqType
from src.simlogging.ilogger import ILogger, ELogType

from src.models.models_cdn_provider.eviction_strategy.lrueviction import lruStrategy
from src.utils import Location

class ModelCDNProvider(IModel):
   
    __modeltag = EModelTag.VIEWOFNODE
    __ownernode: INode
    __supportednodeclasses = []  
    __dependencies = []
    __logger: ILogger
    
    __nodeToTimes = {} #Static variable to hold the pass times for each node. Node id is the key and the value is a numpy array of (start, end, nodeID, ENodeType) tuples 
    __nodeToNode = {} #static variable to see if this pair of nodes has been calculated. Node id is the key and the value is a list of node ids
    __preloaded = False #static variable to see if the pass times have been preloaded
    __nodeToTimesLock = threading.Lock() #Lock for the static variable
    @property
    def iName(self) -> str:
        """
        @type 
            str
        @desc
            A string representing the name of the model class. For example, ModelPower 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    
    @property
    def modelTag(self) -> EModelTag:
        """
        @type
            EModelTag
        @desc
            The model tag for the implemented model
        """
        return self.__modeltag

    @property
    def ownerNode(self):
        """
        @type
            INode
        @desc
            Instance of the owner node that incorporates this model instance.
            The subclass (implementing a model) should keep a private variable holding the owner node instance. 
            This method can return that variable.
        """
        return self.__ownernode
    
    @property
    def supportedNodeClasses(self) -> 'list[str]':
        '''
        @type
            List of string
        @desc
            A model may not support all the node implementation. 
            supportedNodeClasses gives the list of names of the node implementation classes that it supports.
            For example, if a model supports only the SatBasic and SatAdvanced, the list should be ['SatBasic', 'SatAdvanced']
            If the model supports all the node implementations, just keep the list EMPTY.
        '''
        return self.__supportednodeclasses
    
    @property
    def dependencyModelClasses(self) -> 'list[list[str]]':
        '''
        @type
            Nested list of string
        @desc
            dependencyModelClasses gives the nested list of name of the model implementations that this model has dependency on.
            For example, if a model has dependency on the ModelPower and ModelOrbitalBasic, the list should be [['ModelPower'], ['ModelOrbitalBasic']].
            Now, if the model can work with EITHER of the ModelOrbitalBasic OR ModelOrbitalAdvanced, the these two should come under one sublist looking like [['ModelPower'], ['ModelOrbitalBasic', 'ModelOrbitalAdvanced']]. 
            So each exclusively dependent model should be in a separate sublist and all the models that can work with either of the dependent models should be in the same sublist.
            If your model does not have any dependency, just keep the list EMPTY. 
        '''
        return self.__dependencies
    
    def __str__(self) -> str:
        return "".join(["Model name: ", self.iName, ", " , "Model tag: ", self.__modeltag.__str__()])


    def call_APIs(
            self,   
            _apiName: str, 
            **_kwargs):
        '''
        This method acts as an API interface of the model. 
        An API offered by the model can be invoked through this method.
        @param[in] _apiName
            Name of the API. Each model should have a list of the API names.
        @param[in]  _kwargs
            Keyworded arguments that are passed to the corresponding API handler
        @return
            The API return
        '''
        _ret = None

        # try:
        #     _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        # except Exception as e:
        #     print(f"[ModelCDNProvider]: An unhandled API request has been received by {self.__ownernode.nodeID}: ", e)
        _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs) 
        return _ret
    

    def __init__(
        self, 
        _ownernodeins: INode, 
        _loggerins: ILogger,
        _cacheCapacity: int,
        _cacheEvictionStrategy: str,
        _handleRequestsStrategy: str,
        _activeSchedulingStrategy: str
        ) -> None:
        '''
        @desc
            Constructor of the class
        @param[in]  _ownernodeins
            Instance of the owner node that incorporates this model instance
        @param[in]  _loggerins
            Logger instance
        @param[in]  _minElevation
            Minimum elevation angle of view in degrees
        '''
        assert _ownernodeins is not None
        assert _loggerins is not None

        self.__logger = _loggerins
        self.__ownernode = _ownernodeins

        self.__cache = OrderedDict()
        self.__cacheSize = 0 
        self.__cacheCapacity= _cacheCapacity
        self.__cacheEvictionStrategy: callable = self.__cacheEvictionStrategyDictionary[_cacheEvictionStrategy]
        self.__handleRequestsStrategy: callable = self.__handleRequestsStrategyDictionary[_handleRequestsStrategy]
        self.__activeSchedulingStrategy: callable = self.__activeSchedulingStrategyDictionary[_activeSchedulingStrategy]

        self.__myTopology:ITopology = None
                            
    def Execute(self) -> None:
        # Run active scheduling policies
        self.__activeSchedulingStrategy(self)

    def __handle_requests(self, **kwargs) -> list:
        return self.__handleRequestsStrategy(self, requests=kwargs['requests'])

    # Local strategy functions
    def __check_local_cache_only(self, **kwargs):
        if self.__myTopology == None:
            _topologyID = self.__ownernode.topologyID
            _topologies = self.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
            
            
            for _topology in _topologies:
                if _topology.id == _topologyID:
                    self.__myTopology = _topology
                    break
        requests :list = kwargs['requests']
        hits = []
        missed_but_in_sky = []
        missed_but_in_sky_dist = []

        for request in requests:
            if request in self.__cache:
                self.__cache.pop(request)
                self.__cache[request] = True
                hits.append(True)
            else:
                if request not in self.__myTopology.global_cache:
                    self.__myTopology.global_cache[request] = [self.__ownernode.nodeID] 
                else:
                    if len(self.__myTopology.global_cache[request]) > 0:
                        missed_but_in_sky.append(request)
                        # Compute the closest available resource satellite
                        dist = []
                        for remote_source in self.__myTopology.global_cache[request]:
                            remote_source: INode = self.__myTopology.get_Node(remote_source)
                            dist.append(self.__ownernode
                                        .get_Position(self.__ownernode.timestamp)
                                        .get_distance(remote_source.get_Position(remote_source.timestamp)))
                        missed_but_in_sky_dist.append(np.min(dist))

                    self.__myTopology.global_cache[request].append(self.__ownernode.nodeID)
                if self.__cacheSize < self.__cacheCapacity:
                    self.__cacheSize += 1
                else:
                    # We need an eviction
                    poped = self.__cacheEvictionStrategy(cache=self.__cache)[0]
                    self.__myTopology.global_cache[poped].remove(self.__ownernode.nodeID)
                self.__cache[request] = True
                hits.append(False)
    
        if len(missed_but_in_sky) > 0:
            self.__logger.write_Log(f'[Missed but available]{len(missed_but_in_sky)},{missed_but_in_sky},{missed_but_in_sky_dist}', ELogType.LOGALL, self.__ownernode.timestamp, self.iName)
        return hits 
    
    def __no_op(self, **kwargs):
        pass
    
    __apiHandlerDictionary = {
        "handle_requests": __handle_requests
    }

    __cacheEvictionStrategyDictionary = {
        'LRU': lruStrategy
    }

    __handleRequestsStrategyDictionary = {
        "check_local_cache_only": __check_local_cache_only
    }

    __activeSchedulingStrategyDictionary = {
        "no_op": __no_op
    }

    
def init_ModelCDNProvider(
                    _ownernodeins: INode, 
                    _loggerins: ILogger, 
                    _modelArgs) -> IModel:
    '''
    @desc
        This method initializes an instance of ModelFovTimeBased class
    @param[in]  _ownernodeins
        Instance of the owner node that incorporates this model instance
    @param[in]  _loggerins
        Logger instance
    @param[in]  _modelArgs
        It's a converted JSON object containing the model related info. 
        @key min_elevation
            Minimum elevation angle of view in degrees
    @return
        Instance of the model class
    '''
    # check the arguments
    assert _ownernodeins is not None
    assert _loggerins is not None
    
    if "cache_size" not in _modelArgs:
        raise Exception("[ModelCDNProvider Error]: The model arguments should contain the cache_size parameter.") 

    if "cache_eviction_strategy" not in _modelArgs:
        raise Exception("[ModelCDNProvider Error]: The model arguments should contain the cache_eviction_strategy parameter.") 

    if "handle_requests_strategy" not in _modelArgs:
        raise Exception("[ModelCDNProvider Error]: The model arguments should contain the handle_requests_strategy parameter.") 

    if "active_scheduling_strategy" not in _modelArgs:
        raise Exception("[ModelCDNProvider Error]: The model arguments should contain the active_scheduling_stratey parameter.") 
    
    return ModelCDNProvider(_ownernodeins, 
                            _loggerins, 
                            _modelArgs.cache_size, 
                            _modelArgs.cache_eviction_strategy, 
                            _modelArgs.handle_requests_strategy, 
                            _modelArgs.active_scheduling_strategy)
