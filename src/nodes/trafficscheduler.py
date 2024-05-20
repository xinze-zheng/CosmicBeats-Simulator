'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 08 Nov 2022
@desc
    This module implements the basic ground station (GS) class
'''
from io import StringIO
from src.nodes.inode import INode, ENodeType
from src.utils import Time, Location
from src.simlogging.ilogger import ILogger, ELogType
from src.models.imodel import IModel, EModelTag
from src.sim.imanager import IManager
from src.sim.imanager import EManagerReqType
from src.nodes.itopology import ITopology

import concurrent.futures

import numpy as np
from src.nodes.traffic_scheduler_utils.utils import schduleLargestElevation
from src.models.models_cdn_user.access_generation_function.generate_by_distribution import generateByDistribution 
import json

class TrafficScheduler(INode):
    '''
    This class implements the basic ground station functionalities.
    It inherits INode interface
    '''
    
    __nodetype = ENodeType.TRAFFIC_SCHEDULER
    __nodeid: int
    __topologyid: int
    __managerinstance = None
    __logger: ILogger
    __timestamp: Time
    __endTimeStamp: Time
    __timedelta: float              #time granularity for the simulation
    __models: 'list[IModel]'          # List of models
    
    
            
    @property
    def iName(self)-> str:
        """
        @type 
            str
        @desc
            A string representing the name of the node class. For example, NodeSatellite 
            Note that the name should exactly match to your class name. 
        """
        return self.__class__.__name__
    
    @property
    def nodeType(self) -> ENodeType:
        """
        @type
            ENodeType
        @desc
            The node type for the implemented node class
        """
        return self.__nodetype
    
    @property
    def nodeID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of a node in the topology. It basically distinguishes a node from another node.  
        """
        return self.__nodeid
    
    @property
    def topologyID(self) -> int:
        """
        @type 
            int
        @desc
            The ID of the topology that the node instance is part of
        """
        return self.__topologyid
    
    @property
    def timestamp(self) -> Time:
        """
        @type
            Time
        @desc
            Current timestamp of the node instance 
        """
        return self.__timestamp
    @property
    def simStartTime(self) -> Time:
        """
        @type
            Time
        @desc
            Start timestamp of the node instance for simulation 
        """
        return self.__startTimeStamp

    @property
    def simEndTime(self) -> Time:
        """
        @type
            Time
        @desc
            End timestamp of the node instance for simulation
        """
        return self.__endTimeStamp
    
    @property
    def deltaTime(self) -> float:
        """
        @type
            Float
        @desc
            time granularity for the simulation of this node (in seconds).
            Time gap between two simulation epochs
        """
        return self.__timedelta
    
    @property
    def managerInstance(self):
        """
        @type
            Manager class
        @desc
            Manager instance of the simulator that is holding this node instance  
        """
        return self.__managerinstance

    def add_Models(
            self, 
            _modelsToAdd: 'list[IModel]'):
        """
        @desc
            This method adds a model to the node
        @param[in]  _modelsToAdd    
           The instance of the model to be added
        """
        assert _modelsToAdd is not None

        self.__models.extend(_modelsToAdd)
    
    def has_ModelWithTag(
            self, 
            _modelTag: EModelTag) -> IModel:
        """
        @desc
            This method checks whether this node instance has a model implemented having the provided model tag.
            If so, it returns the model.
        @param[in]  _modelTag    
           Tag of the model that is being looked for
        @return
            Instance of the model if it was found.
            Otherwise, None 
        """
        _ret = None

        for _model in self.__models:
            if _model.modelTag.value == _modelTag.value:
                _ret = _model
                break
        
        return _ret
    
    def get_Models(self) -> 'list[IModel]':
        """
        @desc
            This method returns the list of models implemented by this node instance
        @return
            List of models implemented by this node instance
        """
        return self.__models
    
    def has_ModelWithName(
            self, 
            _modelName: str) -> IModel:
        """
        @desc
            This method checks whether this node instance has a model implemented having the provided model implementation name (iName).
            If so, it returns the model.
        @param[in]  _modelName    
           Implementation name (iName) of the model that is being looked for
        @return
            Instance of the model if it was found.
            Otherwise, None 
        """
        _ret = None

        for _model in self.__models:
            if _model.iName == _modelName:
                _ret = _model
                break
        
        return _ret

    def add_ManagerInstance(
            self, 
            _managerIns: IManager):
        '''
        @desc
            Adds manager instance to this node instance
        @param[in]  _managerIns
            Manager instance as IManager
        '''
        assert _managerIns is not None
        self.__managerinstance = _managerIns
    
    def get_Position():
        pass

    def update_Position():
        pass
    
    def __init__(
            self, 
            _nodeID: int, 
            configs: list,
            _topologyID: int, 
            _timeDelta: float, 
            _timeStamp: Time, 
            _endtime: Time, 
            _Logger: ILogger, 
            _hop_to_check: int,
            *_additionalArgs) -> None:
        '''
        @desc
            Constructor of the satellite basic class
        @param[in]  _nodeID
            The ID of a node in the topology. It basically distinguishes a node from another node.
        @param[in]  _topologyID
            The ID of the topology that the node instance is part of
        @param[in]  _location
            Location of the ground station on earth
        @param[in]  _timeDelta
            time granularity for the simulation of this node (in seconds)
        @param[in]  _timeStamp
            Timestamp for the node. Typically, start time 
        @param[in]  _endtime
            End timestamp of the simulation for this node
        @param[in]  _Logger
            Logger instance
        '''
        self.__nodeid = _nodeID
        self.__topologyid = _topologyID
        self.__timedelta = _timeDelta
        self.__timestamp = _timeStamp.copy()
        self.__startTimeStamp = _timeStamp
        self.__endTimeStamp = _endtime
        self.__logger = _Logger
        self.__models = []
        self.__requesters = []
        self.__myTopology = None

        for config in configs:
            pattern: dict
            with open(config.pattern_file, 'r') as f:
                pattern = json.load(f)
            self.__requesters.append(Requester(
                config.lat,
                config.lon,
                config.elev,
                config.num_request,
                schduleLargestElevation,
                generateByDistribution,
                config.load_balance_count,
                pattern,
                self.__logger,
                _hop_to_check
            ))

    
    def Execute(self) -> bool:
        """
        @desc
            This method executes the models of the node instance one by one. 
            This is one time execution of the models.
        @return
            True:   If the execution is successful
            False:  Otherwise
        """
        _ret = False
        for requester in self.__requesters:
            if requester.topology is None:
                topologies = self.__managerinstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
                _myTopology:ITopology = None
                for _topology in topologies:
                    if _topology.id == self.__topologyid:
                        _myTopology = _topology
                        break
                if self.__myTopology is None:
                    self.__myTopology = _myTopology
                for requester in self.__requesters:
                    requester.add_topology(_myTopology)
                break
            else:
                break

        if self.__timestamp <= self.__endTimeStamp:
            self.__timestamp.add_seconds(self.__timedelta)
            self.__logger.write_Log("Executing", ELogType.LOGDEBUG, self.__timestamp)
            
            # with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            #     _results = []
            #     #Let's execute all the nodes in parallel
            #     for requester in self.__requesters:
            #         _result = executor.submit(requester.send_requests, self.__timestamp)
            #         _results.append(_result)
                
            #     #Once all the threads are done, we can check if there are any exceptions that were raised, then we can raise them
            #     #If we don't do this, then the exceptions will be ignored and the nodes will be out of sync
            #     for _result in _results:
            #         _result.result() 
            for requester in self.__requesters:
                requester.send_requests(self.__timestamp)
            
            # Call post hook
            sats = self.__myTopology.get_NodesOfAType(ENodeType.SAT)
            for sat in sats:
                sat.has_ModelWithName('ModelCDNProvider').call_APIs('post_epoch_hook') 
           # update the time of the node
            _ret = True
        
        return _ret
    
    def ExecuteCntd(self):
        """
        @desc
        This method executes the models of the node instance one by one continuously until
        it reaches simulation end time.
        """
        while self.__timestamp <= self.__endTimeStamp:
            self.__logger.write_Log("Executing", ELogType.LOGDEBUG, self.__timestamp)
            
            # execute the models one by one, if any
            for _model in self.__models:
                _model.Execute() 

            # update the time of the node
            self.__timestamp.add_seconds(self.__timedelta)
    
    def __str__(self):      

        _nodeDetails = "".join(["GS node ID:: ", str(self.__nodeid), ", ",
                        "Topology ID: ", str(self.__topologyid), ", "
                        "Current time: ", self.__timestamp.to_str(), ", ",
                        "End time: ", self.__endTimeStamp.to_str(), ", ",
                        "Models (if any): "])

        _stringIOObject = StringIO(_nodeDetails)
        for _model in self.__models:
            _stringIOObject.write(_model.__str__())
            _stringIOObject.write(", ")

        return _stringIOObject.getvalue()

def init_TrafficScheduler(
        _nodeDetails, 
        _timeDetails, 
        _topologyID, 
        _logger)-> INode:
    '''
    @desc
        This method initializes an instance of SatelliteBasic class
    @param[in]  _nodeDetails
        It's a converted JSON object containing the node related info. 
        The JSON object must have the literals as follows (values are given as example).
        {
            "nodeid": 1,
            "configs": [
                {
                    lat: ,
                    lon: ,
                    alt: ,
                    num_req: ,
                    min_elevation: ,
                    schedule_trategy: ,
                    load_balance_count: ,
                    access_pattern: 
                }
            ] 
        }
    @param[in]  _timeDetails
        It's a converted JSON object containing the simulation timing related info. 
        The JOSN object must have the literals as follows (values are given as example).
        {
            "starttime": "2022-10-14 12:00:00",
            "endtime": "2022-10-14 13:00:00",
            "delta": 5.0
        }
    @param[in]  _topologyID
        The ID of the topology that the node instance is part of
    @param[in]  _logger
        Logger instance
    @return
        Created instance of the class
    '''
    # Check whether the arguments contain required parameter

    assert _timeDetails is not None

    assert _timeDetails.starttime != ''
    _simStartTime = Time().from_str(_timeDetails.starttime)

    assert _timeDetails.endtime != ''
    _simEndTime = Time().from_str(_timeDetails.endtime)

    assert _timeDetails.delta > 0
    _timeDelta = _timeDetails.delta

    assert _logger is not None

    assert _nodeDetails is not None

    assert len(_nodeDetails.configs) > 0


    _newNode = TrafficScheduler(
                _nodeDetails.nodeid, 
                _nodeDetails.configs,
                _topologyID, 
                _timeDelta, 
                _simStartTime, 
                _simEndTime, 
                _logger, 
                _nodeDetails.hop_to_check,
                _nodeDetails.additionalargs)
    return _newNode

class Requester():

        __lat: float 
        __lon: float
        __alt: float
        __num_request: float
        __schedule_strategy: callable
        __load_balance_count: int
        __pattern: dict
        __topology: dict

        @property
        def topology(self):
            return self.__topology
        
        def add_topology(self, topology):
            self.__topology = topology

        def __init__(self,
            _lat,
            _lon,
            _alt,
            _num_request,
            _schedule_strategy,
            _access_generation_function,
            _load_balance_count,
            _pattern,
            _logger,
            _hop_to_check = 1
            ) -> None:

            self.__lat = _lat
            self.__lon = _lon
            self.__alt = _alt
            self.__num_request = _num_request
            self.__schedule_strategy = _schedule_strategy
            self.__access_generation_function = _access_generation_function
            self.__load_balance_count = _load_balance_count
            self.__pattern = _pattern
            self.__topology = None 
            self.__hop_to_check = _hop_to_check
            
            self.__location = Location().from_lat_long(_lat, _lon, _alt)
            self.__logger = _logger
        
        def send_requests(self, timestamp: Time):
            total_requests = self.__access_generation_function(pattern = self.__pattern, numToGen = self.__num_request, probOneHitter=0)
            # Can change to kwarg in the future
            targetSatellites: list = self.__schedule_strategy(self.__location, 
                                                                        timestamp,
                                                                        self.__topology,
                                                                        self.__load_balance_count) 
            if targetSatellites is None:
                self.__logger.write_Log(f"[Warning]: Out of service", ELogType.LOGINFO, timestamp)
                return
            requestsPerSat = np.array_split(total_requests, len(targetSatellites))
            for i in range(len(targetSatellites)):
                targetSatellite = targetSatellites[i]
                requests = requestsPerSat[i]
                res = targetSatellite.has_ModelWithName('ModelCDNProvider').call_APIs('handle_requests', requests=requests, hop_to_check=self.__hop_to_check)
                self.__logger.write_Log(f'[Request Result]:{targetSatellite.nodeID}, {res}', ELogType.LOGALL, timestamp, f"({self.__lat}, {self.__lon})")