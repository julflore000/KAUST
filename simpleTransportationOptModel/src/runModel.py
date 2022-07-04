import pandas as pd
import numpy as np
from model import greenAmmoniaTransportation
from datetime import datetime
import os


#dont include the .dat ending or path location
datFileName = "testRun"
testMode = True


inputDataset = {}
#just for initial testing input data

#sets
inputDataset["ports"] = ["JEDDAH","TOKYO"]

inputDataset["regions"] = ["KSA","JP"]

inputDataset["shipTypes"] = [0,1]

inputDataset["ships"] = [0,1,2,3,4]


regionDemandRaw = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='regionDemand')
#dropping time col
regionDemandRaw.drop('Time', inplace=True, axis=1)

regionDemandDict = {}
for col,regionNode in zip(regionDemandRaw.columns,inputDataset["regions"]):
    regionDemand = regionDemandRaw[col].tolist()
    regionDemandDict[regionNode] = regionDemand

#finsihing up horizon set
inputDataset["horizon"] = np.arange(0,len(regionDemandDict[inputDataset["regions"][0]]))

#params
inputDataset["capexShip"] = [1.5,4]

inputDataset["capexPortCapacity"] = .001

inputDataset["capexPortStorage"] = .0005

inputDataset["opexFixedShip"] = [1,1.1]

inputDataset["opexFixedPortCapacity"] = inputDataset["capexPortCapacity"]*.02

inputDataset["opexFixedPortStorage"] = inputDataset["capexPortStorage"]*.02

inputDataset["opexVariableShip"] = [2,2]

inputDataset["bulkSize"] = [25,100]

inputDataset["demand"] = regionDemandDict

#creating dict dataset for network connection
inputDataset["length"] = {}
connectionPairs = [["KSA","JEDDAH"],
                   ["JEDDAH","TOKYO"],
                   ["TOKYO","JP"]]
totalNodes = inputDataset["regions"] + inputDataset["ports"]

for node1 in totalNodes:
    for node2 in totalNodes:
        if(([node1,node2] in connectionPairs) or ([node2,node1] in connectionPairs)):
            inputDataset["length"][node1,node2] = 1
            inputDataset["length"][node2,node1] = 1
        else:
            inputDataset["length"][node1,node2] = 0
            inputDataset["length"][node2,node1] = 0            

#no self connecting nodes
for node in totalNodes:
    inputDataset["length"][node,node] = 0


inputDataset["shipSpeed"] = 1

inputDataset["lifetimeShips"] = 20

inputDataset["discountRate"] = .08

#key is the port,region value is 1 if in region, 0 not if not in region
inputDataset["portRegionParameter"] = {}
for port in inputDataset["ports"]:
    for region in inputDataset["regions"]:
        if(([port,region] in connectionPairs) or ([region,port] in connectionPairs)):
            inputDataset["portRegionParameter"][port,region] = 1
        else:
            inputDataset["portRegionParameter"][port,region] = 0




inputDataset["gEY"] = ((1+inputDataset["discountRate"])**inputDataset["lifetimeShips"] -1)/(inputDataset["discountRate"]*(1+inputDataset["discountRate"])**inputDataset["lifetimeShips"])

# for tracking elapsed time
startRun = datetime.now()
start_time = startRun.strftime("%H:%M:%S")
print("Run started:", start_time)

greenAmmoniaTransportation.main(datFileName,inputDataset,testMode)


#getting end time
endRun = datetime.now()
end_time = endRun.strftime("%H:%M:%S")
print("Run over:", end_time)

#printing total model runtime
print("Total model time took: ",str(endRun-startRun))




'''
inputDataset = {}
#just for initial testing input data

#sets
inputDataset["ports"] = ["JEDDAH","TOKYO","BUSAN","HAMBURG"]

inputDataset["regions"] = ["KSA","JP","SK","DE"]

inputDataset["shipTypes"] = [0,1]

inputDataset["ships"] = [0,1,2,3,4]


regionDemandRaw = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='regionDemand')
#dropping time col
regionDemandRaw.drop('Time', inplace=True, axis=1)

regionDemandDict = {}
for col,regionNode in zip(regionDemandRaw.columns,inputDataset["regions"]):
    regionDemand = regionDemandRaw[col].tolist()
    regionDemandDict[regionNode] = regionDemand

#finsihing up horizon set
inputDataset["horizon"] = np.arange(0,len(regionDemandDict[inputDataset["regions"][0]]))

#params
inputDataset["capexShip"] = [1.5,4]

inputDataset["capexPortCapacity"] = .001

inputDataset["capexPortStorage"] = .0005

inputDataset["opexFixedShip"] = [1,1.1]

inputDataset["opexFixedPortCapacity"] = inputDataset["capexPortCapacity"]*.02

inputDataset["opexFixedPortStorage"] = inputDataset["capexPortStorage"]*.02

inputDataset["opexVariableShip"] = [2,2]

inputDataset["bulkSize"] = [25,100]

inputDataset["demand"] = regionDemandDict

#creating dict dataset for network connection
inputDataset["length"] = {}
connectionPairs = [["KSA","JEDDAH"],
                   ["JEDDAH","TOKYO"],["JEDDAH","BUSAN"],["JEDDAH","HAMBURG"],
                   ["TOKYO","JP"],["BUSAN","SK"],["HAMBURG","DE"]]
totalNodes = inputDataset["regions"] + inputDataset["ports"]

for node1 in totalNodes:
    for node2 in totalNodes:
        if(([node1,node2] in connectionPairs) or ([node2,node1] in connectionPairs)):
            inputDataset["length"][node1,node2] = 1
            inputDataset["length"][node2,node1] = 1
        else:
            inputDataset["length"][node1,node2] = 0
            inputDataset["length"][node2,node1] = 0            

#no self connecting nodes
for node in totalNodes:
    inputDataset["length"][node,node] = 0


inputDataset["shipSpeed"] = 1

inputDataset["lifetimeShips"] = 20

inputDataset["discountRate"] = .08

#key is the port,region value is 1 if in region, 0 not if not in region
inputDataset["portRegionParameter"] = {}
for port in inputDataset["ports"]:
    for region in inputDataset["regions"]:
        if(([port,region] in connectionPairs) or ([region,port] in connectionPairs)):
            inputDataset["portRegionParameter"][port,region] = 1
        else:
            inputDataset["portRegionParameter"][port,region] = 0




inputDataset["gEY"] = ((1+inputDataset["discountRate"])**inputDataset["lifetimeShips"] -1)/(inputDataset["discountRate"]*(1+inputDataset["discountRate"])**inputDataset["lifetimeShips"])

# for tracking elapsed time
startRun = datetime.now()
start_time = startRun.strftime("%H:%M:%S")
print("Run started:", start_time)

greenAmmoniaTransportation.main(datFileName,inputDataset,testMode)


#getting end time
endRun = datetime.now()
end_time = endRun.strftime("%H:%M:%S")
print("Run over:", end_time)

#printing total model runtime
print("Total model time took: ",str(endRun-startRun))
'''