// This method is responsible for drawing the graph, returns the drawn network
try {
    require('vis-network');
} catch (e) { }
function drawGraph(pNodes, pEdges, nodeId) {
    var edges;
    var nodes;
    var network;
    var container;
    var options, data;
    var container = document.getElementById(nodeId);

    // parsing and collecting nodes and edges from the python
    nodes = new vis.DataSet(pNodes);
    edges = new vis.DataSet(pEdges);

    // adding nodes and edges to the graph
    data = {nodes: nodes, edges: edges};

    var options = {
        "autoResize" : true,
        "configure": {
            "enabled": false,
        },
        "edges": {
            "color": {
                "inherit": true
            },
            "smooth": {
                "enabled": false,
                "type": "continuous"
            }
        },
        "interaction": {
            "dragNodes": true,
            "hideEdgesOnDrag": false,
            "hideNodesOnDrag": false
        },
        "physics": {
            "barnesHut": {
                "avoidOverlap": 0.1,
                "centralGravity": 2,
                "damping": 0.09,
                "gravitationalConstant": -80000,
                "springConstant": 0.01,
                "springLength": 250
            },
            "enabled": true,
            "stabilization": {
                "enabled": true,
                "fit": true,
                "iterations": 1000,
                "onlyDynamicEdges": false,
                "updateInterval": 50
            }
        }
    };

    network = new vis.Network(container, data, options);
}