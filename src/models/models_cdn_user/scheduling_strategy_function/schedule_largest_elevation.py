from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.sim.imanager import EManagerReqType
import numpy as np
def schduleLargestElevation(node: INode) -> INode:
    _topologyID = node.topologyID
    _topologies = node.__ownernode.managerInstance.req_Manager(EManagerReqType.GET_TOPOLOGIES)
    
    _myTopology:ITopology = None
    for _topology in _topologies:
        if _topology.id == _topologyID:
            _myTopology = _topology
            break
    
    assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
    views = node.has_ModelWithName('ModelFovTimeBased').call_APIs('get_View', _isDownView = False, _targetNodeTypes=[ENodeType.SAT], _myTime=node.timestamp, _myLocation=node.get_Position())
    elevations = [getElevation(node, _myTopology.get_Node(views[i])) for i in range(len(views))]
    return _myTopology.get_Node(views[np.argmax(elevations)])


def getElevation(curNode: INode, satelliteNode: INode):
    _myLocation = curNode.get_Position()
    _targetNodeLocations = satelliteNode.get_Position()

    _groundNodeLoaction = np.asarray(_myLocation.to_tuple())

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
    return _elevations