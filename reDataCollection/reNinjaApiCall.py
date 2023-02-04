import requests
import pandas as pd
import json

token = '6fde7281fc0e70e6086a8725eef721ef84aecc63'
api_base = 'https://www.renewables.ninja/api/'

s = requests.session()
# Send token header with each request
s.headers = {'Authorization': 'Token ' + token}



sites = {}

sites["northWestSite"] = [28.3290,34.9920]
sites["northEastSite"] = [26.4630,49.975]
sites["centralWestSite"] = [20.894,39.509]

#wind turbine capacity
windTurbineNameplate = 3000.0

#going through each site and getting wind and solar data
for site in sites.keys():

    for year in ["2017","2018","2019"]:
        
        #call wind reNinja     
        url = api_base + 'data/wind'
    
        args = {
            'lat': sites[site][0],
            'lon': sites[site][1],
            'date_from': f'{year}-01-01',
            'date_to': f'{year}-12-31',
            'dataset': 'merra2',
            'capacity': windTurbineNameplate,
            'height': 100,
            'turbine': 'Vestas V112 3000',
            'format': 'json',
            "raw": True
        }

        r = s.get(url, params=args)

        # Parse JSON to get a pandas.DataFrame of data and dict of metadata
        parsed_response = json.loads(r.text)

        windData = pd.read_json(json.dumps(parsed_response['data']), orient='index')
        
        #converting into capacity factor
        windData["electricity"] = windData["electricity"]/windTurbineNameplate



        #rename col
        windData = windData.rename(columns={"electricity": "cfWind"})

        
        #then calling solar part of API-need to change url
        url = api_base + 'data/pv'    

        args = {
            'lat': sites[site][0],
            'lon': sites[site][1],
            'date_from': f'{year}-01-01',
            'date_to': f'{year}-12-31',
            'dataset': 'merra2',
            'capacity': 3000.0,
            'system_loss': 0.1,
            'tracking': 1,
            'tilt': 19.28,
            'azim': 180,
            'format': 'json',
            "raw": True
        }

        r = s.get(url, params=args)

        # Parse JSON to get a pandas.DataFrame of data and dict of metadata
        parsed_response = json.loads(r.text)

        solarData = pd.read_json(json.dumps(parsed_response['data']), orient='index')

        #converting into capacity factor
        solarData["electricity"] = solarData["electricity"]/3000

        #rename column
        solarData = solarData.rename(columns={"electricity": "cfSolar"})
        
        #merging wind and solar data-combine along columns
        combinedDataset = pd.concat([windData,solarData],axis="columns")
                
        if(year == "2017"):
            siteDf = combinedDataset
        else:
            #combine along rows
            siteDf = pd.concat([siteDf,combinedDataset],axis="index")

    #rename index to time
    siteDf.index.names = ['Time']

    #saving final dataset as reData in both hydrogen and ammonia folders
    siteDf.to_excel(f"../productionAmmoniaOptModel/dataInputs/sites/{site}/reData.xlsx")
    siteDf.to_excel(f"../productionHydrogenOptModel/dataInputs/sites/{site}/reData.xlsx")


print("Done!")