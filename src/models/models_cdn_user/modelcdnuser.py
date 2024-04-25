from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.simlogging.ilogger import ILogger
from src.sim.imanager import EManagerReqType
from src.simlogging.ilogger import ILogger, ELogType

from src.models.models_cdn_user.access_generation_function.generate_by_distribution import generateByDistribution
from src.models.models_cdn_user.scheduling_strategy_function.schedule_largest_elevation import schduleLargestElevation

import numpy as np
import json

class ModelCDNUser(IModel):
   
    __modeltag = EModelTag.VIEWOFNODE
    __ownernode: INode
    __supportednodeclasses = []  
    __dependencies = []
    __logger: ILogger
    
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

        try:
            _ret = self.__apiHandlerDictionary[_apiName](self, **_kwargs)
        except Exception as e:
            print(f"[ModelFoVTimeBased]: An unhandled API request has been received by {self.__ownernode.nodeID}: ", e)
        
        return _ret
    

    def __init__(
        self, 
        _ownernodeins: INode, 
        _loggerins: ILogger,
        _patternPath: str,
        _accessGenerationFunction: str,
        _schedulingStrategyFunction: str,
        _accessToGen: int
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

        self.__ownernode = _ownernodeins
        self.__logger = _loggerins
        self.__patternPath = _patternPath
        self.__accessToGen = _accessToGen

        # Load access file into a dictionary
        with open(self.__patternPath, 'r') as f:
            self.__patternDict = json.load(f)
        self.__patternPath

        # Map strategy functions
        self.__accessGenerationFunction: function = self.__accessGenerationFunctionDictionary[_accessGenerationFunction]
        self.__schedulingStrategyFunction: function = self.__schedulingStrategyFunctionDictionary[_schedulingStrategyFunction]
        

    def Execute(self) -> None:
        # Generate some accesses
        requests = self.__accessGenerationFunction(self.__patternDict, self.__accessToGen)
        # Schedule one satellite
        targetSatellite: INode = self.__schedulingStrategyFunction(self.__ownernode, self.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES))
        if targetSatellite is None:
            self.__logger.write_Log(f"[Warning]: Out of service", ELogType.LOGINFO, self.__ownernode.timestamp)
            return
        # Send requests to the scheduled satellite
        cdn_cache_hit_results = targetSatellite.has_ModelWithName('ModelCDNProvider').call_APIs('handle_requests', requests=requests)
        self.__logger.write_Log(f"[Requests]:{requests}", ELogType.LOGINFO, self.__ownernode.timestamp)
        self.__logger.write_Log(f"[Hit rate]:{targetSatellite.nodeID},{len([0 for i in cdn_cache_hit_results if i])/len(cdn_cache_hit_results)}", ELogType.LOGINFO, self.__ownernode.timestamp)
        

    def __send_cdn_requests(self):
        requests = []
        actual_latency = []
        
        with open(self.__file_path, 'r') as f:
            for line in f:
                requests.append(line.split(' ')[0])
                actual_latency.append(line.split(' ')[1])
        in_view = self.__ownernode.has_ModelWithName('ModelHelperFoV').call_APIs('get_View', _isDownView = False, _targetNodeTypes=[ENodeType.SAT], _myTime=self.__ownernode.timestamp, _myLocation=self.__ownernode.get_Position())
        if len(in_view) == 0:
            self.__logger.write_Log(f"No SAT in view", ELogType.LOGDEBUG, self.__ownernode.timestamp)
            self.__logger.write_Log(f"{actual_latency}", ELogType.LOGINFO, self.__ownernode.timestamp)
        else:
            # Take the first satellite to check cache for now
            # Get the node topology ID and find the corresponding topology (node list) from the manager
            _topologyID = self.__ownernode.topologyID
            _topologies = self.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
            
            _myTopology:ITopology = None
            for _topology in _topologies:
                if _topology.id == _topologyID:
                    _myTopology = _topology
                    break
            
            assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
            target_sat = _myTopology.get_Node(in_view[0])
            cdn_cache_hit_results = target_sat.has_ModelWithName('ModelCDNProvider').call_APIs('check_cdn_cache', requests=requests)
            assert len(cdn_cache_hit_results) == len(requests), "[Simulation Error]: hit result must have same length with length of requests"
            for i in range(len(cdn_cache_hit_results)):
                if cdn_cache_hit_results[i]:
                    actual_latency[i] = float(10)
                else:
                    actual_latency[i] = float(actual_latency[i]) + 10
            self.__logger.write_Log(f'RRT Latency:{actual_latency}', ELogType.LOGINFO, self.__ownernode.timestamp, self.iName)
    

    __accessGenerationFunctionDictionary = {
        'generate_by_distribution': generateByDistribution
    }

    __schedulingStrategyFunctionDictionary = {
        'schdeule_by_largest_elevation': schduleLargestElevation
    }


def init_ModelCDNUser(
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
    assert _modelArgs.access_pattern_file is not None
    assert _modelArgs.access_generation_function is not None
    assert _modelArgs.scheduling_strategy_function is not None

    numAccessToGen = 100
    if "num_access_to_gen" in _modelArgs:
        numAccessToGen = int(_modelArgs.num_access_to_gen)

    return ModelCDNUser(_ownernodeins, 
                        _loggerins, 
                        _modelArgs.access_pattern_file, 
                        _modelArgs.access_generation_function, 
                        _modelArgs.scheduling_strategy_function,
                        numAccessToGen)
