from array import array
from fileinput import filename
from pyomo.environ import *
from pyomo.opt import SolverFactory
import pyomo as pyo
from pytest import param
import pandas as pd
import numpy as np
import os.path



class greenAmmoniaTransportation:
    def writeDataFile(dataFileName,inputDataset):
        with open('../modelInputs/'+str(dataFileName)+'.dat', 'w') as f:
            
            
            #creating for loop for writing set structure
            setNames = ["horizon","regions","shipTypes","ships","ports"]
            
            for setName in setNames:
                f.write(f'set {setName} := ')
                for i in range(len(inputDataset[setName])):
                    f.write('%d ' % i)
                f.write(';\n\n')
     
            
            
            #simplifying writing .dat file with for loop
            paramNames = inputDataset.keys()
            
            #no param index names-for writing correct structure of .dat file
            noParamIndexNames = ["capexPortCapacity","capexPortStorage","opexFixedPortCapacity","opexFixedPortStorage","shipSpeed","lifetimeShips","discountRate","gEY"]

            singleParamIndexNames = ["capexShip","opexFixedShip","opexVariableShip","bulkSize",""]

            
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
                    #all others are double indexed
                    #writing correct pyomo structure for single index
                    f.write('param %s := \n' % (paramName))
                    for i in range(len(inputDataset[paramName])):
                        for j in range(len(inputDataset[paramName][0])):
                            if((i == len(inputDataset[paramName])-1) & (j == len(inputDataset[paramName][0])-1)):                            
                                f.write('%d %d %f' % (i,j,inputDataset[paramName][i][j]))    
                            else:
                                f.write('%d %d %f \n' % (i,j,inputDataset[paramName][i][j]))

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
                os.remove(f"../modelOutputs/{dataFileName}.xlsx")
            except:
                print("Test mode activated but one of files already deleted")
        
            
        
        # creating optimization model with pyomo abstract representation
        model = AbstractModel()

        ################### START SETS  ###################
        #timesteps in simulation-based on number of days in the demand
        model.horizon = RangeSet(0,len(inputDataset["demand"][0])-1)
        
        #set of regions that import/export ammonia
        model.regions = RangeSet(0,len(inputDataset["regions"])-1)
        
        #set of ports in simulation
        model.ports = RangeSet(0,len(inputDataset["ports"])-1)
        
        #set of ship model types that can be built for ships in simulation
        model.shipTypes = RangeSet(0,len(inputDataset["shipTypes"])-1)
        
        #number of ships that can be built in the simulation (done for simplicity)
        model.ships = RangeSet(0,len(inputDataset["ships"])-1)
        
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
        
        #demand for region r at timestep t (positive means demand, negative means supply)
        model.demand = Param(model.regions,model.horizon)
        
        #length of route from port i to port j
        model.length = Param(model.ports,model.ports)
        
        #indicator parameter on whether port p is in region r
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
        model.X = Var(model.ships,model.shipTypes,within=Binary)

        #whether to send ship s from port i to port j at timestep t
        # * (1-ship leaves that port at time t to the destination, 0-not put on route)
        model.B = Var(model.ships,model.ports,model.ports,model.horizon,within=Binary)

        #indicator variable on whether ship s is at port p at timestep t
        # (1- ship is at port p at time t, 0 -not at port)
        model.indicatorInPort = Var(model.ships,model.ports,model.horizon,within=Binary)

        #indicator variable on whether ship s is travelling (on a route) at timestep t
        #1-traveling, 0-not en route
        model.indicatorIsTraveling = Var(model.ships,model.horizon,within=Binary)
        
        #amount of ammonia available to deploy on cargo ship s at timestep t
        model.csAvail = Var(model.ships,model.horizon,domain=NonNegativeReals)
        
        #amount of ammonia to deploy (unload) from cargo ship s at timestep t
        model.csDeploy = Var(model.ships,model.horizon,domain=NonNegativeReals)
        
        #amount of ammonia able to be deployed at port storage p at timestep t
        model.psAvail = Var(model.ports,model.horizon,domain=NonNegativeReals)
        
        #amount of ammonia to deploy from port storage p at timestep t to help meet demand
        model.psDeploy = Var(model.ports,model.horizon,domain=NonNegativeReals)
        
        #amount of cargo (ammonia) to transfer from ship s at port p at time t
        # positive means ship unloading, negative means cargo being put onto ship
        model.cargoTransfer = Var(model.ships,model.ports,model.horizon,domain=Reals)
        
        #ammonia unloading capacity at port p
        model.psPortCapacity = Var(model.ports,domain=NonNegativeReals)
        
        #ammonia storage capacity at port p
        model.psStorageCapacity = Var(model.ports,domain=NonNegativeReals)
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
                                                      model.opexVariableShip[shipType]*model.length[i,j]*model.B[ship,i,j,t] for t in model.horizon)
                                                  for j in model.ports if j != i )
                                              for i in model.ports)
                                      ) for shipType in model.shipTypes)
                       for ship in model.ships)
                
        def portCosts(model):
            #sum of capex + fixed OPEX (assuming no variable OPEX) and then looking at storage and capacity costs
            return (sum(model.psPortCapacity[port]*(model.capexPortCapacity + model.gEY*model.opexFixedPortCapacity)
                + model.psStorageCapacity[port]*(model.capexPortStorage + model.gEY*model.opexFixedPortStorage)
            for port in model.ports))
          
        def minCost_rule(model):
            return (cargoShipCosts(model) + portCosts(model))
        
        model.SystemCost = Objective(rule = minCost_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################


        ###################       START CONSTRAINTS     ###################
        
        # can only build 1 ship type for 1 ship at maximum
        def shipBuildingTypeRule(model,ship):
            return sum(model.X[ship,shipType] for shipType in model.shipTypes) <= 1
        model.shipBuildingTypeConstraint = Constraint(model.ships,rule=shipBuildingTypeRule)        
    
        #can only send ships on routes if you have built the ship
        def shipRoutingBuiltRule(model,ship,portI,portJ,time):
            if(portI == portJ):
                return model.B[ship,portI,portJ,time] == 0
            else:
                return(model.B[ship,portI,portJ,time] <= sum(model.X[ship,shipType] for shipType in model.shipTypes))
        model.shipRoutingBuiltConstraint = Constraint(model.ships,model.ports,model.ports,model.horizon,rule=shipRoutingBuiltRule)        

    
        #can only send a ship on a route if the ship is in the correct home port
        def shipInPortScheduleRule(model,ship,portI,portJ,time):
            if(portI == portJ):
                return model.B[ship,portI,portJ,time] == 0
            else:
                return model.B[ship,portI,portJ,time] <= model.indicatorInPort[ship,portI,time]

        model.shipInPortScheduleConstraint = Constraint(model.ships,model.ports,model.ports,model.horizon,rule=shipInPortScheduleRule)        


        #ship is traveling definition-if en route value is 1, else value is zero
        def shipTravelingDefinitionRule(model,ship,time):
            #ship not traveling at start of simulation
            if time == 0:
                return(model.indicatorIsTraveling[ship,time] == 0)
            else:
                return(model.indicatorIsTraveling[ship,time] == (sum((model.indicatorInPort[ship,port,time-1] - model.indicatorInPort[ship,port,time])
                                                         for port in model.ports) + model.indicatorIsTraveling[ship,time-1]))
        model.shipTravelingDefinitionConstraint = Constraint(model.ships,model.horizon,rule=shipTravelingDefinitionRule)        

        #make sure the ships start off in one port
        def shipInitialPortLocationRule(model,ship):
            return(sum(model.indicatorInPort[ship,port,0] for port in model.ports)  == 1)
        model.shipInitialPortLocationConstraint = Constraint(model.ships,rule=shipInitialPortLocationRule)        

        #make sure the ship is only at one port or traveling
        def shipPortMaximumAmountRule(model,ship,time):
            return((sum(model.indicatorInPort[ship,port,time]  for port in model.ports) == (1- model.indicatorIsTraveling[ship,time])))
        model.shipPortMaximumAmountConstraint = Constraint(model.ships,model.horizon,rule=shipPortMaximumAmountRule)        
        
        def shipFuturePortRule(model,ship,portI,portJ,time):
            if portJ == portI:
                return model.B[ship,portI,portJ,time] == 0
            else:
                if(time+1 >= len(model.horizon)):
                    #if unable to make port in time, don't send ship
                    return(model.B[ship,portI,portJ,time] == 0)
                else:
                    #the ship will be at that port only once in the future time
                    
                    return((model.indicatorIsTraveling[ship,time+1]) >= model.B[ship,portI,portJ,time])

        model.shipFuturePortConstraint = Constraint(model.ships,model.ports,model.ports,model.horizon,rule=shipFuturePortRule)        
        
        
        #the ship will be in the port at the final time
        def shipFuturePortTravelTimeRule(model,ship,portI,portJ,time):
            if portJ == portI:
                return model.B[ship,portI,portJ,time] == 0
            else:        
                #need to add one as you get there and officially in port the end of the day
                arrivalTime = time + ceil(model.length[portI,portJ]/model.shipSpeed) + 1
                if(arrivalTime > (len(model.horizon)-1)):
                    #if unable to make port in time, don't send ship
                    return(model.B[ship,portI,portJ,time] == 0)
                else:
                    #the ship will be at that port  in the future time
                    return(model.indicatorInPort[ship,portJ,arrivalTime] == model.B[ship,portI,portJ,time])
        model.shipFuturePortTravelTimeConstraint = Constraint(model.ships,model.ports,model.ports,model.horizon,rule=shipFuturePortTravelTimeRule)        
         
        
        
        #in order for a ship to be at a port, the port must be built
        def portCapacityRule(model,ship,port,time):
            return(model.indicatorInPort[ship,port,time] <= model.psPortCapacity[port])
        model.portCapacityConstraint = Constraint(model.ships,model.ports,model.horizon,rule=portCapacityRule)        
        
        #capacity available on ship must be less than total cargo ship capacity
        def csAvailCapacityRule(model,ship,time):
            return(model.csAvail[ship,time] <= sum(model.X[ship,shipType]*model.bulkSize[shipType] for shipType in model.shipTypes))
        model.csAvailCapacityConstraint = Constraint(model.ships,model.horizon,rule=csAvailCapacityRule)        
        
        #how much cargo you transfer must be less than or equal to how much you have on ship
        #once again the dual is used to enforce the statement we want
        def ctUpperLimitRule(model,ship,port,time):
            return(model.cargoTransfer[ship,port,time] <= model.csAvail[ship,time])
        model.ctUpperLimitConstraint = Constraint(model.ships,model.ports,model.horizon,rule=ctUpperLimitRule)        
        
        #making sure the cargo transfer only happens when the ship is at a port
        def ctInPortRule(model,ship,port,time):
            return(model.cargoTransfer[ship,port,time] <= model.indicatorInPort[ship,port,time]*sum(model.bulkSize[shipType] for shipType in model.shipTypes))
        model.ctInPortConstraint = Constraint(model.ships,model.ports,model.horizon,rule=ctInPortRule)        
        
        
        #cargo storage availability definition (previous day quantity + any cargo transfer)
        def csAvailDefinitionRule(model,ship,time):
            if(time == 0):
                #start of simulation there is not fuel in ships
                return(model.csAvail[ship,time] == 0)
            else:
                return(model.csAvail[ship,time] == model.csAvail[ship,time-1] + (sum(model.cargoTransfer[ship,port,time] for port in model.ports)))
        model.csAvailDefinitionConstraint = Constraint(model.ships,model.horizon,rule=csAvailDefinitionRule)        
        
        #cargo transfer must be less than port capacity (both positive-discharge and negative-loading fuel on)
        def ctPortCapacityPositiveRule(model,port,time):
            return((sum(model.cargoTransfer[ship,port,time] for ship in model.ships) <= model.psPortCapacity[port]))
        model.ctPortCapacityPositiveConstraint = Constraint(model.ports,model.horizon,rule=ctPortCapacityPositiveRule)        
        
        #cargo transfer must be less than port capacity (both positive-discharge and negative-loading fuel on)
        def ctPortCapacityNegativeRule(model,port,time):
            return((sum(model.cargoTransfer[ship,port,time] for ship in model.ships) >= -1*model.psPortCapacity[port]))
        model.ctPortCapacityNegativeConstraint = Constraint(model.ports,model.horizon,rule=ctPortCapacityNegativeRule)        
                
        #port storage availability definition (previous quantity + any cargo transfer - any fuel deployed to meet demand)
        def psAvailDefinitionRule(model,port,time):
            if(time == 0):
                #all ports start off with no fuel in storage
                return(model.psAvail[port,time]  == 0)
            else:
                return(model.psAvail[port,time] == (model.psAvail[port,time-1] + sum(model.cargoTransfer[ship,port,time] for ship in model.ships) - model.psDeploy[port,time]))
        model.psAvailDefinitionConstraint = Constraint(model.ports,model.horizon,rule=psAvailDefinitionRule)        
        
        #storage built for fuel must be greater than or equal to how much you have in storage at any given time
        def psAvailStorageLimitRule(model,port,time):
            return(model.psAvail[port,time] <= model.psStorageCapacity[port])
        model.psAvailStorageLimitConstraint = Constraint(model.ports,model.horizon,rule=psAvailStorageLimitRule)        
        
        #must have enough fuel in storage to deploy
        def psDeployStorageLimitRule(model,port,time):
            return(model.psDeploy[port,time] <= model.psAvail[port,time])
        model.psDeployStorageLimitConstraint = Constraint(model.ports,model.horizon,rule=psDeployStorageLimitRule)        
        
        
        #meet demand constraint-port storage deployments and fuel transfers
        # negative demand means the port is supplying fuel
        def meetDemandRule(model,region,time):
            return(sum(model.portRegionParameter[port,region]*(model.psDeploy[port,time] + sum(model.cargoTransfer[ship,port,time] for ship in model.ships)) for port in model.ports) == model.demand[region,time])
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
                
        
        
        solver = SolverFactory('glpk')
        solver.solve(instance)
        print(instance.psPortCapacity[0].value)
    

        hourlyDvDataset = pd.DataFrame(0.0, index=np.arange(len(inputDataset["cfSolar"])), columns=hourlyDecisionVariables)    
        for ship in inputDataset["ships"]:
            
                    hourlyDvDataset["windGen"][hour] = singleDvDataset["windCapacity"][0]*inputDataset["cfWind"][hour]
                    hourlyDvDataset["solarGen"][hour] = singleDvDataset["solarCapacity"][0]*inputDataset["cfSolar"][hour]
                    hourlyDvDataset["asuGen"][hour] = instance.asuGen[hour].value
                    hourlyDvDataset["hbGen"][hour] = instance.hbGen[hour].value    
                    hourlyDvDataset["hsStore"][hour] = instance.hsStore[hour].value    
                    hourlyDvDataset["bsStore"][hour] = instance.bsStore[hour].value    
                    hourlyDvDataset["hsAvail"][hour] = instance.hsAvail[hour].value    
                    hourlyDvDataset["bsAvail"][hour] = instance.bsAvail[hour].value    
                    hourlyDvDataset["hsDeploy"][hour] = instance.hsDeploy[hour].value    
                    hourlyDvDataset["bsDeploy"][hour] = instance.bsDeploy[hour].value
                    hourlyDvDataset["fcDeploy"][hour] = instance.fcDeploy[hour].value
                    
                    #for later data analysis
                    hourlyDvDataset["timestep"][hour] = hour + 1   

        print("done")
        

        