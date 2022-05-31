import streamlit as st
import pandas as pd
from sympy import Q
from productionOptModel.src.model import greenAmmoniaProduction 
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
from quoters import Quote
import altair as alt
from PIL import Image

#to run streamlit:
# streamlit run d:\Github\KAUST\websiteGUI.py


st.title('Green Ammonia Production Optimization')
print(os.getcwd())
#putting production image in
#image = Image.open(r'../../website/images/greenAmmoniaProduction.png')
#st.image(image, caption=None, width=None, use_column_width=None, clamp=False, channels="RGB", output_format="auto")

form = st.form(key='my_form')


#getting input data
inputDataset = {}
inputDataset["ammoniaDemand"] = form.number_input("Ammonia demand for plant (kg/day)",0,50000000,200000)

inputDataset["hsStoreEfficiency"] = form.number_input("Hydrogen storage efficiency (decimal)",0.0,1.0,.95)
inputDataset["hsDeployEfficiency"] = form.number_input("Hydrogen deploy efficiency (decimal)",0.0,1.0,.95)

inputDataset["bsStoreEfficiency"] = form.number_input("Battery storage efficiency (decimal)",0.0,1.0,.95)
inputDataset["bsDeployEfficiency"] = form.number_input("Battery deploy efficiency (decimal)",0.0,1.0,.95)

inputDataset["hbHydrogenEfficiency"] = form.number_input("Hydrogen Ammonia Plant Ratio efficiency (decimal)",0.0,1.0,.18)
inputDataset["hbNitrogenEfficiency"] = form.number_input("Nitrogen Ammonia Plant Ratio efficiency (decimal)",0.0,1.0,.82)

#capex inputs
inputDataset["capexWind"] = form.number_input("Wind CAPEX ($/MW)",0,10000000,1300000)
inputDataset["capexSolar"] = form.number_input("Solar CAPEX ($/MW)",0,10000000,1200000)

inputDataset["capexHS"] = form.number_input("Hydrogen Storage CAPEX ($/kg)",0,100000,500)

inputDataset["capexBS"] = form.number_input("Battery Storage CAPEX ($/MWh)",0,10000000,400000)

inputDataset["capexASU"] = form.number_input("ASU CAPEX ($/MW)",0,100000000,13182000)

inputDataset["capexHB"] = form.number_input("Ammonia plant CAPEX ($/MW)",0,100000000,6467000)

fixedOPEXPercentage = form.number_input("Fixed OPEX percentage of CAPEX (decimal percentage)",0.0,1.0,.05)




inputDataset["energyUseHS"] = form.number_input("Hydrogen Storage energy use/kg on hourly basis (kWh/kg H2)",0.0,10.0,.00005*1000)/1000

inputDataset["energyUseASU"] = form.number_input("Air Separation energy use/kg on hourly basis (kWh/kg N2)",0.0,10.0,.00011*1000)/1000

inputDataset["energyUseHB"] = form.number_input("Ammonia Plant energy use/kg on hourly basis (kWh/kg NH3)",0.0,10.0,.000532*1000)/1000



inputDataset["minCapacityASU"] = form.number_input("Minimum operating capacity for ASU plant (decimal percentage)",0.0,1.0,.2)

inputDataset["minCapacityHB"] = form.number_input("Minimum operating capacity for ammonia plant (decimal percentage)",0.0,1.0,.2)


inputDataset["plantLifetime"] = form.number_input("Total plant lifetime (years)",1,100,20)


inputDataset["r"] = form.number_input("Discount rate (Time value of money in decimal percentage)",0.0,1.0,.07)

#bool on whether submit button is pressed
submit_button = form.form_submit_button(label='Submit')





if submit_button:
    st.markdown("Please wait-Optimization Model running")
    st.markdown("Heres a quote while you wait")
    st.markdown(Quote.print())
    
    '''
    techNames = ["Wind","Solar","HS","BS","ASU","HB"]
    for name in techNames:
        inputDataset[f"fixedOpex{name}"] = fixedOPEXPercentage* inputDataset[f"capex{name}"]
    
    #setting current directory where model is
    os.chdir("d:/Github/KAUST/productionOptModel/src")
    
    
    #dont include the .dat ending or path location
    datFileName = "testRun"
    testMode = True


    #adding wind and solar generation capacity factors
    windCFDataset = pd.read_excel("../dataInputs/reData.xlsx",sheet_name='cfWind')
    solarCFDataset = pd.read_excel("../dataInputs/reData.xlsx",sheet_name='cfSolar')



    inputDataset["cfWind"] = np.array(windCFDataset["cfWind"])

    inputDataset["cfSolar"] = np.array(solarCFDataset["cfSolar"])


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
    
    singleValueData = pd.read_excel("../modelOutputs/testRun.xlsx",sheet_name="singleValueDvs")
    #now looking at LCOA costs breakdown
    costDataColNames = ["windCosts","solarCosts","eyCosts","hsCosts",
                                            "bsCosts","asuCosts","hbCosts"]
    altairPlotData = singleValueData[costDataColNames].T
    
    print(altairPlotData["0"])
    
    stackedBarChart = alt.Chart(singleValueData).mark_bar().encode(
        y=costDataColNames
    )
    st.altair_chart(stackedBarChart)
    #dfTechCosts.plot.bar(stacked=True,figsize=(10, 6))
    plt.title("LCOA Technology Breakdown")
    plt.xlabel("LCOA")
    plt.ylabel("$/kg")
    st.bar_chart(dfTechCosts,height=500,width=500,use_container_width=False)
    #st.pyplot(fig=plt)
    
    
    
    
    