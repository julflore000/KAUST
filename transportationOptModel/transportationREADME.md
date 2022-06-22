# Green Ammonia Production Optimization
This section of the repo details the work on the green ammonia downstream side

### Table of Parameters
**[General Parameters](#general-parameters)**<br>
**[Ships](#ships)**<br>
**[Ports](#ports)**<br>
**[Regions](#regions)**<br>
**[Other Helpful Info](#other-helpful-info)**<br>

### Table of Outputs
**[Output](#outputs)**<br>


### General Parameters
1. Ship speed
2. Discount rate
    * Interest rate for simulation
3. Lifetime of simulation
    * How long the ship and ports will be simulated
4. Network Connection
    * How each node is connected to each other (plan on having user input)
### Ships
6. CAPEX
    * CAPEX for each ship type
6. OPEX
    * OPEX for each ship type
7. Bulk size (capacity)
    * Capacity for each cargo ship
### Ports
8. CAPEX
    * CAPEX for each port
9. OPEX
    * OPEX for each port
### Regions
10. Demand
    * Demand for each region (positive means demand and negative means supply)

### Other Helpful Information
* To find correct port identification https://unece.org/trade/cefact/unlocode-code-list-country-and-territory and select LOCODE (don't include any spaces)
* Nautical mile distances from https://www.portworld.com/map
* GB shapefile from https://geoportal.statistics.gov.uk/datasets/nuts-level-1-january-2018-ultra-generalised-clipped-boundaries-in-the-united-kingdom/explore?filters=eyJudXRzMTE4Y2QiOlsiVUtMIiwiVUtLIiwiVUtKIiwiVUtJIiwiVUtIIiwiVUtHIiwiVUtGIiwiVUtFIiwiVUtEIiwiVUtDIiwiVUtNIl19&location=53.481863%2C-0.342861%2C6.00
* GB population of cities from https://public.opendatasoft.com/explore/dataset/geonames-all-cities-with-a-population-1000/export/?disjunctive.cou_name_en&sort=name&q=united+kingdom&location=6,54.83866,0.0769&basemap=jawg.light

### Table of Outputs
* Model Outputs
    * Hourly flow of transport network
        * How much fuel to have in storage
        * How much fuel to move on a certain ship at a certain time
        * How many ships you need to move the required demand