from fileinput import filename
from pyomo.environ import *
from pyomo.opt import SolverFactory
import pyomo as pyo
from pytest import param
import pandas as pd
import numpy as np
import os.path
import math

class greenHydrogenProduction:
    def writeDataFile(dataFileName,inputDataset):
        with open('../modelInputs/'+str(dataFileName)+'.dat', 'w') as f:
            
            
            #horizon (time) set
            f.write('set horizon := ')
            for i in range(len(inputDataset["cfWind"])):
                f.write('%d ' % i)
            f.write(';\n\n')

            #ey plants set
            f.write('set eyPlants := ')
            for i in range(len(inputDataset["capexEY"])):
                f.write('%d ' % i)
            f.write(';\n\n')
            
            
            #simplifying writing .dat file with for loop
            paramNames = inputDataset.keys()
            
            #single param index names-for writing correct structure of .dat file
            singleParamIndexNames = ["cfWind","cfSolar","capexEY","fixedOpexEY","variableOpexEY","energyUseEY","stackSize"]
            
            
            for paramName in paramNames:
                if((paramName in ["horizon","eyPlants"])):
                    #skip names as they are sets defined above
                    continue
                elif(paramName in singleParamIndexNames):
                    #writing correct pyomo structure for re generation
                    f.write('param %s := \n' % (paramName))
                    for i in range(len(inputDataset[paramName])):
                        if(i != len(inputDataset[paramName])-1):
                            f.write('%d %f \n' % (i,inputDataset[paramName][i]))
                        else:
                            f.write('%d %f' % (i,inputDataset[paramName][i]))                    
                    f.write(';\n\n')
                else:
                    #all other parameters are single values
                    f.write('param %s := %f; \n' % (paramName,inputDataset[paramName]))
            
            print("Completed data file")
            

    def main(dataFileName,inputDataset,testMode=False):
        """Hourly operations of green hydrogen production complex

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
        #timesteps in simulation-based on capacity factor dataset
        model.horizon = RangeSet(0,len(inputDataset["cfSolar"])-1)
        
        #number of unique electroyzer (ey) models to select from
        model.eyPlants = RangeSet(0,len(inputDataset["capexEY"])-1)
        
        ################### END SETS  ###################


        
        ################### START PARAMETERS  ###################
        #hydrogen demand over simulation timeseries
        model.hydrogenDemand = Param()
        
        #respective capacity factor timeseries data for wind and solar site
        model.cfWind = Param(model.horizon)
        model.cfSolar = Param(model.horizon)
        
        #chemical efficiency of storing hydrogen in hydrogen tank
        model.hsStoreEfficiency = Param()
        
        #chemical efficiency of deploying hydrogen from tank
        model.hsDeployEfficiency = Param()

        #energy efficiency of storing energy in battery (e.g. you need to put in 1.2 kW to store 1 kW)
        model.bsStoreEfficiency = Param()
        
        #energy efficiency of deploying energy from battery
        model.bsDeployEfficiency = Param()        
        
        #vaporization rate of H2 in percent stored per timestep
        model.hsVaporizationRate = Param()
        
                
        #Looking at CAPEX for wind and solar per MW
        model.capexWind = Param()
        model.capexSolar = Param()
        
        #capex for electroysis depending on plant size (to capture economics of scale)
        model.capexEY = Param(model.eyPlants)
        
        #hydrogen storage CAPEX per kg H2
        model.capexHS = Param()

        #battery storage CAPEX per MWh
        model.capexBS = Param()
        

        
        #same outline above for different stages but now looking at fixed OPEX
        model.fixedOpexWind = Param()
        model.fixedOpexSolar = Param()
        model.fixedOpexEY = Param(model.eyPlants)
        model.fixedOpexHS = Param()
        model.fixedOpexBS = Param()

        #Now only looking at variable OPEX for EY as all the other technologies are assumed to have 
        #negligible variable OPEX
        model.variableOpexEY = Param(model.eyPlants)

       
       
        #energy consumption for each EY model type MWh/kg H2
        model.energyUseEY = Param(model.eyPlants)
        
        #energy consumption for Hydrogen storage: MWh/kg H2
        model.energyUseHS = Param()
        
             
       
        #stack size (rated energy for EY-MW) from each EY model type
        model.stackSize = Param(model.eyPlants)
        
        #number of periods that the plants will be in operation
        model.plantLifetime = Param()

        #WACC or discount rate for plant operations
        model.r = Param()
        
        #utilization ratio of plant (not used in model but calculated for total hydrogen production)
        model.utilizationRatio = Param()
        ################### END PARAMETERS  ###################
        
        
        
        
        ################### START DECISION VARIABLES  ###################
        #how much wind capacity to build
        model.windCapacity = Var(domain=NonNegativeReals)
        
        #how much solar capacity to build
        model.solarCapacity = Var(domain=NonNegativeReals)
        
        #how many stacks to build of model i for EY (so only integers)
        model.eyCapacity = Var(model.eyPlants, domain = NonNegativeIntegers)
        
        #total battery storage capacity to build (MWh)
        model.bsCapacity = Var(domain=NonNegativeReals)
        
        #total hydrogen storage capacity to build (kg H2)
        model.hsCapacity = Var(domain=NonNegativeReals)
        
        #H2 (kg) to produce from models i at timestep t
        model.eyGen = Var(model.eyPlants,model.horizon,domain=NonNegativeReals)

        #amount of hydrogen (kg) to store in tanks at timestep t
        model.hsStore = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy (MWh) to store in battery storage at timestep t
        model.bsStore = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of hydrogen (kg) in storage at timestep t which can be used
        model.hsAvail = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy (MWh) available in battery at timestep t
        model.bsAvail = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of hydrogen (kg) to deploy to HB process at timestep t
        model.hsDeploy = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy (MWh) to release into islanded grid at timestep t
        model.bsDeploy = Var(model.horizon,domain=NonNegativeReals)
    
        ################### END DECISION VARIABLES    ###################
        
        
        
        ###################     START OBJECTIVE     ###################
        #sum up the CAPEX, fixed OPEX, and variable OPEX costs for each of the 7 components of the green hydrogen value chain
        def windCosts(model):
            #sum of capex multiplied by wind capacity built + 
            #operational fixed costs*number of plant years that the OPEX is applied and then factor in time value of money
            return (model.windCapacity*(model.capexWind 
                                        + sum((model.fixedOpexWind/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))
             
        def solarCosts(model):
            #sum of capex multiplied by solar capacity built + 
            #operational fixed costs*number of plant years that the OPEX is applied
            return (model.solarCapacity*(model.capexSolar 
                                         + sum((model.fixedOpexSolar/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))

        def eyCosts(model):
            # have a temporary fix for running model without annual data for variable OPEX(8760/len*+(model.horizon)))-calculates the scaling factor for full year expenditures
            # stackSize[i]*eyModelCapacity[i] = total MW consumption of ey model i
            # need to then multiply by capexEY (in $/MW) and fixed OPEX ($/MW) including discount factor
            # for variable ($/kg H2) multiply by generation at each hour (this could be the water cost)
            return (sum(model.stackSize[i]*model.eyCapacity[i]*(model.capexEY[i] + 
                    sum((model.fixedOpexEY[i]/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime))))  for i in model.eyPlants) +
                    sum((8760/len(model.horizon))*sum(model.variableOpexEY[i]*model.eyGen[i,t] for i in model.eyPlants)/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))
        
        def hsCosts(model):
            #similar to wind and solar costs-sum up capex for hydrogen storage and then fixed OEPX 
            # however for hsCapacity (in kg) you need to convert to MW as capexHS and fixedOpxHS are in $/MW
            #energyUseHS is in MWh/kg thus multiplying by kg leaves us with MWh on a per hour basis for MW (assuming 1 MW capacity can deploy for 1 MWh)
            return (model.hsCapacity*(model.capexHS + 
                    sum((model.fixedOpexHS/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))
       
        def bsCosts(model):
            #same as hsCosts but dont have to change bsCapacity to MW as already in MWh
            return (model.bsCapacity*(model.capexBS + 
                    sum((model.fixedOpexBS/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))                      

      
        
        def minCost_rule(model):
            return (windCosts(model) + solarCosts(model) + eyCosts(model) + hsCosts(model) + 
                    bsCosts(model))
        
        model.SystemCost = Objective(rule = minCost_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################
    
        ###################       START CONSTRAINTS     ###################
        #meet the hydrogen production targets for demand over the entire production basis (converting total simulation run multiplied by ratio to convert to daily basis)
        def meetHydrogenDemand(model):
            return(sum((sum(model.eyGen[i,t] for i in model.eyPlants)- (model.hsStore[t]/model.hsStoreEfficiency) - model.hsDeploy[t]) for t in model.horizon) 
                   == model.hydrogenDemand)
        model.meetHydrogenDemandConstraint = Constraint(rule=meetHydrogenDemand)

        #generate enough energy to meet all required islanded components demand
        #Note: the energy usage parameters should encapsulate the energy efficiencies of each of the stages
        def energyDemand(model,t):
            #summing up all the demand from the various energy consumption stages (MWh/kg*kg produced gives us MWh)
            return (sum(model.energyUseEY[i]*model.eyGen[i,t] for i in model.eyPlants) +
                    model.energyUseHS*model.hsAvail[t] + (model.bsStore[t]/model.bsStoreEfficiency))
        
        def energyGen(model,t):
            #summing up generation from wind, solar, and battery storage (don't need to include efficiency for bs as 
            # the decision variable BSdeploy is the actual quantity deployed to grid)
            return(model.cfWind[t]*model.windCapacity + model.cfSolar[t]*model.solarCapacity + model.bsDeploy[t])
        
        def energyRule(model,t):
            #energy generated should always be equal to or greater than energy demanded
            return(energyDemand(model,t) <= energyGen(model,t))
        
        model.energyConstraint = Constraint(model.horizon,rule=energyRule)


        #battery storage operations definition (current energy available is 
        # zero at beginning and equal to previous available amount + new energy stored - (energy deployed + energy required to deploy it))
        def bsAvailEnergyRule(model,t):
            if t == 0:
                return(model.bsAvail[0] == 0)
            else:
                return(model.bsAvail[t] == model.bsAvail[t-1] + model.bsStore[t] - (model.bsDeploy[t])/model.bsDeployEfficiency)
        model.bsAvailEnergyDefConstraint = Constraint(model.horizon,rule=bsAvailEnergyRule)

        #max available energy you can have in storage is storage capacity
        def bsAvailUpperBoundRule(model,t):
            return(model.bsAvail[t] <= model.bsCapacity)
        model.bsAvailUpperBoundConstraint = Constraint(model.horizon,rule=bsAvailUpperBoundRule)
        
        #max amount of energy you can store in bs is max capacity - current energy charge at start - energy you deploy in hour
        #for simplicity, I assume you can not store energy in the hour and deploy it within the same hour-this would require finer resolution then hourly capacity factors
        def bsStoreUpperBoundRule(model,t):
            if(t==0):
                return(model.bsStore[t] <= model.bsCapacity)
            else:
                return(model.bsStore[t] <= model.bsCapacity - model.bsAvail[t-1])
        model.bsStoreUpperBoundConstraint = Constraint(model.horizon,rule=bsStoreUpperBoundRule)
        
        #energy deployed (and required) from storage must be less than energy available
        def bsDeployUpperBoundRule(model,t):
            if(t==0):
                return(model.bsDeploy[t] == 0)
            else:
                return(model.bsDeploy[t]/model.bsDeployEfficiency <= model.bsAvail[t-1])
                
        model.bsDeployUpperBoundConstraint = Constraint(model.horizon,rule=bsDeployUpperBoundRule)


        #hydrogen storage operations definition (current hydrogen available is zero at beginning and equal to previous available amount + new hydrogen stored - (hydrogen deployed + hydrogen required to deploy it))
        def hsAvailEnergyRule(model,t):
            if t == 0:
                return(model.hsAvail[0] == 0)
            else:
                return(model.hsAvail[t] == (1-model.hsVaporizationRate)*model.hsAvail[t-1] + model.hsStore[t] - ((model.hsDeploy[t])/model.hsDeployEfficiency))
        model.hsAvailEnergyDefConstraint = Constraint(model.horizon,rule=hsAvailEnergyRule)

        #max available hydrogen in storage is storage capacity
        def hsAvailUpperBoundRule(model,t):
            return(model.hsAvail[t] <= model.hsCapacity)
        model.hsAvailUpperBoundConstraint = Constraint(model.horizon,rule=hsAvailUpperBoundRule)
        
        #max amount of hydrogen you can store in hs is remaining space available (diff of hydrogen capacity - hydrogen available)
        def hsStoreUpperBoundRule(model,t):
            if(t==0):
                return(model.hsStore[t] <= model.hsCapacity)
            else:
                return(model.hsStore[t] <= model.hsCapacity - model.hsAvail[t-1])
        model.hsStoreUpperBoundConstraint = Constraint(model.horizon,rule=hsStoreUpperBoundRule)
        
        #hydrogen deployed (and also required to deploy) from storage must be less than hydrogen available
        def hsDeployUpperBoundRule(model,t):
            if(t==0):
                return(model.hsDeploy[t] == 0)
            else:
                return(model.hsDeploy[t]/model.hsDeployEfficiency <= model.hsAvail[t-1])
        model.hsDeployUpperBoundConstraint = Constraint(model.horizon,rule=hsDeployUpperBoundRule)
                
        #amount of hydrogen to store (and lost in storing) must be less than or equal to hydrogen generated from all EY stacks
        def hsStoreGenUpperBoundRule(model,t):
            return((model.hsStore[t]/model.hsStoreEfficiency) <= sum(model.eyGen[i,t] for i in model.eyPlants))
        model.hsStoreGenUpperBoundConstraint = Constraint(model.horizon,rule=hsStoreGenUpperBoundRule)
        
        #hydrogen production (in kg) from all the stacks in model i must be less than total number built*output per unit (have to convert stackSize (MW) to kg (and thus divide by energyUsage (MWh/kg)))
        def eyGenUpperBoundRule(model,i,t):
            return(model.eyGen[i,t] <= (model.stackSize[i]/model.energyUseEY[i])*model.eyCapacity[i])
        model.eyGenUpperBoundConstraint = Constraint(model.eyPlants,model.horizon,rule=eyGenUpperBoundRule)
        
        
        ###################       END   CONSTRAINTS     ###################
    


        ###################          WRITING DATA       ###################
        if(os.path.isfile(f"../dataInputs/{dataFileName}.dat")):
            print(f"Data file {dataFileName} already exists!\nSkipping creating .dat file")
        else:
            #print(f"Data file {dataFileName} does not exist.\nCreating .dat file")
            greenHydrogenProduction.writeDataFile(dataFileName,inputDataset)
        
        # load in data for the system
        data = DataPortal()
        data.load(filename=f"../modelInputs/{dataFileName}.dat", model=model)
        instance = model.create_instance(data)
                
        
        
        solver = SolverFactory('glpk')
        result = solver.solve(instance)
        #instance.display()
        
        
        #setting up structure in order to get out decision variables (and objective) and save in correct excel format
        singleDecisionVariables = ["windCapacity","solarCapacity","bsCapacity",
                                        "hsCapacity","totalSystemCost","LCOH","windCosts",
                                        "solarCosts","eyCosts","hsCosts","bsCosts",
                                        "windCapexCosts","windOpexCosts","solarCapexCosts",
                                        "solarOpexCosts","eyCapexCosts","eyOpexCosts",
                                        "hsCapexCosts","hsOpexCosts","bsCapexCosts", "bsOpexCosts"]
        
        
        
        #included wind and solar generation for simplifying data analysis and timestep
        hourlyDecisionVariables = ["windGen","solarGen","hsStore","bsStore","hsAvail",
                                   "bsAvail", "hsDeploy","bsDeploy","timestep"]
        
        #eyDecisionVariables =  ["eyCapacity"]
        
        #eyHourlyDecisionVariables = ["eyGen"]
        

        singleDvDataset = pd.DataFrame(0.0, index=np.arange(1), columns=singleDecisionVariables)

        hourlyDvDataset = pd.DataFrame(0.0, index=np.arange(len(inputDataset["cfSolar"])), columns=hourlyDecisionVariables)
        
        eySingleDvDataset = pd.DataFrame(0.0, index=np.arange(len(inputDataset["capexEY"])), columns=np.arange(len(inputDataset["capexEY"]))) 
        
        eyHourlyDvDataset = pd.DataFrame(0.0, index=np.arange(len(inputDataset["cfSolar"])), columns=np.arange(len(inputDataset["capexEY"]))) 
        
        #assigning single values to df
        singleDvDataset["windCapacity"][0] = instance.windCapacity.value
        singleDvDataset["solarCapacity"][0] = instance.solarCapacity.value
            
        singleDvDataset["bsCapacity"][0] = instance.bsCapacity.value            
        singleDvDataset["hsCapacity"][0] = instance.hsCapacity.value
        singleDvDataset["totalSystemCost"][0] = value(instance.SystemCost)
        
        #still assigning single values to df however looking at LCOH and various segments contributing
        totalHydrogenProduction = instance.utilizationRatio*sum((inputDataset["hydrogenDemand"]*8760/len(instance.horizon))/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))
        #totalHydrogenProduction = instance.utilizationRatio*sum((inputDataset["hydrogenDemand"]*8760/len(instance.horizon))/(math.pow((1+0),t)) for t in np.arange(instance.plantLifetime))
        
        
        singleDvDataset["LCOH"][0] = value(instance.SystemCost)/totalHydrogenProduction
        
        singleDvDataset["windCosts"][0] = (instance.windCapacity.value*(instance.capexWind 
                                        + sum((instance.fixedOpexWind/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalHydrogenProduction        
        singleDvDataset["windCapexCosts"] = (instance.windCapacity.value*(instance.capexWind))/totalHydrogenProduction
        singleDvDataset["windOpexCosts"] = (instance.windCapacity.value*sum((instance.fixedOpexWind/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))))/totalHydrogenProduction
        
        
        
        singleDvDataset["solarCosts"][0] = (instance.solarCapacity.value*(instance.capexSolar 
                                         + sum((instance.fixedOpexSolar/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalHydrogenProduction
        singleDvDataset["solarCapexCosts"] = (instance.solarCapacity.value*(instance.capexSolar))/totalHydrogenProduction
        singleDvDataset["solarOpexCosts"] = (instance.solarCapacity.value*sum((instance.fixedOpexSolar/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))))/totalHydrogenProduction
        
        
        
        singleDvDataset["eyCosts"][0] = (sum(instance.stackSize[i]*instance.eyCapacity[i].value*(instance.capexEY[i] + 
                    sum((instance.fixedOpexEY[i]/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))))  for i in instance.eyPlants) +
                    sum((8760/len(instance.horizon))*sum(instance.variableOpexEY[i]*instance.eyGen[i,t].value for i in instance.eyPlants)/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))/totalHydrogenProduction
        singleDvDataset["eyCapexCosts"] = (sum(instance.stackSize[i]*instance.eyCapacity[i].value*instance.capexEY[i] for i in instance.eyPlants))/totalHydrogenProduction
        singleDvDataset["eyOpexCosts"] = (sum(instance.stackSize[i]*instance.eyCapacity[i].value*sum((instance.fixedOpexEY[i]/(math.pow((1+value(instance.r)),t))) for t in np.arange(instance.plantLifetime)) for i in instance.eyPlants) + sum((8760/len(instance.horizon))*sum(instance.variableOpexEY[i]*instance.eyGen[i,t].value for i in instance.eyPlants)/(math.pow((1+value(instance.r)),t)) for t in np.arange(instance.plantLifetime)))/totalHydrogenProduction
        
        
        
        singleDvDataset["hsCosts"][0] = (instance.hsCapacity.value*(instance.capexHS + 
                    sum((instance.fixedOpexHS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalHydrogenProduction
        singleDvDataset["hsCapexCosts"] = (instance.hsCapacity.value*(instance.capexHS))/totalHydrogenProduction
        singleDvDataset["hsOpexCosts"] = (instance.hsCapacity.value*sum((instance.fixedOpexHS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))))/totalHydrogenProduction
        
        
        singleDvDataset["bsCosts"][0] = (instance.bsCapacity.value*(instance.capexBS + 
                    sum((instance.fixedOpexBS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalHydrogenProduction                      
        singleDvDataset["bsCapexCosts"] = (instance.bsCapacity.value*(instance.capexBS))/totalHydrogenProduction
        singleDvDataset["bsOpexCosts"] = (instance.bsCapacity.value*sum((instance.fixedOpexBS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime))))/totalHydrogenProduction
        
        
        
        
        #assigning hourly values to dfs
        for hour in np.arange(len(inputDataset["cfSolar"])):
            hourlyDvDataset["windGen"][hour] = singleDvDataset["windCapacity"][0]*inputDataset["cfWind"][hour]
            hourlyDvDataset["solarGen"][hour] = singleDvDataset["solarCapacity"][0]*inputDataset["cfSolar"][hour]
            hourlyDvDataset["hsStore"][hour] = instance.hsStore[hour].value    
            hourlyDvDataset["bsStore"][hour] = instance.bsStore[hour].value    
            hourlyDvDataset["hsAvail"][hour] = instance.hsAvail[hour].value    
            hourlyDvDataset["bsAvail"][hour] = instance.bsAvail[hour].value    
            hourlyDvDataset["hsDeploy"][hour] = instance.hsDeploy[hour].value    
            hourlyDvDataset["bsDeploy"][hour] = instance.bsDeploy[hour].value
            
            #for later data analysis
            hourlyDvDataset["timestep"][hour] = hour + 1   

        #assigning single dvs for ey types
        eySingleDvDataset = pd.DataFrame(columns=np.arange(len(inputDataset["capexEY"])), index=range(2))
        for eyUnit in np.arange(len(inputDataset["capexEY"])):
            #looking at capacity and load factor
            eySingleDvDataset[eyUnit][0] = (1/instance.energyUseEY[eyUnit])*instance.stackSize[eyUnit]*instance.eyCapacity[eyUnit].value
            if(instance.eyCapacity[eyUnit].value != 0):
                eySingleDvDataset[eyUnit][1] = sum(instance.eyGen[eyUnit,hour].value for hour in np.arange(len(instance.horizon)))/(len(instance.horizon)*(1/instance.energyUseEY[eyUnit])*instance.stackSize[eyUnit]*instance.eyCapacity[eyUnit].value)
            else:
                eySingleDvDataset[eyUnit][1] = 0
        #assigning hourly dvs for each ey unit
        for eyUnit in np.arange(len(inputDataset["capexEY"])):
            for hour in np.arange(len(inputDataset["cfSolar"])):
                eyHourlyDvDataset[eyUnit][hour] = instance.eyGen[eyUnit,hour].value          
        
        
        #now saving 4 datasets to different sheets in same excel file
        excelOutputFileName = f"../modelOutputs/{dataFileName}.xlsx"
        with pd.ExcelWriter(excelOutputFileName) as writer:  
            singleDvDataset.to_excel(writer,sheet_name='singleValueDvs') 
            
            hourlyDvDataset.to_excel(writer,sheet_name='hourlyValueDvs') 
            
            eySingleDvDataset.to_excel(writer,sheet_name='singleEyValueDvs') 
            
            eyHourlyDvDataset.to_excel(writer,sheet_name='hourlyEyValueDvs') 
        
        print(f"Model output results saved to {excelOutputFileName}")
        