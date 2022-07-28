import random
import networkx as nx
import matplotlib.pyplot as plt
import pickle
import numpy as np
from matplotlib.pyplot import pause
import shapefile
from matplotlib.artist import Artist

def shipFuelFlow(graph,time):
    #port pair list to skip as you have already done that edge
    skipNodeList = []
    
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for node2 in modelDataset["Input Parameters"]["ports"]:
            totalShipFlow = sum(shipFlowDataset[ship,node1,node2,time] for ship in modelDataset["Input Parameters"]["ships"])

            #if port pair in node list, only change the edge if there is any flow
            if(([node1,node2] not in skipNodeList) or (totalShipFlow != 0)):
                try:
                    graph[node1][node2]["weight"] = 5*totalShipFlow/maxFuelFlow
                except KeyError:
                    continue
                #make sure you don't accidentally reset the edge
                skipNodeList.append([node2,node1])

    return graph

def portFuelFlow(graph,time):
    for port in modelDataset["Input Parameters"]["ports"]:
        for region in modelDataset["Input Parameters"]["regions"]:
            if((storageFlowDataset[port,region,time] is not None)):
                graph[port][region]["weight"] = 5*np.abs(storageFlowDataset[port,region,time])/maxFuelFlow


    return graph

def nodeSizes(time):
    nodeNames = modelDataset["Input Parameters"]["ports"] + modelDataset["Input Parameters"]["regions"]
    
    nodeSizeList = []
    for node in nodeNames:
        if(node in modelDataset["Input Parameters"]["ports"]):
            nodeSizeList.append(5*fuelAvailDataset[node,time])
        else:
            nodeSizeList.append(5*np.abs(fuelDemandDataset[node][time]))
    
    return(nodeSizeList)

def resetGraph(graph):
    #resetting edges
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for node2 in modelDataset["Input Parameters"]["ports"]:
            if(networkDataset[node1,node2] > 0):
                graph.add_edge(node1,node2,weight=0,color="black")
            
    #resetting edges
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for region in modelDataset["Input Parameters"]["regions"]:
            if((portRegionDataset[node1,region ] > 0)) :
                graph.add_edge(node1,region,weight=0,color="black")
    return(graph)

def removeEdges(graph):
    #first removing edges
    edgeList = graph.edges
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for node2 in modelDataset["Input Parameters"]["ports"]:
            if((node1,node2) in edgeList):
                graph.remove_edge(node1,node2)
                
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for region in modelDataset["Input Parameters"]["regions"]:
            if((node1,region) in edgeList):
                graph.remove_edge(node1,region)

    return(graph)



#reading in the global country map
fileName =  "shapeFile/world-administrative-boundaries"
sf = shapefile.Reader(fileName) # whichever file
fig = plt.figure(figsize=(8,6))
ax = fig.add_subplot(111)


#setting up graph visualization 
minLonX =-20
maxLonX = 150
minLatY = 0
maxLatY = 90

#graph delay for animation in seconds
graphDelay = 1.5

#scaling factor for edge and node displays
scalingSize = 5


#drawing map
plt.xlim([minLonX, maxLonX])
plt.ylim([minLatY, maxLatY])
for shape in sf.shapes():
    points = np.array(shape.points)
    intervals = list(shape.parts) + [len(shape.points)]

    for (i, j) in zip(intervals[:-1], intervals[1:]):
        #ax.plot(*zip(*points[i:j]),color="gray",linewidth=.25, alpha=0.3)
        ax.fill(*zip(*points[i:j]),color="green", alpha=0.3)
#reading in model output data
pkl_file = open('../modelOutputs/testRun.pkl', 'rb')

modelDataset = pickle.load(pkl_file)
pkl_file.close()


storageFlowDataset = modelDataset["Fuel Flow Storage"]
shipFlowDataset = modelDataset["Fuel Flow Ship"]
fuelAvailDataset = modelDataset["Port Fuel Avail"]
fuelDemandDataset = modelDataset["Input Parameters"]["demand"]

#adding nodes to graph
graph = nx.Graph()
latDict = {
    "KSA": 24,
    "JEDDAH": 22.4,
    "DAMMAM": 26,
    "TOKYO": 34.83,
    "JP":38.3,
    "HAMBURG": 53.5,
    "DE": 50
}
lonDict = {
    "KSA": 45.66,
    "JEDDAH": 39.6,
    "DAMMAM": 50,
    "TOKYO": 138,
    "JP":140,
    "HAMBURG": 9.96,
    "DE": 10.52
}



colorMap = []
for node in modelDataset["Input Parameters"]["ports"]:
    graph.add_node(node, Position=(lonDict[node],latDict[node]))
    colorMap.append("tab:blue")

#adding region nodes
for node in modelDataset["Input Parameters"]["regions"]:
    graph.add_node(node, Position=(lonDict[node],latDict[node]))
    colorMap.append("tab:red")

#adding edges between ports
networkDataset = modelDataset["Input Parameters"]["length"]
for node1 in modelDataset["Input Parameters"]["ports"]:
    for node2 in modelDataset["Input Parameters"]["ports"]:
        if((networkDataset[node1,node2] > 0)) :
            graph.add_edge(node1,node2,weight=1,color="gray")

#adding edges between ports and regions
portRegionDataset = modelDataset["Input Parameters"]["portRegionParameter"]
for node1 in modelDataset["Input Parameters"]["ports"]:
    for node2 in modelDataset["Input Parameters"]["regions"]:
        if((portRegionDataset[node1,node2] > 0)) :
            graph.add_edge(node1,node2,weight=1,color="gray")

#getting max fuel flow
maxStorageFlow = max([value for value in storageFlowDataset.values() if value is not None])
maxShipFlow = max([value for value in shipFlowDataset.values() if value is not None])
maxFuelFlow = max(maxStorageFlow,maxShipFlow)            






for i in np.arange(0,4):
    #graphing initial structure
    nx.draw(graph, pos=nx.get_node_attributes(graph,'Position'),node_color=colorMap,
            node_size=2,edge_color = "gray",ax=ax)
    pause(2)
    ax.collections[0].remove()
    ax.collections[0].remove()
    for time in modelDataset["Input Parameters"]["horizon"]:
        
        #resting graph
        graph = removeEdges(graph)
        graph = resetGraph(graph)
        
        #getting ship and fuel flow
        graph = shipFuelFlow(graph,time)
        graph = portFuelFlow(graph,time)
        
        #getting weights and locations
        weights = nx.get_edge_attributes(graph,'weight').values()
        positions = nx.get_node_attributes(graph,'Position')

        #getUpdated node sizes
        nodeSizeList = nodeSizes(time) 
        
        #drawing updated network flow
        nx.draw(graph, positions, 
                width=list(weights),
                node_color=colorMap,
                node_size=nodeSizeList,
                edge_color = "black",
                ax=ax)
        #plotting time on frame
        frame = plt.text(66,90,str(time))
        pause(graphDelay)
        #removes the previous flow,ship locations, and text for the new update graph
        ax.collections[0].remove()
        ax.collections[0].remove()
        Artist.remove(frame)
        
print("done")