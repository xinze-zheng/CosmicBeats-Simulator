'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.

Created by: Tusher Chakraborty
Created on: 12 Oct 2022
@desc
    This module implements the Topology class that inherits the ITopology
'''
from io import StringIO

from src.nodes.inode import ENodeType, INode
from src.nodes.itopology import ITopology

import json
from collections import deque

class Topology(ITopology):
    '''
    Topology class that holds the nodes. It inherits the ITopology interface.
    '''
    __nodes: 'list[INode]'
    __id: int
    __name: str
    __global_cache: dict
    # ISL topology
    __isl_graph: dict
    __isl_dist: dict

    NEXT_ISL = 0
    PREV_ISL = 1
    LEFT_ISL = 2
    RIGHT_ISL = 3
    ALL_NEIGHBOR = 4

    @property
    def id(self) -> int:
        '''
        @type
            Integer
        @desc
            ID of the topology. Each topology should have an unique ID
        '''
        return self.__id
    
    @property
    def global_cache(self) -> dict:
        return self.__global_cache
    
    @property
    def isl_graph(self) -> dict:
        return self.__isl_graph

    @property
    def name(self) -> str:
        '''
        @type
            String
        @desc
            Name of the topology
        '''
        return self.__name
    
    def add_Node(
            self, 
            _node: INode):
        '''
        @desc
            Adds the node given in the argument to the list
        @param[in]  _node
            Node to be added to the list
        '''
        if(_node is not None):
            self.__nodes.append(_node)
            if _node.nodeID not in self.__nodeIDToNodeMap:
                self.__nodeIDToNodeMap[_node.nodeID] = _node
            else:
                raise Exception("Node ID already exists in the topology")
    
    def get_Node(
            self, 
            _nodeId: int) -> INode:
        '''
        @desc
            Get a node from this topology with node id.
        @param[in]  _nodeId
            ID of the node that is being looked for
        @return
            INode instance of the node. None if not found
        '''
        return self.__nodeIDToNodeMap.get(_nodeId, None)
    
    def get_NodesOfAType(
            self, 
            _nodeType: ENodeType) -> 'list[INode]':
        '''
        @desc
            Get the list of all nodes of a type provided in the argument
        @param[in]  _nodeType
            Type of the node
        @return
            List of the nodes
        '''
        _ret: 'list[INode]' = []
        for _node in self.__nodes:
            if(_node.nodeType == _nodeType):
                _ret.append(_node)
        return _ret
    
    def get_ISL_dist(self, nodeFrom: int, nodeTo: int):
        # BFS for shortest path
        if nodeFrom in self.__isl_dist:
            return self.__isl_dist[nodeFrom][nodeTo]

        visited = set()
        queue = deque()
        queue.append([str(nodeFrom), 0])
        visited.add(str(nodeFrom))
        self.__isl_dist[nodeFrom] = {}
        # print(queue)
        while queue:
            current = queue.popleft()
            # print(current)
            dist = current[1]
            current_node = current[0]
            self.__isl_dist[nodeFrom][int(current_node)] = int(dist)
            for neighbor in self.__isl_graph[current_node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append([neighbor, dist + 1])
        return self.__isl_dist[nodeFrom][nodeTo]

    def get_shortest_replica(self, nodeFrom: int, request: str):
        if nodeFrom not in self.__isl_dist:
            self.get_ISL_dist(nodeFrom, nodeFrom)
        min_hop = 100000
        for remote_replica in self.__global_cache[request]:
            hop = self.__isl_dist[nodeFrom][int(remote_replica)]
            min_hop = min(min_hop, hop)
        return min_hop
    
    def get_ISL_neighbor(self, node: int):
        # Return in the form of [next, prev, left, right]
        return self.__isl_graph[str(node)]



        
    @property
    def nodes(self) -> 'list[INode]':
        '''
        @type
            List of INode
        @desc
            All the nodes of this topology instance
        '''
        return self.__nodes
    
    def __init__(
            self, 
            _name: str, 
            _id: int) -> None:
        '''
        @desc
            Constructor of the topology
        @param[in]  _name
            Name of the topology
        @param[in]  _id
            ID of the topology
        '''
        self.__name = _name
        self.__id = _id
        self.__nodes = []
        self.__nodeIDToNodeMap = {}
        self.__global_cache = {}
        self.__isl_dist = {}

    def __init__(
            self, 
            _name: str, 
            _id: int,
            _isl_topology: str) -> None:
        '''
        @desc
            Constructor of the topology
        @param[in]  _name
            Name of the topology
        @param[in]  _id
            ID of the topology
        '''
        self.__name = _name
        self.__id = _id
        self.__nodes = []
        self.__nodeIDToNodeMap = {}
        self.__global_cache = {}
        self.__isl_dist = {}

        if _isl_topology is not None: 
            with open(_isl_topology, 'r') as f:
                self.__isl_graph = json.load(f)

    def __str__(self) -> str:
        '''
        @desc
            Overriding the __str__() method
        '''
        _string = "".join(["Topology ID: ", str(self.__id), ", ",
                "Topology name: ", self.__name, ", ",
                "Number of nodes: ", str(len(self.__nodes)), "\n"])
        
        _stringIOObject = StringIO(_string)
        for _node in self.__nodes:
            _stringIOObject.write(_node.__str__())
        
        return _stringIOObject.getvalue()