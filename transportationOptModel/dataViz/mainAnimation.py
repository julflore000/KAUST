import random
import networkx as nx
import matplotlib.pyplot as plt
import pickle
import numpy as np
from matplotlib.pyplot import pause
import shapefile
#from mpl_toolkits.basemap import Basemap as Basemap
global storageFlowDataset,shipFlowDataset

#setting up basemap global map


fileName =  "shapeFile/world-administrative-boundaries"
sf = shapefile.Reader(fileName) # whichever file
fig = plt.figure()
ax = fig.add_subplot(111)



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

#adding nodes to graph
graph = nx.Graph()
latDict = {
    "KSA": 28.5,
    "P1": 21,
    "T1": 11,
    "T2":3,
    "T3":30.6,
    "P2":33.4,
    "JP":35.7

}
lonDict = {
    "KSA": 35,
    "P1": 39.6,
    "T1": 45,
    "T2":93,
    "T3":126.5,
    "P2":133.8,
    "JP":139.8
}



colorMap = []
for node in modelDataset["Input Parameters"]["nodes"]:
    graph.add_node(node, Position=(lonDict[node],latDict[node]))
    colorMap.append("tab:blue")


#adding base locations for ships
dictKeys = modelDataset["Ship Location"].keys()
for ship in modelDataset["Input Parameters"]["ships"]:
    if((ship,0) in modelDataset["Ship Location"].keys()):
        shipLoc = modelDataset["Ship Location"][ship,0]
        #get node location data
        shipLocData = nx.get_node_attributes(graph,'Position')[shipLoc]
        graph.add_node(f"S{ship}", Position=(shipLocData[0],shipLocData[1]+3))
        colorMap.append("tab:red")

#adding edges
networkDataset = modelDataset["Input Parameters"]["length"]
for node1 in modelDataset["Input Parameters"]["nodes"]:
    for node2 in modelDataset["Input Parameters"]["nodes"]:
        if(networkDataset[node1,node2] > 0):
            graph.add_edge(node1,node2,weight=1)
            
#graphing initial structure
nx.draw(graph, pos=nx.get_node_attributes(graph,'Position'),
        node_size=15,ax=ax)


def storageFlow(graph,time):
    for node1 in modelDataset["Input Parameters"]["portAccessibleNodes"]:
        for node2 in modelDataset["Input Parameters"]["portAccessibleNodes"]:
            if(storageFlowDataset[node1,node2,time] > 0):
                graph[node1][node2]["weight"] = storageFlowDataset[node1,node2,time]/5

    return graph

def shipFlow(graph,time):
    for node1 in modelDataset["Input Parameters"]["shipNodes"]:
        for node2 in modelDataset["Input Parameters"]["shipNodes"]:
            shipFlowSum = sum(shipFlowDataset[ship,node1,node2,time] for ship in modelDataset["Input Parameters"]["ships"])
            if(shipFlowSum > 0):
                graph[node1][node2]["weight"] = shipFlowSum/5

    return graph

def shipLocation(graph,dictKeys,time):
    runThru = 1
    for ship in modelDataset["Input Parameters"]["ships"]:
        if((ship,0) in dictKeys):
            shipLoc = modelDataset["Ship Location"][ship,time]
            #get node location data
            shipLocData = nx.get_node_attributes(graph,'Position')[shipLoc]
            graph.nodes[f"S{ship}"]["Position"] = (shipLocData[0],shipLocData[1]+1.5*(runThru))
            runThru += 1
    return graph


def resetGraph(graph):
    #resetting edges
    for node1 in modelDataset["Input Parameters"]["nodes"]:
        for node2 in modelDataset["Input Parameters"]["nodes"]:
            if(networkDataset[node1,node2] > 0):
                graph.add_edge(node1,node2,color="blue")
                
        
    return(graph)

def removeEdges(graph):
    #first removing edges
    edgeList = graph.edges
    for node1 in modelDataset["Input Parameters"]["nodes"]:
        for node2 in modelDataset["Input Parameters"]["nodes"]:
            if((node1,node2) in edgeList):
                graph.remove_edge(node1,node2)
    return(graph)

for i in np.arange(0,3):  
    for time in modelDataset["Input Parameters"]["horizon"]:
        graph = resetGraph(graph)
        graph = storageFlow(graph,time)
        graph = shipFlow(graph,time)
        graph = shipLocation(graph,dictKeys,time)
        #getting weights and locations
        weights = nx.get_edge_attributes(graph,'weight').values()
        positions = nx.get_node_attributes(graph,'Position')
        
        #drawing updated network flow
        nx.draw(graph, positions, 
                width=list(weights),
                node_color=colorMap,
                node_size=10,
                ax=ax)

        pause(2)
        #removes the previous flow/ship locations for the new update graph
        ax.collections[1].remove()
        ax.collections[1].remove()

print("done")