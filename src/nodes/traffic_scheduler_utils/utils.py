import numpy as np
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.utils import Time, Location

def get_view_up(
        topology: ITopology,
        location: Location,
        time: Time,
        target_node_type: list,
        min_elevation = 25
        ) -> list:
    """
    @desc
        This method generates the view for the parent node at the given time and location.
        If the _time and location are not provided it picks the latest location of the node based on the current node time. 
    @param[in]  _kwargs
        keyworded arguments that should contain the following arguments
        @key:  _isDownView
            True: A view of a node in space
            False: A view of a node on ground
        @key:  _targetNodeTypes
            List of the node types that we want to cover in the view.
            Ensure that the consistency has been kept with the view selection.
            For example, DO NOT select the nodes in space if it's a down view
        @key:  _myTime
            Time of the FoV search
        @key:  "_myLocation"
            Location of the node
    @return
        A list containing the visible node IDs of the target node types 
    """
    _ret = None

    _targetNodeTypes = set(target_node_type)
    
    _myNodes = topology.nodes # All the nodes in my topology
    _nodeIDToElevation = np.zeros((len(_myNodes), 2)) # A 2D array for holding nodeID of view target nodes and corresponding elevation angle (initially zero)
    _targetNodeLocations = np.zeros((len(_myNodes), 3)) # A array holding the position vectors of the target nodes
    
    _index = 0
    for _node in _myNodes:
        if _node.nodeType in _targetNodeTypes:
            _targetNodePosition = _node.get_Position(time)
            if _targetNodePosition is not None:
                _nodeIDToElevation[_index] = (_node.nodeID, 0.0)
                _targetNodeLocations[_index] = _targetNodePosition.to_tuple()
                _index = _index + 1
    
    _totalNumOfNodes = _index

    if _totalNumOfNodes > 0:
        # truncate the array as we took it as the size of all nodes in the topology
        _nodeIDToElevation = _nodeIDToElevation[:_totalNumOfNodes, ]
        _targetNodeLocations = _targetNodeLocations[:_totalNumOfNodes, ]
        
        # It's a down view. So all the target nodes should be in the space. So the viewer node must be on the ground
        _groundNodeLoaction = np.asarray(location.to_tuple())

        # calculate the Norm of ground node positions
        _groundNodeLocationNorm = np.linalg.norm(_groundNodeLoaction)

        # calculate the unit vector for ground node locations
        _groundNodeLocationUnitVec = np.divide(_groundNodeLoaction.T, _groundNodeLocationNorm).T

        # Calculate the delta position vectors for the satellite locations and ground node location
        _deltaSatToGroundNodeLocations = _targetNodeLocations - _groundNodeLoaction # the delta vector between the positions of satellites and each ground node

        # calculate the Norm of delta position vectors
        _deltaSatToGroundNodeLocationNorms = np.linalg.norm(_deltaSatToGroundNodeLocations, axis=1)

        # calculate the unit vectors for delta position vectors
        _deltaSatToGroundNodeLocationUnitVec = np.divide(
                                                    _deltaSatToGroundNodeLocations.T, 
                                                    _deltaSatToGroundNodeLocationNorms).T
        # calculate the elevation angles
        _elevations = np.arcsin(np.dot(
                                    _deltaSatToGroundNodeLocationUnitVec, 
                                    _groundNodeLocationUnitVec)) * 180/np.pi
        
        # copy the elevation angles against the node IDs
        _nodeIDToElevation[:_totalNumOfNodes, 1:2] =  _elevations.reshape(_totalNumOfNodes, 1)
    else:
        return _ret
    
    #now we have the node ID vs elevation angle array. We need to find the nodes which are greater than our minimum elevation angle
    _ret = _nodeIDToElevation[_nodeIDToElevation[:, 1] >= min_elevation].tolist()
    return _ret

def schduleLargestElevation(position: Location, timestamp: Time, topology: ITopology, num_to_schedule=1) -> list:
    """
    @desc
        This method return list of node instance with largest elevation of 
        length num_to_schedule
    """ 
    views = get_view_up(topology, position, timestamp, target_node_type = [ENodeType.SAT])
    
    if views is None or len(views) == 0:
        return None
    views = np.asanyarray(views)
    top_idx = np.argsort(views, axis = 0)
    top_idx = top_idx[:, 1][-min(num_to_schedule, len(views)):]
    ret = [topology.get_Node(int(views[top_idx[i]][0])) for i in range(len(top_idx))]
    return ret 