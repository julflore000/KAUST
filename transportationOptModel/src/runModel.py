import pandas as pd
import numpy as np
from model import greenAmmoniaTransportation
from datetime import datetime
import os


#dont include the .dat ending or path location
datFileName = "testRun"
testMode = True


regionDemandRaw = pd.read_excel("../dataInputs/inputSheet.xlsx",sheet_name='regionDemand')
regionDemandList = []
for col in regionDemandRaw.columns:
    if(col == "Time"):
        continue
    regionDemand = regionDemandRaw[col].tolist()
    regionDemandList.append(regionDemand)

inputDataset = {}


#just for initial testing input data

#sets
inputDataset["horizon"] = np.arange(0,len(regionDemandList[0]))

inputDataset["regions"] = [0,1,2]

inputDataset["ports"] = [0,1,2,3]

inputDataset["shipTypes"] = [0,1,2]

inputDataset["ships"] = [0,1,2,3,4,5,7,8,9,10,11,12,13,14,15]


#params
inputDataset["capexShip"] = [1.5,3,6]

inputDataset["capexPortCapacity"] = 2

inputDataset["capexPortStorage"] = 2

inputDataset["opexFixedShip"] = [1,1.1,1.2]

inputDataset["opexFixedPortCapacity"] = inputDataset["capexPortCapacity"]*.02

inputDataset["opexFixedPortStorage"] = inputDataset["capexPortStorage"]*.02

inputDataset["opexVariableShip"] = [0.1,0.2,0.2]

inputDataset["bulkSize"] = [2,5,15]

inputDataset["demand"] = regionDemandList


inputDataset["length"] = [[0,1,2,3],
                          [1,0,1,2],
                          [2,1,0,1],
                          [3,2,1,0]]

inputDataset["shipSpeed"] =2

inputDataset["lifetimeShips"] = 20

inputDataset["discountRate"] = .08

#rows are the ports and cols are the regions (1 in region, 0 not in region)
inputDataset["portRegionParameter"] = [[1,0,0],
                                       [0,1,0],
                                       [0,0,1],
                                       [0,0,1]]

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