import pandas as pd
import numpy as np
from model import greenAmmoniaProduction
from datetime import datetime
import os


#dont include the .dat ending or path location
datFileName = "testRun"
testMode = True
startDay = 0
endDay = 75
'''datFileName = "testRun"
testMode = True
startDay = 0
endDay = 25'''
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