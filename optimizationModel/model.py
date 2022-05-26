from fileinput import filename
from pyomo.environ import *
from pyomo.opt import SolverFactory
import pyomo as pyo
from pytest import param
import pandas as pd
import numpy as np
import os.path
import math

class greenAmmoniaProduction:
    def writeDataFile(dataFileName,inputDataset):

        with open('modelInputs/'+str(dataFileName)+'.dat', 'w') as f:
            
            
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
        """Hourly operations of green ammonia production complex

        Args:
            dataFileName (str): .dat file name which will read in/be created data for model run
            inputDataset (dict): see README for further clarification on what parameters are expected to be inputted into spreadsheet
            testMode (bool): automatically set to false, if true-will delete the .dat input file and output file associated with the dataFileName
        """ 
        #deleting files if test mode is activated
        if(testMode):
            try:
                os.remove(f"modelInputs/{dataFileName}.dat")
                os.remove(f"modelOutputs/{dataFileName}.xlsx")
            except:
                print("Test mode activated but one of files already deleted")
        # creating optimization model with pyomo
        model = AbstractModel()

        ################### START SETS  ###################
        #timesteps in simulation
        model.horizon = RangeSet(0,len(inputDataset["cfSolar"])-1)
        
        #number of unique electroyzer (ey) models to select from
        model.eyPlants = RangeSet(0,len(inputDataset["capexEY"])-1)
        
        ################### END SETS  ###################


        
        ################### START PARAMETERS  ###################
        #ammonia demand for simulation 
        model.ammoniaDemand = Param()
        
        #respective capacity factor timeseries data for wind and solar site
        model.cfWind = Param(model.horizon)
        model.cfSolar = Param(model.horizon)
        
        #chemicial efficiency of storing in hydrogen tank
        model.hsStoreEfficiency = Param()
        
        #chemicial efficiency of deploying hydrogen from tank
        model.hsDeployEfficiency = Param()

        #energy efficiency of storing energy in battery (e.g. you need to put in 1.2 kW to store 1 kW)
        model.bsStoreEfficiency = Param()
        
        #energy efficiency of deploying hydrogen from tank
        model.bsDeployEfficiency = Param()        
        
        #chemical efficiency of hydrogen into HB process (e.g.-1.5 tons H2 input will output 1 ton ammonia)
        model.hbHydrogenEfficiency = Param() 
        
        #chemical efficiency of nitrogen into HB process (e.g.-1.5 tons N2 input will output 1 ton ammonia)
        model.hbNitrogenEfficiency = Param() 
                
        #Looking at CAPEX for wind and solar per MW
        model.capexWind = Param()
        model.capexSolar = Param()
        
        #capex for electroysis depending on plant size (to capture economies of scale)
        model.capexEY = Param(model.eyPlants)
        
        #hydrogen storage CAPEX per ton H2 produced
        model.capexHS = Param()

        #battery storage CAPEX per MW
        model.capexBS = Param()
        
        #air separation unit CAPEX per ton N2 produced
        model.capexASU = Param()
        
        #Haber-Bosch ammonia plant  CAPEX per ton NH2 produced
        model.capexHB = Param()
        
        #same outline above for different stages but now looking at fixed OPEX
        model.fixedOpexWind = Param()
        model.fixedOpexSolar = Param()
        model.fixedOpexEY = Param(model.eyPlants)
        model.fixedOpexHS = Param()
        model.fixedOpexBS = Param()
        model.fixedOpexASU = Param()
        model.fixedOpexHB = Param()        

        #same outline above for different stages but now looking at variable OPEX
        model.variableOpexEY = Param(model.eyPlants)

       
       
        #energy consumption for each EY model type per unit output of H2
        model.energyUseEY = Param(model.eyPlants)
        
        #energy consumption for Hydrogen storage per H2
        model.energyUseHS = Param()
        
        #energy consumption per unit output of N2
        model.energyUseASU = Param()
        
        #energy consumption per unit output of NH3
        model.energyUseHB = Param()
        
        #minimum operating percentage of nameplate capacity for ASU
        model.minCapacityASU = Param()
        
        #minimum operating percentage of nameplate capacity for Ammonia plant        
        model.minCapacityHB = Param()
       
        #stack size (how much hydrogen can be producded) from each EY model type
        model.stackSize = Param(model.eyPlants)
        
        #number of periods that the plants will be in operation
        model.plantLifetime = Param()
        
        #WACC or discount rate for plant operations
        model.r = Param()
        ################### END PARAMETERS  ###################
        
        
        
        ################### START DECISION VARIABLES  ###################
        #how much wind capacity to build
        model.windCapacity = Var(domain=NonNegativeReals)
        
        #how much solar capacity to build
        model.solarCapacity = Var(domain=NonNegativeReals)
        
        #how many stacks to build of model i for EY (so only integers)
        model.eyCapacity = Var(model.eyPlants, domain = NonNegativeIntegers)
        
        #total battery storage capacity to build
        model.bsCapacity = Var(domain=NonNegativeReals)
        
        #total hydrogen storage capacity to build
        model.hsCapacity = Var(domain=NonNegativeReals)
        
        #total ASU capacity to build
        model.asuCapacity = Var(domain=NonNegativeReals)
        
        #total ammonia plant nameplate capacity to build (HB process)
        model.hbCapacity = Var(domain=NonNegativeReals)
        
        #H2 to produce from models i at timestep t
        model.eyGen = Var(model.eyPlants,model.horizon,domain=NonNegativeReals)
        
        #N2 to produce from ASU at timestep t
        model.asuGen = Var(model.horizon,domain=NonNegativeReals)
        
        #NH3 to produce from ammonia plant (HB) at timestep t
        model.hbGen = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of hydrogen to store in tanks at timestep t
        model.hsStore = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy to store in battery storage at timestep t
        model.bsStore = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of hydrogen in storage at timestep t which can be used
        model.hsAvail = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy available in battery at timestep t
        model.bsAvail = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of hydrogen to deploy to HB process at timestep t
        model.hsDeploy = Var(model.horizon,domain=NonNegativeReals)
        
        #amount of energy to release into islanded grid at timestep t
        model.bsDeploy = Var(model.horizon,domain=NonNegativeReals)
    
        ################### END DECISION VARIABLES    ###################
        
        ###################     START OBJECTIVE     ###################
        #sum up the CAPEX, fixed OPEX, and variable OPEX costs for each of the 7 components of the green ammonia value chain
        
        def windCosts(model):
            return (model.windCapacity*(model.capexWind 
                                        + sum((model.fixedOpexWind/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))
             
        def solarCosts(model):
            return (model.solarCapacity*(model.capexSolar 
                                         + sum((model.fixedOpexSolar/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))

        def eyCosts(model):
            #have a temporary fix for running model without annual data for variable OPEX(8760/len*+(model.horizon)))-calculates the scaling factor for full year expenditures
            return (sum(model.stackSize[i]*model.eyCapacity[i]*(model.capexEY[i] + 
                    sum((model.fixedOpexEY[i]/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))) +
                    sum((8760/len(model.horizon))*model.variableOpexEY[i]*sum(model.eyGen[i,t2] for t2 in model.horizon)/(math.pow((1+model.r),t)) for t in model.horizon) for i in model.eyPlants))
        
        def hsCosts(model):
            return (model.energyUseHS*model.hsCapacity*(model.capexHS + 
                    sum((model.fixedOpexHS/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))
       
        def bsCosts(model):
            return (model.bsCapacity*(model.capexBS + 
                    sum((model.fixedOpexBS/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))                      

        def asuCosts(model):
            return (model.energyUseASU*model.asuCapacity*(model.capexASU + 
                    sum((model.fixedOpexASU/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime)))))                                                                

        def hbCosts(model):
            return (model.energyUseHB*model.hbCapacity*(model.capexHB + 
                    sum((model.fixedOpexHB/(math.pow((1+model.r),t)) for t in np.arange(model.plantLifetime))))) 
                    
        
        def minCost_rule(model):
            return (windCosts(model) + solarCosts(model) + eyCosts(model) + hsCosts(model) + 
                    bsCosts(model) + asuCosts(model) + hbCosts(model))
        
        model.SystemCost = Objective(rule = minCost_rule, sense = minimize)
        
        ###################       END OBJECTIVE     ###################
    
        ###################       START CONSTRAINTS     ###################
        #meet the ammonia production targets
        def meetAmmoniaDemand(model):
            return sum(model.hbGen[t] for t in model.horizon) == model.ammoniaDemand
        model.meetAmmoniaDemandConstraint = Constraint(rule=meetAmmoniaDemand)

        #generate enough energy to meet all required island components demand
        #Note: the energy usage parameters should encapsulate the energy efficiencies of each of the stages
        def energyDemand(model,t):
            return (sum(model.energyUseEY[i]*model.eyGen[i,t] for i in model.eyPlants) +
                    model.energyUseHS*model.hsAvail[t] + (model.bsStore[t]/model.bsStoreEfficiency) +
                    model.energyUseASU*model.asuGen[t] + model.energyUseHB*model.hbGen[t])
        
        def energyGen(model,t):
            return(model.cfWind[t]*model.windCapacity + model.cfSolar[t]*model.solarCapacity + model.bsDeployEfficiency*model.bsDeploy[t])
        
        def energyRule(model,t):
            return(energyDemand(model,t) <= energyGen(model,t))
        
        model.energyConstraint = Constraint(model.horizon,rule=energyRule)


        #battery storage operations definition (current energy available is zero at beginning and equal to previous available amount + new energy stored - (energy deployed + energy required to deploy it))
        def bsAvailEnergyRule(model,t):
            if t == 0:
                return(model.bsAvail[0] == 0)
            else:
                return(model.bsAvail[t] == model.bsAvail[t-1] + model.bsStore[t] - (model.bsDeploy[t])/model.bsDeployEfficiency)
        model.bsAvailEnergyDefConstraint = Constraint(model.horizon,rule=bsAvailEnergyRule)

        #max available energy storage is storage capacity
        def bsAvailUpperBoundRule(model,t):
            return(model.bsAvail[t] <= model.bsCapacity)
        model.bsAvailUpperBoundConstraint = Constraint(model.horizon,rule=bsAvailUpperBoundRule)
        
        #max amount of energy you can store in bs is remaining space available
        def bsStoreUpperBoundRule(model,t):
            return(model.bsStore[t] <= model.bsCapacity - model.bsAvail[t])
        model.bsStoreUpperBoundConstraint = Constraint(model.horizon,rule=bsStoreUpperBoundRule)
        
        #energy deployed from storage must be less than energy available
        def bsDeployUpperBoundRule(model,t):
            return(model.bsDeploy[t]/model.bsDeployEfficiency <= model.bsAvail[t])
        model.bsDeployUpperBoundConstraint = Constraint(model.horizon,rule=bsDeployUpperBoundRule)



        #hydrogen storage operations definition (current energy available is zero at beginning and equal to previous available amount + new energy stored - (energy deployed + energy required to deploy it))
        def hsAvailEnergyRule(model,t):
            if t == 0:
                return(model.hsAvail[0] == 0)
            else:
                return(model.hsAvail[t] == model.hsAvail[t-1] + model.hsStore[t] - (model.hsDeploy[t])/model.hsDeployEfficiency)
        model.hsAvailEnergyDefConstraint = Constraint(model.horizon,rule=hsAvailEnergyRule)

        #max available energy storage is storage capacity
        def hsAvailUpperBoundRule(model,t):
            return(model.hsAvail[t] <= model.hsCapacity)
        model.hsAvailUpperBoundConstraint = Constraint(model.horizon,rule=hsAvailUpperBoundRule)
        
        #max amount of energy you can store in bs is remaining space available
        def hsStoreUpperBoundRule(model,t):
            return(model.hsStore[t] <= model.hsCapacity - model.hsAvail[t])
        model.hsStoreUpperBoundConstraint = Constraint(model.horizon,rule=hsStoreUpperBoundRule)
        
        #energy deployed from storage must be less than energy available
        def hsDeployUpperBoundRule(model,t):
            return(model.hsDeploy[t]/model.hsDeployEfficiency <= model.hsAvail[t])
        model.hsDeployUpperBoundConstraint = Constraint(model.horizon,rule=hsDeployUpperBoundRule)
                
        #amount of hydrogen to store must be less than hydrogen generated from all EY stacks
        def hsStoreUpperBoundRule(model,t):
            return((model.hsStore[t]/model.hsStoreEfficiency) <= sum(model.eyGen[i,t] for i in model.eyPlants))
        model.hsStoreUpperBoundConstraint = Constraint(model.horizon,rule=hsStoreUpperBoundRule)
        
        #generation from all the stacks of model i must be less than total number built*output per unit
        def eyGenUpperBoundRule(model,i,t):
            return(model.eyGen[i,t] <= (model.stackSize[i]/model.energyUseEY[i])*model.eyCapacity[i])
        model.eyGenUpperBoundConstraint = Constraint(model.eyPlants,model.horizon,rule=eyGenUpperBoundRule)
        
        #ASU production can't exceed max capacity
        def asuGenUpperBoundRule(model,t):
            return(model.asuGen[t] <= model.asuCapacity)
        model.asuGenUpperBoundConstraint = Constraint(model.horizon,rule=asuGenUpperBoundRule)

        #Ammonia plant production (HB) can't exceed max capacity
        def hbGenUpperBoundRule(model,t):
            return(model.hbGen[t] <= model.hbCapacity)
        model.hbGenUpperBoundConstraint = Constraint(model.horizon,rule=hbGenUpperBoundRule)        
        
        #ASU plant not fall below its minimum hourly production capacity
        def asuGenLowerBoundRule(model,t):
            return(model.asuGen[t] >= model.minCapacityASU*model.asuCapacity)
        model.asuGenLowerBoundConstraint = Constraint(model.horizon,rule=asuGenLowerBoundRule)

        #Ammonia plant production (HB) can't exceed max capacity
        def hbGenLowerBoundRule(model,t):
            return(model.hbGen[t] >= model.minCapacityHB*model.hbCapacity)
        model.hbGenLowerBoundConstraint = Constraint(model.horizon,rule=hbGenLowerBoundRule)        
        
        #hydrogen input to the ammonia plant must be equal to the required hydrogen input ratio
        def hbHydrogenInputRule(model,t):
            return((1/model.hbHydrogenEfficiency)*(sum(model.eyGen[i,t]  for i in model.eyPlants)-model.hsStore[t]/model.hsStoreEfficiency + model.hsDeploy[t]) == model.hbGen[t])
        model.hbGenHydrogenInputConstraint = Constraint(model.horizon,rule=hbHydrogenInputRule)        
 
        #nitrogen input to the ammonia plant must be equal to the required hydrogen input ratio
        def hbNitrogenInputRule(model,t):
            return((1/model.hbNitrogenEfficiency)*(model.asuGen[t]) == model.hbGen[t])
        model.hbGenNitrogenInputConstraint = Constraint(model.horizon,rule=hbNitrogenInputRule)        
         
        ###################       END   CONSTRAINTS     ###################
    


        ###################          WRITING DATA       ###################
        if(os.path.isfile(f"dataInputs/{dataFileName}.dat")):
            print(f"Data file {dataFileName} already exists!\nSkipping creating .dat file")
        else:
            #print(f"Data file {dataFileName} does not exist.\nCreating .dat file")
            greenAmmoniaProduction.writeDataFile(dataFileName,inputDataset)
        
        # load in data for the system
        data = DataPortal()
        data.load(filename=f"modelInputs/{dataFileName}.dat", model=model)
        instance = model.create_instance(data)
        

        
        
        
        solver = SolverFactory('glpk')
        result = solver.solve(instance)
        #instance.display()
        
        
        #setting up structure in order to get out decision variables (and objective) and save in correct excel format
        singleDecisionVariables = ["windCapacity","solarCapacity","bsCapacity",
                                        "hsCapacity","asuCapacity","hbCapacity", "totalSystemCost",
                                        "LCOA","windCosts","solarCosts","eyCosts","hsCosts","bsCosts",
                                        "asuCosts","hbCosts"]
        
        #included wind and solar generation for simplifying data analysis and timestep
        hourlyDecisionVariables = ["windGen","solarGen","asuGen","hbGen","hsStore",
                                   "bsStore","hsAvail","bsAvail", "hsDeploy","bsDeploy","timestep"]
        
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
        singleDvDataset["asuCapacity"][0] = instance.asuCapacity.value            
        singleDvDataset["hbCapacity"][0] = instance.hbCapacity.value            
        singleDvDataset["totalSystemCost"][0] = value(instance.SystemCost)
        
        #still assigning single values to df however looking at LCOA and various segments contributing
        totalAmmoniaProduction = (inputDataset["ammoniaDemand"]*inputDataset["plantLifetime"]*8760/len(instance.horizon))
        
        singleDvDataset["LCOA"][0] = value(instance.SystemCost)/totalAmmoniaProduction
        singleDvDataset["windCosts"][0] = (instance.windCapacity.value*(instance.capexWind 
                                        + sum((instance.fixedOpexWind/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction        
       
        singleDvDataset["solarCosts"][0] = (instance.solarCapacity.value*(instance.capexSolar 
                                         + sum((instance.fixedOpexSolar/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction
        
        singleDvDataset["eyCosts"][0] = (sum(instance.stackSize[i]*instance.eyCapacity[i].value*(instance.capexEY[i] + 
                    sum((instance.fixedOpexEY[i]/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))) +
                    sum((8760/len(instance.horizon))*instance.variableOpexEY[i]*sum(instance.eyGen[i,t2].value for t2 in instance.horizon)/(math.pow((1+instance.r),t)) for t in instance.horizon) for i in instance.eyPlants))/totalAmmoniaProduction
        
        singleDvDataset["hsCosts"][0] = (instance.energyUseHS*instance.hsCapacity.value*(instance.capexHS + 
                    sum((instance.fixedOpexHS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction
        
        singleDvDataset["bsCosts"][0] = (instance.bsCapacity.value*(instance.capexBS + 
                    sum((instance.fixedOpexBS/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction                      
        
        singleDvDataset["asuCosts"][0] = (instance.energyUseASU*instance.asuCapacity.value*(instance.capexASU + 
                    sum((instance.fixedOpexASU/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction                                                                
        
        singleDvDataset["hbCosts"][0] = (instance.energyUseHB*instance.hbCapacity.value*(instance.capexHB + 
                    sum((instance.fixedOpexHB/(math.pow((1+instance.r),t)) for t in np.arange(instance.plantLifetime)))))/totalAmmoniaProduction 
       
        
        #assigning hourly values to dfs
        for hour in np.arange(len(inputDataset["cfSolar"])):
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
            
            #for later data analysis
            hourlyDvDataset["timestep"][hour] = hour + 1   

        #assigning single dvs for ey types
        for eyUnit in np.arange(len(inputDataset["capexEY"])):
            eySingleDvDataset[eyUnit][0] = instance.eyCapacity[eyUnit].value    

        #assigning hourly dvs for each ey unit
        for eyUnit in np.arange(len(inputDataset["capexEY"])):
            for hour in np.arange(len(inputDataset["cfSolar"])):
                eyHourlyDvDataset[eyUnit][hour] = instance.eyGen[eyUnit,hour].value          
        
        
        #now saving 4 datasets to different sheets in same excel file
        excelOutputFileName = f"modelOutputs/{dataFileName}.xlsx"
        with pd.ExcelWriter(excelOutputFileName) as writer:  
            singleDvDataset.to_excel(writer,sheet_name='singleValueDvs') 
            
            hourlyDvDataset.to_excel(writer,sheet_name='hourlyValueDvs') 
            
            eySingleDvDataset.to_excel(writer,sheet_name='singleEyValueDvs') 
            
            eyHourlyDvDataset.to_excel(writer,sheet_name='hourlyEyValueDvs') 
        
        print(f"Model output results saved to {excelOutputFileName}")
        
        '''   
        #creating dataframe of raw generation at each timestep
        dfRaw = pd.DataFrame(0.0, index=np.arange(len(demand)), columns=columnNames)
        
        
        #assigning generation values to df
        for x,techName in zip(range(len(lcoe)),technologyNames):
            for t in range(len(demand)):
                dfRaw[techName][t] = instance.x._data[x,t].value
                
        
        
        #now creating a second dataframe of percent generation of each technology at each timestep
        dfPercent = pd.DataFrame(0.0, index=np.arange(len(demand)), columns=columnNames)
        
                
        for t in range(len(demand)):
            totalGen = 0
            #getting out each generation for each tech at t timestep
            for techName in technologyNames:
                totalGen +=  dfRaw[techName][t]
            
            #then converting the same indices into percents
            for techName in technologyNames:
                dfPercent[techName][t] =  (dfRaw[techName][t])/totalGen

        #renaming index col for more clarity
        dfRaw.index.names = ['Timestep']
        dfPercent.index.names = ['Timestep']
        
        #saving to excel
        outputFileLocation = f"../modelOutputs/outputEnergyCommitmentCT{carbonTax}GT{geothermalLCOE}.xlsx"
        
        writer = pd.ExcelWriter(outputFileLocation, engine = 'xlsxwriter')
        
        dfRaw.to_excel(writer,sheet_name = 'rawGeneration')
        dfPercent.to_excel(writer,sheet_name = 'percentGeneration')       
         
         
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()
        print(f"Model results saved to: {outputFileLocation}")
        ''' 