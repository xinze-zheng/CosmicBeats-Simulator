from src.models.imodel import IModel, EModelTag
from src.nodes.inode import INode, ENodeType
from src.nodes.itopology import ITopology
from src.sim.imanager import EManagerReqType
from src.nodes.traffic_scheduler_utils.utils import get_view_up
import numpy as np
def schduleLargestElevation(node: INode, topology, num=1) -> list:
    _topologyID = node.topologyID
    _topologies = topology
    
    _myTopology:ITopology = None
    for _topology in _topologies:
        if _topology.id == _topologyID:
            _myTopology = _topology
            break
    
    assert _myTopology is not None, "[Simulation Error]: A topology should have been found for an existing node"
    views = node.has_ModelWithName('ModelHelperFoVWithElevation').call_APIs('get_View', _isDownView = False, _targetNodeTypes=[ENodeType.SAT], _myTime=node.timestamp, _myLocation=node.get_Position())
    views_new = get_view_up(_myTopology, node.get_Position(), node.timestamp, target_node_type = [ENodeType.SAT])
    
    if views is None or len(views) == 0:
        assert views == views_new
        return None
    assert len(views) == len(views_new)
    for i in range(len(views)):
        assert views[i] == views_new[i]
    views = np.asanyarray(views)
    top_idx = np.argsort(views, axis = 0)
    top_idx = top_idx[:, 1][-min(num, len(views)):]
    ret = [_myTopology.get_Node(int(views[top_idx[i]][0])) for i in range(len(top_idx))]
    return ret 
