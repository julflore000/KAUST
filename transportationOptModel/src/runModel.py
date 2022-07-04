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
inputDataset["nodes"] = ["KSA","P1","T1","T2","P2","JP"]

inputDataset["portNodes"] = ["P1","P2"]

inputDataset["oceanNodes"] = ["T1","T2"]

inputDataset["regionNodes"] = ["KSA","JP"]

inputDataset["shipNodes"] = np.concatenate((inputDataset["portNodes"],inputDataset["oceanNodes"]))

inputDataset["portAccessibleNodes"] = np.concatenate((inputDataset["portNodes"],inputDataset["regionNodes"]))

inputDataset["shipTypes"] = [0,1]

inputDataset["ships"] = [0,1,2,3]


regionDemandRaw = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='regionDemand')
#dropping time col
regionDemandRaw.drop('Time', inplace=True, axis=1)

regionDemandDict = {}
for col,regionNode in zip(regionDemandRaw.columns,inputDataset["regionNodes"]):
    regionDemand = regionDemandRaw[col].tolist()
    regionDemandDict[regionNode] = regionDemand

#finsihing up horizon set
inputDataset["horizon"] = np.arange(0,len(regionDemandDict[inputDataset["regionNodes"][0]]))

#params
inputDataset["capexShip"] = [1.5,4]

inputDataset["capexPortCapacity"] = .01

inputDataset["capexPortStorage"] = 0.01

inputDataset["opexFixedShip"] = [1,1.1]

inputDataset["opexFixedPortCapacity"] = inputDataset["capexPortCapacity"]*.02

inputDataset["opexFixedPortStorage"] = inputDataset["capexPortStorage"]*.02

inputDataset["opexVariableShip"] = [2,2]

inputDataset["bulkSize"] = [2,10]

inputDataset["demand"] = regionDemandDict

#creating dict dataset for network connection
inputDataset["length"] = {}
nodeNumList = np.arange(len(inputDataset["nodes"]))

tempLengthList = np.eye(len(inputDataset["nodes"]), k=1)  +  np.eye(len(inputDataset["nodes"]), k=-1)
tempLengthList[1][0] = 0
tempLengthList[len(inputDataset["nodes"])-1][len(inputDataset["nodes"])-2] = 0

for num1,name1 in zip(nodeNumList,inputDataset["nodes"]):
    for num2,name2 in zip(nodeNumList,inputDataset["nodes"]):
        inputDataset["length"][name1,name2] = tempLengthList[num1][num2]


#make sure final region node is connected to final port node


inputDataset["shipSpeed"] = 1

inputDataset["lifetimeShips"] = 20

inputDataset["discountRate"] = .08

#key is the port,region value is 1 if in region, 0 not if not in region
inputDataset["portRegionParameter"] = {("P1","KSA"):1,
                                       ("P1","JP"):0,
                                       ("P2","KSA"):0,
                                       ("P2","JP"):1}



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


'''datFileName = "testRun"
testMode = True
startDay = 0
endDay = 25
transmissionLosses = .02

pdSingleParamDataset = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='systemSettings')

paramNames = pdSingleParamDataset["ParamName"]
paramValues = pdSingleParamDataset["Value"]

#creating input dataset for single value Params
inputDataset = {}

#adding wind and solar generation capacity factors
windCFDataset = pd.read_excel("../dataInputs/reData.xlsx",sheet_name='cfWind')
solarCFDataset = pd.read_excel("../dataInputs/reData.xlsx",sheet_name='cfSolar')



inputDataset["cfWind"] = np.array(windCFDataset["cfWind"])[(24*startDay):(24*endDay)]*(1-transmissionLosses)

inputDataset["cfSolar"] = np.array(solarCFDataset["cfSolar"])[(24*startDay):(24*endDay)]*(1-transmissionLosses)

#adding single param value data
for paramName,paramValue in zip(paramNames,paramValues):
    inputDataset[paramName] = paramValue


pdEYDataset = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='eyUnitSettings')
#adding EY unit data
for paramName in pdEYDataset.columns:
    if(paramName == "Name"):
        #skip assigning the Name column as the model uses integer indices
        continue
    #create empty array inside dict
    inputDataset[paramName] = np.zeros(len(pdEYDataset["capexEY"]))
    for index in np.arange(0,len(pdEYDataset["capexEY"])):
        inputDataset[paramName][index] = pdEYDataset[paramName][index]

#getting correct ammonia demand
inputDataset["ammoniaDemand"] = inputDataset["ammoniaDemand"]*endDay


# for tracking elapsed time
startRun = datetime.now()
start_time = startRun.strftime("%H:%M:%S")
print("Run started:", start_time)

greenAmmoniaProduction.main(datFileName,inputDataset,testMode)


#getting end time
endRun = datetime.now()
end_time = endRun.strftime("%H:%M:%S")
print("Run over:", end_time)

#printing total model runtime
print("Total model time took: ",str(endRun-startRun))
'''