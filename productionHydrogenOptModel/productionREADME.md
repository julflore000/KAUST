# Green Hydrogen Production Optimization
This section of the repo details the work on the green hydrogen production chain side and a walkthrough of all the various different parameter inputs (minimum of 25)


### Table of Parameters
**[General Parameters](#general-parameters)**<br>
**[Wind](#wind)**<br>
**[Solar](#solar)**<br>
**[Hydrogen Storage](#hydrogen-storage)**<br>
**[Electrical Storage](#electrical-storage)**<br>
**[Electrolyzers](#electrolyzers)**<br>
**[Other Helpful Info](#other-helpful-info)**<br>

### Table of Outputs
**[Output](#outputs)**<br>

### General Parameters
1. Hydrogen Demand
    * The required production quota for the hypothetical ammonia plant
2. Utilization Ratio
    * The percent of the time that the plant is operational (e.g. 95% means 5% of the production is not available due to O&M)
3. Discount Rate
    * Discount rate to account for TVOM
4. Plant lifetimes
    * Plant lifetime for all the components in the ammonia plant

### Wind
5. Capacity Factor Time Series
    * Time series data representing the capacity factor of a wind plant for a selected location
    * (takes into account transmission losses)
6. CAPEX
    * Capital expenditures to build capacity of wind plant
7. OPEX
    * Fixed operational expenditures for wind plant (taking as percent of CAPEX)
### Solar
8. Capacity Factor Time Series
    * Time series data representing the capacity factor of a solar plant for a selected location
9. CAPEX
    * Capital expenditures to build capacity of solar plant
10. OPEX
    * Fixed operational expenditures for solar plant (taking as percent of CAPEX)
### Hydrogen Storage
11. Storage Efficiency
    * Percent of hydrogen that is able to be fully stored in transfer (%)
12. Vaporization Rate
    * Percent of hydrogen that is lost per hour due to boil off
13. Deploy Efficiency
    * Percent of hydrogen that is able to be fully deployed in transfer (%)
14. Energy Use Hydrogen Storage
    * How much energy is required to store amount of hydrogen in tanks
15. CAPEX
    * CAPEX for hydrogen storage
16. OPEX
    * Fixed OPEX for hydrogen storage, taken as percent of CAPEX
* Assumptions
    * Storage can be used as either pressurized or cryogenic tanks-depending on parameter inputs
### Electrical Storage
17. Storage Efficiency
    * Percent of energy that is able to be fully stored in transfer (%)
18. Deploy Efficiency
    * Percent of energy that is able to be fully deployed in transfer (%)
19. CAPEX
    * CAPEX for electrical storage
20. OPEX
    * Fixed OPEX for electrical storage, taken as percent of CAPEX
* Assumptions
    * Able to hold a charge without losses (reasonable on short time scales which is when we see storage being deployed)

### Electrolyzers
21. CAPEX
    * CAPEX for electrolyzer model
22. Fixed OPEX
    * Fixed OPEX for electrolyzer model
23. Variable OPEX
    * Variable OPEX for electrolyzer model type (water costs)
24. Energy Use
    * How much energy is consumed in the production of 1 kg of H2
25. Stack Size
    * The size of a electrolyzer unit for model type
* Assumptions
    * The above 5 parameters are for only one model type and you can have as many electrolyzer models as desired (this was done to take into account scaling benefits of electrolyzer models)


### Other Helpful Info
* Data sources
    * See the input sheet for source citation

* Also see the doc folder for the formal mathematical formulation of the green ammonia production model

* Solar hourly data comes from: https://re.jrc.ec.europa.eu/pvg_tools/en/#HR exploring https://globalsolaratlas.info/map?c=24.557033,39.875112,5&s=27.376934,37.840085&m=site&pv=ground,180,30,1000

* Wind speed data comes from same source above and converted to 90 meters from 10 meters

* Wind speed then converted to power output from Vestas V90-3.0 Power profile from SAM library which has a Pout of 1800

Then converted to capacity factor

### Outputs
* Model Outputs
    * Sizing capacities
        * Wind capacity
        * Solar capacity
        * Battery Storage capacity
        * Hydrogen Storage capacity
        * Electrolyzer capacity
    * Hourly operations
        * How much hydrogen to store/deploy in tank
        * How much hydrogen to produce
        * How much energy to store/deploy in battery