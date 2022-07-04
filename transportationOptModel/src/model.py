from array import array
from fileinput import filename
from pyomo.environ import *
from pyomo.opt import SolverFactory
from pytest import param
import pandas as pd
import numpy as np
import os.path
from pyomo.util.infeasible import log_infeasible_constraints
import pickle


class greenAmmoniaTransportation:
    def writeDataFile(dataFileName,inputDataset):
        with open('../modelInputs/'+str(dataFileName)+'.dat', 'w') as f:
            
            
            #creating for loop for writing set structure
            setNames = ["nodes","portNodes","oceanNodes","regionNodes","horizon","shipTypes","ships","shipNodes","portAccessibleNodes"]
            for setName in setNames:
                f.write(f'set {setName} := ')
                for i in inputDataset[setName]:
                    f.write('%s ' % i)
                f.write(';\n\n')
     
            
            
            #simplifying writing .dat file with for loop
            paramNames = inputDataset.keys()
            
            #no param index names-for writing correct structure of .dat file
            noParamIndexNames = ["capexPortCapacity","capexPortStorage","opexFixedPortCapacity","opexFixedPortStorage","shipSpeed","lifetimeShips","discountRate","gEY"]

            singleParamIndexNames = ["capexShip","opexFixedShip","opexVariableShip","bulkSize"]

            doubleParamIndexNames = {"demand":["regionNodes","horizon"],
                                     "length":["nodes","nodes"],
                                     "portRegionParameter":["portNodes","regionNodes"]}
            
            for paramName in paramNames:
                if paramName in setNames:
                    #skip the set values as only interested in paramNames
                    continue
                if(paramName in noParamIndexNames):
                    #single parameter value structure
                    f.write('param %s := %f; \n' % (paramName,inputDataset[paramName]))                     
                elif(paramName in singleParamIndexNames):
                    #writing correct pyomo structure for single index
                    f.write('param %s := \n' % (paramName))
                    for i in range(len(inputDataset[paramName])):
                        if(i != len(inputDataset[paramName])-1):
                            f.write('%d %f \n' % (i,inputDataset[paramName][i]))
                        else:
                            f.write('%d %f' % (i,inputDataset[paramName][i]))                    
                    f.write(';\n\n')
                else:
                    #all others are double indexed-getting out specific index format for unique indices
                    #i.e. not all params have the same index format
                    indexNames = doubleParamIndexNames[paramName]
                    firstIndexName =indexNames[0]
                    secondIndexName = indexNames[1]
                    
                    lenFirstIndexName = len(inputDataset[firstIndexName])-1
                    lenSecondIndexName = len(inputDataset[secondIndexName])-1
                    
                    #writing correct pyomo structure for single index
                    f.write('param %s := \n' % (paramName))                         
                    for i in inputDataset[firstIndexName]:
                        for j in inputDataset[secondIndexName]:
                            if((i == inputDataset[firstIndexName][lenFirstIndexName]) & (j == inputDataset[secondIndexName][lenSecondIndexName])):                            
                                if((paramName == "portRegionParameter") or (paramName == "length")):
                                    f.write('%s %s %f' % (i,j,inputDataset[paramName][i,j]))    
                                else:    
                                    f.write('%s %d %f' % (i,j,inputDataset[paramName][i][j]))    
                            else:
                                if((paramName == "portRegionParameter") or (paramName == "length")):
                                    f.write('%s %s %f \n' % (i,j,inputDataset[paramName][i,j]))    
                                else:
                                    f.write('%s %d %f \n' % (i,j,inputDataset[paramName][i][j]))

                    f.write(';\n\n')
                    
            print("Completed data file")
            

    def main(dataFileName,inputDataset,testMode=False):
        """Daily operations of a green ammonia shipping fleet

        Args:
            dataFileName (str): .dat file name which will read in/be created data for model run
            inputDataset (dict): see README for further clarification on what parameters are expected to be inputted into spreadsheet
            testMode (bool): automatically set to false, if true-will delete the .dat input file and output file associated with the dataFileName
        """ 
        
        #deleting files if test mode is activated
        if(testMode):
            try:
                os.remove(f"../modelInputs/{dataFileName}.dat")
                #os.remove(f"../modelOutputs/{dataFileName}.xlsx")
            except:
                print("Test mode activated but one of dat or xlsx files files already deleted")
        
            
        
        # creating optimization model with pyomo abstract representation
        model = AbstractModel()

        ################### START SETS  ###################
        
        #set of total nodes that import/export ammonia
        model.nodes = Set(initialize= inputDataset["nodes"])
        model.nodes.construct()       
         
        #set of port nodes in simulation
        model.portNodes = Set(initialize= inputDataset["portNodes"])
        model.portNodes.construct()
        
        #set of ocean nodes
        model.oceanNodes = Set(initialize = inputDataset["oceanNodes"])
        model.oceanNodes.construct()

        #set of region nodes
        model.regionNodes = Set(initialize = inputDataset["regionNodes"])
        model.regionNodes.construct()
           
        #defining nodes which ships can access (ports or ocean nodes)   
        model.shipNodes = Set(initialize = inputDataset["shipNodes"])
        model.shipNodes.construct()

        #defining nodes which ships can access (ports or ocean nodes)   
        model.portAccessibleNodes = Set(initialize = inputDataset["portAccessibleNodes"])
        model.portAccessibleNodes.construct()
        
        #number of ships that can be built in the simulation (done for simplicity)
        model.ships = RangeSet(0,len(inputDataset["ships"])-1)
                        
        #set of ship model types that can be built for ships in simulation
        model.shipTypes = RangeSet(0,len(inputDataset["shipTypes"])-1)
        
        #timesteps in simulation-based on number of days in the demand
        model.horizon = RangeSet(0,len(inputDataset["demand"][inputDataset["regionNodes"][0]])-1)
        ################### END SETS   ###################


        ################### START PARAMETERS  ###################
        #CAPEX for ship type m 
        model.capexShip = Param(model.shipTypes)

        #CAPEX for port capacity on kg basis
        model.capexPortCapacity = Param()

        #CAPEX for port storage on kg basis
        model.capexPortStorage = Param()
        
        #Fixed OPEX for ship model m
        model.opexFixedShip = Param(model.shipTypes)
        
        #Fixed OPEX for port capacity on kg basis
        model.opexFixedPortCapacity = Param()
        
        #Fixed OPEX for port storage on kg basis
        model.opexFixedPortStorage= Param()
        
        #Variable OPEX (fuel costs mainly) for ship model m
        model.opexVariableShip = Param(model.shipTypes)
        
        #cargo ship ammonia capacity size for model type m 
        model.bulkSize = Param(model.shipTypes)          
        
        #demand for region r at timestep t
        model.demand = Param(model.regionNodes,model.horizon)       
        
        #length of route from two nodes (length of zero means the two nodes are not connected)
        model.length = Param(model.nodes,model.nodes)
        
        #binary indicator parameter on whether port p is in region r
        # if it is, value is 1 else, value is zero
        model.portRegionParameter = Param(model.portNodes,model.regionNodes)
        
        #ship speed for simulation-assume all ships travel at the same speed
        model.shipSpeed = Param()
        
        #lifetime of ships and thus the total cost estimated out to
        model.lifetimeShips = Param()
        
        #discount rate for model
        model.discountRate = Param()
        
        #equivalent lifetime of investment in NPV
        # *converts annual investments into what the lifetime would be in present turns
        model.gEY = Param()
        ################### END PARAMETERS    ###################


        ################### START DECISION VARIABLES    ###################
        
        #whether to build the ship in that model type (binary, 1-yes, 0-no)
        model.X = Var(model.ships,model.shipTypes,domain=Binary,initialize=1)

        #flow of fuel (ammonia) from node i to node j for ship s at time t
        model.fuelFlowShip = Var(model.ships,model.shipNodes,model.shipNodes,model.horizon,domain=NonNegativeReals)
        
        #available fuel at ship node s
        model.fuelAvailShip = Var(model.ships,model.oceanNodes,model.horizon,domain=NonNegativeReals)
        
        #indicator variable on where ship s is
        #if at node n at time t, SL = 1, else = 0
        model.shipLocation = Var(model.ships,model.shipNodes,model.horizon,domain=Binary)

        #flow of fuel (ammonia) from node i to node j for port p at time t
        # can be inflow from supply or outflow to demand
        model.fuelFlowStorage = Var(model.portAccessibleNodes,model.portAccessibleNodes,model.horizon,domain=NonNegativeReals)
  
        #fuel available at port p
        model.faPort = Var(model.portNodes,model.horizon,domain=NonNegativeReals) 
        
        #capacity of port storage p
        model.capacityStorage = Var(model.portNodes,domain=NonNegativeReals)
        
        #capacity for importing/exporting ammonia at port
        model.capacityPort =Var(model.portNodes,domain=NonNegativeReals)
        
        ################### END DECISION VARIABLES    ###################



        ###################     START OBJECTIVE     ###################
        #sum up the CAPEX, fixed OPEX, and variable OPEX costs for cargo ships and port storage/capacity 
        def cargoShipCosts(model):
            #sum of capex for each ship you build + the fixed costs + variable costs discounted 
            return sum(sum(model.capexShip[shipType]*model.X[ship,shipType] +
                           model.gEY*(model.opexFixedShip[shipType]*model.X[ship,shipType] +
                                          sum(
                                              sum(
                                                  sum(
                                                      model.opexVariableShip[shipType]*model.length[i,j]*model.fuelFlowShip[ship,i,j,t] for t in model.horizon)
                                                  for j in model.shipNodes if j != i )
                                              for i in model.shipNodes)
                                      ) for shipType in model.shipTypes)
                       for ship in model.ships)
                
        def portCosts(model):
            #sum of capex + fixed OPEX (assuming no variable OPEX) and then looking at storage and capacity costs
            return (sum(model.capacityPort[port]*(model.capexPortCapacity + model.gEY*model.opexFixedPortCapacity)
                + model.capacityStorage[port]*(model.capexPortStorage + model.gEY*model.opexFixedPortStorage)
            for port in model.portNodes))
          
        def minCost_rule(model):
            return (cargoShipCosts(model) + portCosts(model))
        
        model.SystemCost = Objective(rule = minCost_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################


        ###################       START CONSTRAINTS     ###################
        #ship built indicator definition
        def shipBuiltIndicatorRule(model,ship):
            return (sum(model.X[ship,shipType] for shipType in model.shipTypes) <= 1)
        model.shipBuiltIndicatorConstraint = Constraint(model.ships,rule=shipBuiltIndicatorRule)        
        

        #if you build a ship, the ship needs to be somewhere on network
        def shipNetworkPlaceRule(model,ship,time):
            return(sum(model.shipLocation[ship,node,time] for node in model.shipNodes) == sum(model.X[ship,shipType] for shipType in model.shipTypes))
        model.shipNetworkPlaceConstraint = Constraint(model.ships,model.horizon,rule=shipNetworkPlaceRule)        

        #ports can only interact with demand regions if they are connected
        def nodePortConnectionRule(model,nodeI,nodeJ,time):
            return (model.fuelFlowStorage[nodeI,nodeJ,time] <= model.length[nodeI,nodeJ]*sum(model.capacityStorage[port] for port in model.portNodes))
        model.nodePortConnectionConstraint =  Constraint(model.portAccessibleNodes,model.portAccessibleNodes,
                                                        model.horizon,rule=nodePortConnectionRule)        
            
    
        #can only transfer fuel if the nodes are connected and at the home node
        def nodeShipConnectionRule(model,ship,nodeI,nodeJ,time):
            return (model.fuelFlowShip[ship,nodeI,nodeJ,time] <= ( model.shipLocation[ship,nodeI,time])*model.length[nodeI,nodeJ]*sum(model.bulkSize[shipType] for shipType in model.shipTypes if nodeI != nodeJ))            

        model.nodeShipConnectionConstraint = Constraint(model.ships,model.shipNodes,model.shipNodes,model.horizon,rule=nodeShipConnectionRule)


        #ship can only move from location to location
        def shipLocNodeConnectionRule(model,ship,nodeJ,time):
            if((time == 0)):
                return(model.shipLocation[ship,nodeJ,time] >= 0)
            return((model.shipLocation[ship,nodeJ,time]) <= sum(model.shipLocation[ship,nodeI,time-1]*model.length[nodeI,nodeJ] for nodeI in model.shipNodes))
        model.shipLocNodeConnectionConstraint = Constraint(model.ships,model.shipNodes,model.horizon,rule=shipLocNodeConnectionRule)
 
        #fuel available definition
        #previous fuel + any flows in - any flows out
        def fuelAvailShipDefinitionRule(model,ship,node,time):
            if(time == 0):
                return(model.fuelAvailShip[ship,node,time] == 0)
            else:
                return((model.fuelAvailShip[ship,node,time-1] + 
                        sum( 
                                model.fuelFlowShip[ship,node2,node,time-1] - model.fuelFlowShip[ship,node,node2,time-1]                                  
                                for node2 in model.shipNodes))
                       == model.fuelAvailShip[ship,node,time]
                    
                )
        model.fuelAvailShipDefinitionConstraint = Constraint(model.ships,model.oceanNodes,model.horizon,rule=fuelAvailShipDefinitionRule)


        
  
        #port import export capacity
        def portImportExportCapacityRule(model,port,time):
            return(sum(
                    sum(
                            model.fuelFlowShip[ship,node,port,time] + model.fuelFlowShip[ship,port,node,time]
                        for node in model.oceanNodes)
                for ship in model.ships)  <= model.capacityPort[port])  
        model.portImportExportCapacityConstraint = Constraint(model.portNodes,model.horizon,rule=portImportExportCapacityRule) 
  
        #port export capacity rule
        def availFuelCapacityRule(model,port,time):
            return(model.faPort[port,time] <= model.capacityStorage[port])
        model.availFuelCapacityConstraint = Constraint(model.portNodes,model.horizon,rule=availFuelCapacityRule) 
    


        #fuel availability at ports definition
        #any flows in and out storage wise and then any flows in and out shipping wise
        def availFuelDefinitionRule(model,port,time):
            if(time == 0):
                return(model.faPort[port,0] ==  0)
            else:
                return(
                    (model.faPort[port,time-1] + 
                     sum(model.portRegionParameter[port,region]*(model.fuelFlowStorage[region,port,time-1]-model.fuelFlowStorage[port,region,time-1]) 
                         for region in model.regionNodes) +
                     sum(
                         sum(model.fuelFlowShip[ship,ocean,port,time-1] - model.fuelFlowShip[ship,port,ocean,time-1]
                            for ocean in model.oceanNodes) 
                         for ship in model.ships)
                     ) == model.faPort[port,time] 
                )
        model.availFuelDefinitionConstraint = Constraint(model.portNodes,model.horizon,rule=availFuelDefinitionRule) 


        def maxFuelTransferRule(model,port,time):
            if(time == 0):
                return(model.faPort[port,0] ==  0)
            else:
                return(
                    (
                     sum(model.fuelFlowStorage[port,region,time]
                         for region in model.regionNodes) +
                     sum(
                         sum(model.fuelFlowShip[ship,port,ocean,time]
                            for ocean in model.oceanNodes) 
                         for ship in model.ships)
                     ) <= model.faPort[port,time] 
                )
        model.maxFuelTransferConstraint = Constraint(model.portNodes,model.horizon,rule=maxFuelTransferRule) 
            

        #meet demand constraint for network
        # negative demand means the port is supplying fuel
        def meetDemandRule(model,region,time):
            return(sum(model.portRegionParameter[port,region]*(model.fuelFlowStorage[port,region,time] - model.fuelFlowStorage[region,port,time]) for port in model.portNodes) == model.demand[region,time])
        model.meetDemandConstraint = Constraint(model.regionNodes,model.horizon,rule=meetDemandRule)        
    
        
        
        ###################       END CONSTRAINTS     ###################



        ###################          WRITING DATA       ###################
        if(os.path.isfile(f"../dataInputs/{dataFileName}.dat")):
            print(f"Data file {dataFileName} already exists!\nSkipping creating .dat file")
        else:
            #print(f"Data file {dataFileName} does not exist.\nCreating .dat file")
            greenAmmoniaTransportation.writeDataFile(dataFileName,inputDataset)
        
        # load in data for the system
        data = DataPortal()
        data.load(filename=f"../modelInputs/{dataFileName}.dat", model=model)
        instance = model.create_instance(data)



        #instance.nodePortConnectionConstraint.pprint()    
        
        solver = SolverFactory('glpk')
        solver.solve(instance)
        
        
            

        
                
        #what model ship built
        shipBuiltDataset = np.zeros((len(inputDataset["ships"]),len(inputDataset["shipTypes"])))
        for ship in np.arange(len(inputDataset["ships"])):
            for shipType in np.arange(len(inputDataset["shipTypes"])):
                shipBuiltDataset[ship][shipType] = instance.X[ship,shipType].value


        fuelFlowDataset = np.zeros((len(inputDataset["ships"]),len(inputDataset["horizon"])))
        for ship in np.arange(len(inputDataset["ships"])):
            for time in np.arange(len(inputDataset["horizon"])):
                totalCount = 0
                for nodeI in instance.shipNodes:
                    for nodeJ in instance.shipNodes:
                        if(instance.fuelFlowShip[ship,nodeI,nodeJ,time].value == None):
                            continue
                        totalCount += instance.fuelFlowShip[ship,nodeI,nodeJ,time].value
                fuelFlowDataset[ship][time] = totalCount
        #print("fuel flow ship")
        #print(fuelFlowDataset)

        
        
        
        
        #saving data
        masterDataFrame = {}
        
        
        
        masterDataFrame["Input Parameters"] = inputDataset
        
        masterDataFrame["Ship Built Dataset"] = shipBuiltDataset
     
        #print(shipBuiltDataset)
        
        #ship fuel availability
        '''        fuelAvailShipDataset = np.zeros((len(inputDataset["ships"]),len(inputDataset["oceanNodes"]),len(inputDataset["horizon"])))
        for ship in np.arange(len(inputDataset["ships"])):
            for time in np.arange(len(inputDataset["horizon"])):
                for nodeName in  instance.oceanNodes:
                    fuelAvailShipDataset[ship][node][time] = instance.fuelAvailShip[ship,node,time].value

        masterDataFrame["Fuel Avail Ship"] = fuelAvailShipDataset'''
  
        
        '''        #looking at fuel flows per ship
        fuelFlowDataset = np.zeros((len(inputDataset["ships"]),len(inputDataset["shipNodes"]),len(inputDataset["shipNodes"]),len(inputDataset["horizon"])))
        for ship in np.arange(len(inputDataset["ships"])):
            for time in np.arange(len(inputDataset["horizon"])):
                node1 = 0
                for nodeI in instance.shipNodes:
                    node2 = 0
                    for nodeJ in instance.shipNodes:
                        if(instance.fuelFlowShip[ship,nodeI,nodeJ,time].value == None):
                            continue
                        
                        fuelFlowDataset[ship][node1][node2][time] = instance.fuelFlowShip[ship,nodeI,nodeJ,time].value
                        node2 += 1
                    node1 += 1
        masterDataFrame["Fuel Flow Ship"] = fuelFlowDataset'''
        
         #looking at fuel flows for each ship
        fuelFlowShipDataset = {}#np.zeros((len(inputDataset["ships"]),len(inputDataset["shipNodes"]),len(inputDataset["shipNodes"]),len(inputDataset["horizon"])))
        for ship in inputDataset["ships"]:
            for time in np.arange(len(inputDataset["horizon"])):
                for nodeI in instance.shipNodes:
                    for nodeJ in instance.shipNodes:
                        fuelFlowShipDataset[ship,nodeI,nodeJ,time] = instance.fuelFlowShip[ship,nodeI,nodeJ,time].value
        masterDataFrame["Fuel Flow Ship"] = fuelFlowShipDataset
 
        fuelFlowStorageDataset = {}#np.zeros((len(inputDataset["ships"]),len(inputDataset["shipNodes"]),len(inputDataset["shipNodes"]),len(inputDataset["horizon"])))
        for time in np.arange(len(inputDataset["horizon"])):
            for nodeI in instance.portAccessibleNodes:
                for nodeJ in instance.portAccessibleNodes:
                        fuelFlowStorageDataset[nodeI,nodeJ,time] = instance.fuelFlowStorage[nodeI,nodeJ,time].value
        masterDataFrame["Fuel Flow Storage"] = fuelFlowStorageDataset
    
        
        #looking at when each ship is traveling or in port
        #print(instance.indicatorInPort[1,0,0].value)
        shipLocationDataset = {}#np.zeros((len(inputDataset["ships"]),len(inputDataset["horizon"])))
        for ship in np.arange(len(inputDataset["ships"])):
            if(sum(instance.X[ship,shipType].value for shipType in instance.shipTypes) == 0):
                continue
            for time in np.arange(len(inputDataset["horizon"])):
                for node in inputDataset["shipNodes"]:
                    if(instance.shipLocation[ship,node,time].value == 1):
                        shipLocationDataset[ship,time] = node
                    
        masterDataFrame["Ship Location"] = shipLocationDataset


        #looking at fuel available in storage
        portAvailDataset = {}#np.zeros((len(inputDataset["portNodes"]),len(inputDataset["horizon"])))
        for port in inputDataset["portNodes"]:
            for time in np.arange(len(inputDataset["horizon"])):
                portAvailDataset[port,time] = instance.faPort[port,time].value
        masterDataFrame["Port Fuel Avail"] = portAvailDataset

        
        print('port storage')
        portStorageDataset = {}
        portTransferCapacityDataset = {}
        for port in inputDataset["portNodes"]:
            portStorageDataset[port] = instance.capacityStorage[port].value
            portTransferCapacityDataset[port] = instance.capacityPort[port].value       
            
        masterDataFrame["Port Storage Capacity"] = portStorageDataset
        masterDataFrame["Port Transfer Capacity"] = portTransferCapacityDataset
        
        
        
        #structure of numpy dataframe
        #0: ship build type dataset
        #1: fuel availability on ship dataset
        #2: fuel flow dataset between nodes
        #3: ship location dataset
        #4: fuel availability on port
        #5: port capacity for storage
        #6: port transfer capacity (import + export total handling)
        
        #saving data into pickle dataframe
        output = open(f'../modelOutputs/{dataFileName}.pkl', 'wb')
        pickle.dump(masterDataFrame, output)
        output.close()   
        print(f"Output written to {dataFileName} in model outputs folder")


        #print("done")
        

        