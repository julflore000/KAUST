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
            if((totalShipFlow != 0) or ([node1,node2] not in skipNodeList)):
                try:
                    graph[node1][node2]["weight"] = 2*totalShipFlow/maxFuelFlow
                except KeyError:
                    continue
                #make sure you don't accidentally reset the edge
                skipNodeList.append([node2,node1])

    return graph

def portFuelFlow(graph,time):
    for port in modelDataset["Input Parameters"]["ports"]:
        for region in modelDataset["Input Parameters"]["regions"]:
            if((storageFlowDataset[port,region,time] is not None)):
                graph[port][region]["weight"] = 2*np.abs(storageFlowDataset[port,region,time])/maxFuelFlow


    return graph

def nodeSizes(time):
    nodeNames = modelDataset["Input Parameters"]["ports"] + modelDataset["Input Parameters"]["regions"]
    
    nodeSizeList = []
    for node in nodeNames:
        if(node in modelDataset["Input Parameters"]["ports"]):
            nodeSizeList.append(fuelAvailDataset[node,time])
        else:
            nodeSizeList.append(np.abs(fuelDemandDataset[node][time]))
    
    return(nodeSizeList)

def resetGraph(graph):
    #resetting edges
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for node2 in modelDataset["Input Parameters"]["ports"]:
            if(networkDataset[node1,node2] > 0):
                graph.add_edge(node1,node2,color="blue")
                
        
    return(graph)

def removeEdges(graph):
    #first removing edges
    edgeList = graph.edges
    for node1 in modelDataset["Input Parameters"]["ports"]:
        for node2 in modelDataset["Input Parameters"]["ports"]:
            if((node1,node2) in edgeList):
                graph.remove_edge(node1,node2)
    return(graph)



#reading in the global country map
fileName =  "shapeFile/world-administrative-boundaries"
sf = shapefile.Reader(fileName) # whichever file
fig = plt.figure()
ax = fig.add_subplot(111)


#setting up to 
minLonX =-20
maxLonX = 150
minLatY = 0
maxLatY = 90


#drawing map
plt.xlim([minLonX, maxLonX])
plt.ylim([minLatY, maxLatY])
for shape in sf.shapes():
    points = np.array(shape.points)
    intervals = list(shape.parts) + [len(shape.points)]

    for (i, j) in zip(intervals[:-1], intervals[1:]):
        ax.plot(*zip(*points[i:j]),color="gray",linewidth=.5)


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
    "TOKYO": 34,
    "JP":35.7,
    "BUSAN": 35.5 ,
    "SK": 37.35,
    "HAMBURG": 53.5,
    "DE": 50 
}
lonDict = {
    "KSA": 45.66,
    "JEDDAH": 39.6,
    "TOKYO": 138,
    "JP":139.8,
    "BUSAN": 129.28,
    "SK": 127,
    "HAMBURG": 9.96,
    "DE": 10.52 
}

#graph delay for animation in seconds
graphDelay = 1


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
            graph.add_edge(node1,node2,weight=1)

#adding edges between ports and regions
portRegionDataset = modelDataset["Input Parameters"]["portRegionParameter"]
for node1 in modelDataset["Input Parameters"]["ports"]:
    for node2 in modelDataset["Input Parameters"]["regions"]:
        if((portRegionDataset[node1,node2] > 0)) :
            graph.add_edge(node1,node2,weight=1)

#getting max fuel flow
maxStorageFlow = max([value for value in storageFlowDataset.values() if value is not None])
maxShipFlow = max([value for value in shipFlowDataset.values() if value is not None])
maxFuelFlow = max(maxStorageFlow,maxShipFlow)            


#graphing initial structure
nx.draw(graph, pos=nx.get_node_attributes(graph,'Position'),node_color=colorMap,
        node_size=2,ax=ax)


for i in np.arange(0,3): 
    for time in modelDataset["Input Parameters"]["horizon"]:
        graph = resetGraph(graph)
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
                ax=ax)
        frame = plt.text(66,90,str(time))
        pause(graphDelay)
        #removes the previous flow,ship locations, and text for the new update graph
        ax.collections[1].remove()
        ax.collections[1].remove()
        Artist.remove(frame)
        
print("done")