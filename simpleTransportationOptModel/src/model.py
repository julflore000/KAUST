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
            setNames = ["ports","regions","ships","shipTypes","horizon"]
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

            doubleParamIndexNames = {"demand":["regions","horizon"],
                                     "length":["ports","ports"],
                                     "portRegionParameter":["ports","regions"]}
            
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
        
        #set of total ports that can import/export ammonia
        model.ports = Set(initialize= inputDataset["ports"])
        model.ports.construct()       
         
      
        #set of regions that ports belong to
        model.regions = Set(initialize = inputDataset["regions"])
        model.regions.construct()
           
        
        #number of ships that can be built in the simulation (done for simplicity)
        model.ships = RangeSet(0,len(inputDataset["ships"])-1)
                        
        #set of ship model types that can be built for ships in simulation
        model.shipTypes = RangeSet(0,len(inputDataset["shipTypes"])-1)
        
        #timesteps in simulation-based on number of months in the demand
        model.horizon = RangeSet(0,len(inputDataset["demand"][inputDataset["regions"][0]])-1)
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
        model.demand = Param(model.regions,model.horizon)       
        
        #length of route from two ports (length of zero means the two ports are not connected)
        model.length = Param(model.ports,model.ports)
        
        #binary indicator parameter on whether port p is in region r
        # if it is, value is 1 else, value is zero
        model.portRegionParameter = Param(model.ports,model.regions)
        
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
        model.B = Var(model.ships,model.shipTypes,domain=Binary,initialize=0)

        #flow of fuel (ammonia or hydrogen) from port i to port j for ship s at time t
        model.X = Var(model.ships,model.ports,model.ports,model.horizon,domain=NonNegativeReals)
        
        #whether to activate port link connection i to j
        model.Y = Var(model.ships,model.ports,model.ports,model.horizon,domain=Binary)
        
        
        
        #fuel available at port p
        model.faPort = Var(model.ports,model.horizon,domain=NonNegativeReals)
        

        #flow of fuel (ammonia) from port i to region r at time t
        # can be inflow from supply or outflow to demand
        model.fuelFlowStorage = Var(model.ports,model.regions,model.horizon,domain=Reals)
  

        #capacity of port storage p
        model.capacityStorage = Var(model.ports,domain=NonNegativeReals)
        
        #capacity for importing/exporting ammonia at port
        model.capacityPort =Var(model.ports,domain=NonNegativeReals)
        
        ################### END DECISION VARIABLES    ###################



        ###################     START OBJECTIVE     ###################
        #sum up the CAPEX, fixed OPEX, and variable OPEX costs for cargo ships and port storage/capacity 
        def cargoShipCosts(model):
            #sum of capex for each ship you build + the fixed costs + variable costs discounted 
            return sum(sum(model.capexShip[shipType]*model.B[ship,shipType] +
                           model.gEY*(model.opexFixedShip[shipType]*model.B[ship,shipType] +
                                          sum(
                                              sum(
                                                  sum(
                                                      model.opexVariableShip[shipType]*(2*model.length[i,j]/model.shipSpeed)*model.X[ship,i,j,t] for t in model.horizon)
                                                  for j in model.ports if j != i )
                                              for i in model.ports)
                                      ) for shipType in model.shipTypes)
                       for ship in model.ships)
                
        def portCosts(model):
            #sum of capex + fixed OPEX (assuming no variable OPEX) and then looking at storage and capacity costs
            return (sum(model.capacityPort[port]*(model.capexPortCapacity + model.gEY*model.opexFixedPortCapacity)
                + model.capacityStorage[port]*(model.capexPortStorage + model.gEY*model.opexFixedPortStorage)
            for port in model.ports))
          
        def minCost_rule(model):
            return (cargoShipCosts(model) + portCosts(model))
        
        model.SystemCost = Objective(rule = minCost_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################


        ###################       START CONSTRAINTS     ###################
        #can only build 1 ship from the available models
        def shipBuiltMax1Rule(model,ship):
            return (sum(model.B[ship,shipType] for shipType in model.shipTypes) <= 1)
        model.shipBuiltMax1Constraint = Constraint(model.ships,rule=shipBuiltMax1Rule)        
        

        #can only send a ship from port i to port j if the ship model is built and max capacity of tanker specs
        def shipFlowRule(model,ship,time):
            return (sum(
                sum(
                    model.X[ship,i,j,time] for i in model.ports)
             for j in model.ports) <= sum(model.B[ship,shipType]*model.bulkSize[shipType] for shipType in model.shipTypes))
        model.shipFlowConstraint = Constraint(model.ships,model.horizon,rule=shipFlowRule)        
                

        #max fuel that can either be deployed to another port or used to meet demand at port p
        def maxFuelFlowRule(model,i,time):
            return (sum(
                sum(
                    model.X[ship,i,j,time] for j in model.ports)
             for ship in model.ships) + sum(model.portRegionParameter[i,r]*model.fuelFlowStorage[i,r,time] for r in model.regions) <= model.faPort[i,time])
        model.maxFuelFlowConstraint = Constraint(model.ports,model.horizon,rule=maxFuelFlowRule)        
           

        #activate port link rule-can only send a ship on one port route per month
        def activatePortLinkRule(model,ship,time):
            return( sum(sum(model.Y[ship,i,j,time] for j in model.ports) for i in model.ports) <= 1)
        model.activatePortLinkConstraint = Constraint(model.ships,model.horizon,rule=activatePortLinkRule)        

        #activate port link rule implementation-can only send a ship on one port route per month
        def activatePortFlowRule(model,ship,i,j,time):
            return(model.X[ship,i,j,time] <= model.length[i,j]*model.Y[ship,i,j,time]*sum(model.bulkSize[shipType] for shipType in model.shipTypes))
        model.activatePortFlowConstraint = Constraint(model.ships,model.ports,model.ports,model.horizon,rule=activatePortFlowRule)        
        
        #port import export capacity
        def portImportExportCapacityRule(model,i,time):
            return(sum(
                    sum(
                            model.X[ship,i,j,time] + model.X[ship,j,i,time]
                        for j in model.ports)
                for ship in model.ships)  <= model.capacityPort[i])  
        model.portImportExportCapacityConstraint = Constraint(model.ports,model.horizon,rule=portImportExportCapacityRule) 
  
        #port export capacity rule
        def availFuelCapacityRule(model,port,time):
            return(model.faPort[port,time] <= model.capacityStorage[port])
        model.availFuelCapacityConstraint = Constraint(model.ports,model.horizon,rule=availFuelCapacityRule) 
    


        #fuel availability at ports definition
        #any flows in and out storage wise and then any flows in and out shipping wise
        def availFuelDefinitionRule(model,port,time):
            if(time == 0):
                return(model.faPort[port,0] ==  0)
            else:
                return(
                    (model.faPort[port,time-1] - 
                     sum(model.portRegionParameter[port,region]*(model.fuelFlowStorage[port,region,time-1]) 
                         for region in model.regions) +
                     sum(
                         sum(model.X[ship,i,port,time-1] - model.X[ship,port,i,time-1]
                            for i in model.ports) 
                         for ship in model.ships)
                     ) == model.faPort[port,time] 
                )
        model.availFuelDefinitionConstraint = Constraint(model.ports,model.horizon,rule=availFuelDefinitionRule) 
 

        #meet demand constraint for network
        # negative demand means the port is supplying fuel
        def meetDemandRule(model,region,time):
            return(sum(model.portRegionParameter[port,region]*(model.fuelFlowStorage[port,region,time]) for port in model.ports) == model.demand[region,time])
        model.meetDemandConstraint = Constraint(model.regions,model.horizon,rule=meetDemandRule)        
    
        
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
                shipBuiltDataset[ship][shipType] = instance.B[ship,shipType].value


        fuelFlowDataset = np.zeros((len(inputDataset["ships"]),len(inputDataset["horizon"])))
        for ship in np.arange(len(inputDataset["ships"])):
            for time in np.arange(len(inputDataset["horizon"])):
                totalCount = 0
                for nodeI in instance.ports:
                    for nodeJ in instance.ports:
                        if(instance.X[ship,nodeI,nodeJ,time].value == None):
                            continue
                        totalCount += instance.X[ship,nodeI,nodeJ,time].value
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
                for nodeI in instance.ports:
                    for nodeJ in instance.ports:
                        fuelFlowShipDataset[ship,nodeI,nodeJ,time] = instance.X[ship,nodeI,nodeJ,time].value
        masterDataFrame["Fuel Flow Ship"] = fuelFlowShipDataset
 
        fuelFlowStorageDataset = {}#np.zeros((len(inputDataset["ships"]),len(inputDataset["shipNodes"]),len(inputDataset["shipNodes"]),len(inputDataset["horizon"])))
        for time in np.arange(len(inputDataset["horizon"])):
            for nodeI in instance.ports:
                for nodeJ in instance.regions:
                    fuelFlowStorageDataset[nodeI,nodeJ,time] = instance.fuelFlowStorage[nodeI,nodeJ,time].value
        masterDataFrame["Fuel Flow Storage"] = fuelFlowStorageDataset
    


        #looking at fuel available in storage
        portAvailDataset = {}#np.zeros((len(inputDataset["portNodes"]),len(inputDataset["horizon"])))
        for port in inputDataset["ports"]:
            for time in np.arange(len(inputDataset["horizon"])):
                portAvailDataset[port,time] = instance.faPort[port,time].value
        masterDataFrame["Port Fuel Avail"] = portAvailDataset

        
        print('port storage')
        portStorageDataset = {}
        portTransferCapacityDataset = {}
        for port in inputDataset["ports"]:
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
        

        