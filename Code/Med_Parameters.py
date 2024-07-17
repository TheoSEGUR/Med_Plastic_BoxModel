import numpy as np
import json
import os
import math
from datetime import datetime
from openpyxl import load_workbook
import glob

#NOTE that in the manuscript large microplastics and small microplastics are termed LMP and SMP; in the model below they are still called MP and sMP
#saving k values within a class because it's convenient

###################
#Developpement tool
###################
#To find the PAR file more efficiently, put here a comprehensible title
title = "First try at V4" 
#To keep track of the changes, put in this section the changes made
Rq = ""

#How many MC_iterations? Each iteration will create a file. As a reminder, the random seed of 0 leads to
#no random reshuffling. So you can set MC_iterations to 1 to create a run based on mean parameter values only.
MC_iterations = 1000

#bellow indicate if you want to keep the history of the run (create a new file identified by a timestamp) (True)
#or write a new one after deleting the previous runs (False)
historic_mode = False

###################
#Below is a function for a pert distribution based on a distribution minimum, mean, and maximum. 
#note that the mode is calculated from the mean. 
#lamb is a form factor that controls how the mean is related to the mode 
#(it controls the shape of the distribution. 4 is standard, but you can play with this. )
def pert_mean(minval, meanval, maxval, *, lamb=4, size=1):
    
    modeval = (meanval*(lamb+2) - minval - maxval)/lamb
    
    r = maxval - minval
    alpha = 1 + lamb * (modeval - minval) / r
    beta = 1 + lamb * (maxval - modeval) / r
    return minval + np.random.beta(alpha, beta, size=size) * r

def lognormal(inf, sup, n_sigma=2, size=1):
    Mean = (1/n_sigma)*math.log(sup*inf)
    Sigma = (1/(2*n_sigma))*math.log(sup/inf)
    
    return np.random.lognormal(mean=Mean, sigma=Sigma, size=size)

##################
class boxmodel_parameters: 
    def __init__(self,seed) :
        self.seed = seed
    
    def __shuffle__(self):
        np.random.seed(self.seed) #Set the random seed for this shuffeling iteration

        ### Forcing randomization -------------------------------------------------
        self.F_waste_random = 1 if self.seed==0 else np.random.normal(1,0.05)
        self.f_rec_random   = 1 if self.seed==0 else np.random.normal(1,0.05)
        self.f_inc_random   = 1 if self.seed==0 else np.random.normal(1,0.05)
        self.f_mism_random  = 1 if self.seed==0 else np.random.normal(1,0.05)
        
        ### Comp_0: P production --------------------------------------------------
        self.f_LMP = 0.14 if self.seed==0 else pert_mean(0.07, 0.14, 0.21, size=1, lamb = 4)[0]
        self.LB19 = 0.03 if self.seed==0 else pert_mean(0.015, 0.03, 0.045, size=1, lamb = 4)[0]  # Plastics degradation rate in 'per year' units; Originally from Lebreton et al. 2019, NCOMMS, but supported by many studies. Below this rate is applied to P to LMP degradation adn LMP to SMP degradation in all environments
        self.f_ssed = 0.179 # proportion of continetal shelf in the Med sea (from Poulos et al., 2020 ESR)
        #Below, proportion of remote soil for eachh region, calculated using FAO Global Land Cover Database
        self.f_soil_R1 = 0.57
        self.f_soil_R2 = 0.66
        self.f_soil_R3 = 0.80
        
        #Below, proportion of mismanaged plastic waste that is open burned, from OECD 2022 Global plastic outlook (Table A.A.23 p245)
        self.f_burn_R1 = 0.31
        self.f_burn_R2 = 0.31
        self.f_burn_R3 = 0.31    
        
        ### Comp_1: mismanaged terrestrial plastic pool --------------------------------------------------     
        ##  River fluxes
        self.F_P_terr_to_surf   = 0.043 if self.seed==0 else pert_mean(0.01, 0.043, 0.2, lamb=4)[0] #0.06
        self.F_LMP_terr_to_surf = 0.65 if self.seed==0 else pert_mean(0.007, 0.65, 10, lamb=4)[0]   #0.7
        self.F_sMP_terr_to_surf = 0.025 if self.seed==0 else pert_mean(0.01, 0.025, 0.05, lamb=4)[0]
        
        ## Fraction of 
        self.f_runoff_R1 = 0.879 #0.1069 #R1 account in average 11% of the total river flux in 2015, according to Lebreton17, Nyberg23 and Meijer21
        self.f_runoff_R2 = 0.120 #0.7461 #R2 account in average 75% of the total river flux in 2015, according to Lebreton17, Nyberg23 and Meijer21
        self.f_runoff_R3 = 0.001 #0.1470 #R3 account in average 15% of the total river flux in 2015, according to Lebreton17, Nyberg23 and Meijer21
        
        # Set after a single model itteration:
        self.M_R1_P_mism   = 14.7 
        self.M_R1_LMP_mism = 7.8
        self.M_R1_sMP_mism = 5.1
        
        self.M_R2_P_mism   = 16.3
        self.M_R2_LMP_mism = 8.4
        self.M_R2_sMP_mism = 3.4
        
        self.M_R3_P_mism   = 9.1
        self.M_R3_LMP_mism = 4.7
        self.M_R3_sMP_mism = 1.7
        
        #   Region1
        self.k_R1_P_terr_to_surf   = self.F_P_terr_to_surf   * self.f_runoff_R1 / self.M_R1_P_mism
        self.k_R1_LMP_terr_to_surf = self.F_LMP_terr_to_surf * self.f_runoff_R1 / self.M_R1_LMP_mism
        self.k_R1_sMP_terr_to_surf = self.F_sMP_terr_to_surf * self.f_runoff_R1 / self.M_R1_sMP_mism
        #   Region2 
        self.k_R2_P_terr_to_surf   = self.F_P_terr_to_surf   * self.f_runoff_R2 / self.M_R2_P_mism
        self.k_R2_LMP_terr_to_surf = self.F_LMP_terr_to_surf * self.f_runoff_R2 / self.M_R2_LMP_mism
        self.k_R2_sMP_terr_to_surf = self.F_sMP_terr_to_surf * self.f_runoff_R2 / self.M_R2_sMP_mism
        #   Region3
        self.k_R3_P_terr_to_surf   = self.F_P_terr_to_surf   * self.f_runoff_R3 / self.M_R3_P_mism
        self.k_R3_LMP_terr_to_surf = self.F_LMP_terr_to_surf * self.f_runoff_R3 / self.M_R3_LMP_mism
        self.k_R3_sMP_terr_to_surf = self.F_sMP_terr_to_surf * self.f_runoff_R3 / self.M_R3_sMP_mism

        ##  sMP emissions to atm
        #   Regions
        self.k_R1_sMP_terr_to_atmo = 0.0024 if self.seed==0 else pert_mean(0.0007, 0.0024, 0.0063)[0] #0.0018 # from Sonke et al., 2024
        self.k_R2_sMP_terr_to_atmo = self.k_R1_sMP_terr_to_atmo #same behavious set to all regions
        self.k_R3_sMP_terr_to_atmo = self.k_R1_sMP_terr_to_atmo #same behavious set to all regions
        
        ##  Fragmentation
        self.k_mism_P_to_LMP   = self.LB19
        self.k_mism_LMP_to_sMP = self.LB19
        
        
        
        ### Comp_2: Atmosphere ----------------------------------------------------
        ##  Deposition to mismanaged terrestrial plastic pool AND remote soils
        #   Regions
        self.k_R1_sMP_atmo_to_terr = 58 if self.seed==0 else pert_mean(19, 58, 114)[0] #50 # from Sonke et al., 2024
        self.k_R2_sMP_atmo_to_terr = self.k_R1_sMP_atmo_to_terr #same behavious set to all regions
        self.k_R3_sMP_atmo_to_terr = self.k_R1_sMP_atmo_to_terr #same behavious set to all regions
        
        ##  Deposition to sea surface
        self.k_sMP_atmo_to_surf = 40 if self.seed==0 else pert_mean(10,40,178)[0] #34 # from Sonke et al., 2024
        
        
        
        ### Comp_3: Natural soil --------------------------------------------------
        
        
        
        ### Comp_4: Sea surface ---------------------------------------------------
        ##  Emission to the atmosphere
        self.k_sMP_surf_to_atmo = 1.3 if self.seed==0 else pert_mean(0.2,1.3,6.8)[0] #0.95 # from Sonke et al., 2024
        
        ##  Beaching
        self.k_P_surf_to_sand   = 0.23 #if self.seed==0 else pert_mean(0.01,0.2,0.5)[0]#
        self.k_LMP_surf_to_sand = 0 # 0.03     
        self.k_sMP_surf_to_sand = 0 # from Sonke et al., 2024
        
        ##  Sinking to shelf sediment
        self.k_P_surf_to_ssed   = 200 #250
        self.k_LMP_surf_to_ssed = 23667 * pert_mean(0.01, 1, 2)[0] * self.F_LMP_terr_to_surf #7080 #if self.seed==0 else pert_mean(6000,7080,8000)[0] #250
        self.k_sMP_surf_to_ssed = 117 if self.seed==0 else pert_mean(52,117,191)[0] #120 # from Sonke et al., 2024
        
        ##  Sinking to water column
        self.k_P_surf_to_wcol   = 0   #not included in model because we assume open ocean P to be buoyant, but approx 1367 y-1, based on Long et al. 2015, ES&T: sMP sinking rate of 375 m/d=136700 m/y and a mixed layer depth of 100m: 136700/100=1367 y-1
        self.k_LMP_surf_to_wcol = 250 #
        self.k_sMP_surf_to_wcol = 15 if self.seed==0 else pert_mean(9,15,23)[0] #15 # from Sonke et al., 2024
        
        ##  Fragmentation
        self.k_surf_P_to_LMP   = self.LB19 #*0
        self.k_surf_LMP_to_sMP = self.LB19 #*0
        
        
        
        ### Comp_5: Beach ---------------------------------------------------------
        ## Fragmentation
        self.k_sand_P_to_LMP   = self.LB19 #*0
        self.k_sand_LMP_to_sMP = self.LB19 #*0
        
        
        
        ### Comp_6: Shelf sediment ------------------------------------------------
        
        
        
        ### Comp_7: Water column --------------------------------------------------
        ##  Sink to deep sediment
        self.k_LMP_wcol_to_dsed = 0.001 #
        self.k_sMP_wcol_to_dsed = 0.00026 if self.seed==0 else pert_mean(0.00015,0.00026,0.00040)[0] #0.00026 # from Sonke et al., 2024
       
        ##  Fragmentation
        self.k_wcol_LMP_to_sMP = 0 # self.LB19
        
    
        
        ### Comp_8: Deep sediment -------------------------------------------------

now = datetime.now()
current_time = now.strftime("%Y%m%d_%H%M")

if historic_mode == True:
    ###now saving this as a json. Creating the timestamp
    print("Creating new file...")
    print(f"\n{current_time}")

    #where to save the parameter *.json files
    outdir = "./Input/MC_params_" + current_time + "/" #create a sub folder
    if not os.path.exists(outdir):  #if the output file does not exist
        os.mkdir(outdir)            #create a new directory
else :
    outdir = "./Input_temp/"
    if not os.path.exists(outdir):  #if the output file does not exist
        os.mkdir(outdir)            #create a new directory
    if len(os.listdir(outdir))>0:   #if this directory is already used by a previous run
        print(f"Removing previous PARS files in {outdir}...")
        for f in glob.glob(outdir+"*"): #for all file tpe in the directory
            os.remove(f)                #remove them
        
        
print(f"\nSaving {MC_iterations} new .json files to :")
print(f"{outdir}")

#Generate the .json file(s)
for myseed in range(0,MC_iterations):
    fname = "Med_PARS_S" + str(myseed).zfill(len(str(MC_iterations))) + ".json"

    print(end = '\x1b[2K')
    avance = str(round(100*(myseed)/MC_iterations))
    print(avance + "% completed...", end = '\r')
    
    #create a parameters object and do the MC random reshuffling.
    parameters_obj = boxmodel_parameters(myseed)
    parameters_obj.__shuffle__()

    #get the variables from boxmodel_parameters class as dictionary
    pardict =  {k:float('{:.2e}'.format(v)) for k, v in parameters_obj.__dict__.items() if not (k.startswith('__')
                                                             and k.endswith('__') and not (k.startswith("generate")))}

    #saving this as json.
    with open(outdir + fname, "w") as write_file:
        json.dump(pardict, write_file, indent = 4)
        
print(f'\n{len(os.listdir(outdir))} new input files successfully created!')        
print("\nDone.")