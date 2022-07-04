import numpy as np
import pandas as pd

df = pd.read_excel("reData.xlsx",sheet_name='windTurbinePowerAnalysis')


windSpeedArray = df["windSpeed"][0].split("|")

windPowerArray = df["powerOutput"][0].split("|")

cleanedArray = {"windSpeed": windSpeedArray,"windPower":windPowerArray}

newDf = pd.DataFrame(data=cleanedArray)

newDf.to_excel("cleanedWindPowerCurve.xlsx")
