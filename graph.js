// This method is responsible for drawing the graph, returns the drawn network
try {
    require('vis-network');
} catch (e) { }

function drawGraph(pNodes, pEdges, options, elementId) {
    // parsing and collecting nodes and edges from the python
    var nodes = new vis.DataSet(pNodes);
    var edges = new vis.DataSet(pEdges);
    var container = document.getElementById(elementId);

    // adding nodes and edges to the graph
    var data = {nodes: nodes,
                edges: edges};

    var network = new vis.Network(container, data, options);

    setTimeout(function() {
      var options = {offset: {x:0, y:0},
        duration: 2000,
      };
      network.fit({animation: options});
    }, 1000);

    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            var nodeId = params.nodes[0];
            var networkInfo = document.getElementById("networkInfo");
            networkInfo.innerText = "Выбрана вершина \nid: " + nodeId + "\n" + nodes.get(nodeId).title;
            nodeImage.src = nodes.get(nodeId).image;
            nodeHref.href = "https://vk.com/id" + nodeId;
            nodeHref.style.display = 'block';
        }
        else if (params.edges.length > 0) {
            var edgeId = params.edges[0];
            var networkInfo = document.getElementById("networkInfo");
            networkInfo.innerText = "Выбрана связь \n" + edges.get(edgeId).title + " \nВес: " + edges.get(edgeId).value;
            nodeHref.href = "";
            nodeHref.style.display = 'none';
        }
    });

    network.on("doubleClick", function (params) {
        edges.update(pEdges);
        if (params.nodes.length > 0) {
            var allEdges = edges.get({ returnType: "Object" });
            var selectedNodeId = params.nodes[0];
            var connectedEdges = network.getConnectedEdges(selectedNodeId);

            var updateArray = [];
            for (var edgeId in allEdges) {
                if (!connectedEdges.includes(edgeId)) {
                    allEdges[edgeId].color = "rgba(200,200,200,0.5)";
                    updateArray.push(allEdges[edgeId]);
                }
            }
            edges.update(updateArray);
        }
    });
}