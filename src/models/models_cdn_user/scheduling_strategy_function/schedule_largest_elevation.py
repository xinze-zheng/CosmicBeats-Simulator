from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.sim.imanager import EManagerReqType
import numpy as np
def schduleLargestElevation(node: INode, topology) -> INode:
    _topologyID = node.topologyID
    _topologies = topology
    
    _myTopology:ITopology = None
    for _topology in _topologies:
        if _topology.id == _topologyID:
            _myTopology = _topology
            break
    
    assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
    views = node.has_ModelWithName('ModelHelperFoVWithElevation').call_APIs('get_View', _isDownView = False, _targetNodeTypes=[ENodeType.SAT], _myTime=node.timestamp, _myLocation=node.get_Position())
    if views is None or len(views) == 0:
        return None
    views = np.asanyarray(views)
    return _myTopology.get_Node(views[np.argmax(views[:,1])][0])
