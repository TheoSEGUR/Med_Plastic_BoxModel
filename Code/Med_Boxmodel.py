import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from Med_Forcings import boxmodel_forcings #this is custom. Make sure to have the script boxmodel_forcings.py in the same folder
from timeit import default_timer as timer
from datetime import datetime
from openpyxl import load_workbook
import json
import os
import glob
import multiprocessing
import sys
from warnings import simplefilter
from tqdm import tqdm 
import winsound
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

##############################
#Microplastics box model. Mar-Aug 2023. Authors: Théo SEGUR, Jeroen SONKE, Alkuin KOENIG (jeroen.sonke@get.omp.eu and Alkuin.Koenig@gmx.de)
##############################
#Instructions:
#This is the main script (boxmodel.py).To be able to run this, you need to have in the same folder
#the script "boxmodel_forcings_V4.py", where forcings are defined.
#you also need a *.json input file with mass transfer coefficients, k (for example created with the script "boxmodel_parameters_V4.py")
#The variable "input_relpath" below should point to the location of this input *.json
#Note that the output file will be named automatically. It will be saved at the path "output_relpath" which should be given below.

#creating a timestamp so that we can keep track of the outputs
now = datetime.now()
current_time = now.strftime("%Y%m%d_%H%M")

###############################
#User input.
###############################
#Logbook info
#Set an explicite title to your run
title = "First try at MC"
#Add any remarques that may help to give context to this run
Rq = "Try 0"

##############################
#bellow indicate if you want to keep the historic of the run (create a new file iddentified by a timestemp) (True)
#or write a new one after deleting the previous runs (False)
historic_mode = False

#below indicate the relative path to the input file. 
input_relpath = "./Input/MC_params_"+"20231129_1152"+"/"
#below indicate the relative path to where you want the output file to be saved
output_relpath = "./Output/MC_OUT_" + current_time + "/"


### below indicate the time span for which the model should be run (t1 to t2, given in years)
t_span = np.array([1950,2100])
### below indicate how many output lines you want to have per year (for example 10 --> output every 0.1 years).
lines_per_year = 1

### below indiacte wich method will be used to solve the ODE system
#solv_method = "RK45" # default method (explicite), used for non-stiff ODE systems
solv_method = "Radau" # alternative method (implicite), used for stiff ODE systems

### set below to True if you want the used parameters (rate constants) repeated as metadata in the output file (recommended). Set to False otherwise. 
extended_meta = True

### set below to True if you want the result to contain additionnal control values (fraction curves). Set to False otherwise. 
extended_control = True

### below indicate whitch atmosphere setteings you want
scenario_atm = ("Local",)

### below indicate the future plastics release scenario (see examples further below). 
#
scenario_release = ("BAU",)
#scenario_release = ("fullstop", 2030)
#scenario_release = ("freeze", 2030)
#scenario_release = ("OECD_RA", np.array([2030,2060]))
#scenario_release = ("OECD_GA", np.array([2030,2060]))

### below indicate the cleanup scenario (cleanup refers to removing P, MP or sMP from the discarded plastics pool)
#
scenario_cleanup = ("no_cleanup",)
#scenario_cleanup = ("cleanup_mismanaged_fixedfrac", np.array([2025,2060]), np.array([0.05,0.05,0.05,0.0,0.0,0.0,0.0,0.0,0.0]))
#scenario_cleanup = ("cleanup_mismanaged_linear_increment", np.array([2025,2060]), np.array([0.25,0.25,0.25,0.0,0.0,0.0,0.0,0.0,0.0]))

########
#EXAMPLES FOR RELEASE AND CLEANUP SCENARIOS BELOW
########
#scenario_release = ("BAU",) #business as usual
#scenario_release = ("SCS",) #system change scenario from Lau et al., 2020
#scenario_release = ("fullstop",2025) #stop all virgin plastics production and all plastics waste on 01.01.2025; this scenario illustrates ecosystem recovery over hundreds to thousands of years

#scenario_release = ("OECD_RA", np.array([YEAR START,YEAR END]), np.array([R1_P_reduc, R1_MP_reduc, R2_P_reduc, R2_MP_reduc, R3_P_reduc, R3_MP_reduc]))
#scenario_release = ("OECD_GA", np.array([YEAR START,YEAR END]), np.array([R1_P_reduc, R1_MP_reduc, R2_P_reduc, R2_MP_reduc, R3_P_reduc, R3_MP_reduc]))

#scenario_cleanup = ("no_cleanup",) #No cleanup of mismanaged plastic waste
#scenario_cleanup = ("cleanup_mismanaged_fixedfrac", np.array([YEAR START,YEAR END])), np.array([P_R1,P_R2,P_R3,LMP_R1,LMP_R2,LMP_R3,sMP_R1,sMP_R2,sMP_R3])) #Clean 1% of mism pool each year from 2030 to 2060
#scenario_cleanup = ("cleanup_mismanaged_linear_increment", np.array([YEAR START,YEAR END]), np.array([P_R1,P_R2,P_R3,LMP_R1,LMP_R2,LMP_R3,sMP_R1,sMP_R2,sMP_R3])) #Objective to clean 10% of mism pool each year by 2060 (starting with 0% in 2030 and linearly increasing)
#######

#######
if historic_mode==True:
    if not os.path.exists(output_relpath):  #if the output file does not exist
        os.mkdir(output_relpath)            #create a new directory
if historic_mode==False:
    input_relpath = "./Input_temp/"
    output_relpath = "./Output_temp/"
    if not os.path.exists(output_relpath):
        os.mkdir(output_relpath)
    if len(os.listdir(output_relpath))>0:   #if this directory is already used by a previous run
        print(f"Removing previous PARS files in {output_relpath}...")
        for f in glob.glob(output_relpath+"*"): #for all file tpe in the directory
            os.remove(f)                #remove them



###############################
#Below the definition of the model, alongside all ordinary differential equations
###############################
def Med_boxmodel(t, y, PARS, FRCS):
    
    ### Comp_0: Recycled ------------------------------------------------------
    M_R1_Ptot_rec = y[0]
    M_R2_Ptot_rec = y[1]
    M_R3_Ptot_rec = y[2]
    
    ### Comp_1: Incinerated ---------------------------------------------------
    M_R1_Ptot_inc = y[3]
    M_R2_Ptot_inc = y[4]
    M_R3_Ptot_inc = y[5]
    
    ### Comp_2: Landfilled (sanitary) -----------------------------------------
    M_R1_Ptot_landf = y[6]
    M_R2_Ptot_landf = y[7]
    M_R3_Ptot_landf = y[8]
    
    ### Comp_3: Mismanaged ----------------------------------------------------
    ##  P
    M_R1_P_mism = y[9]  # Region1
    M_R2_P_mism = y[10] # Region2
    M_R3_P_mism = y[11] # Region3
    ##  LMP
    M_R1_LMP_mism = y[12] # Region1
    M_R2_LMP_mism = y[13] # Region2
    M_R3_LMP_mism = y[14] # Region3
    ##  sMP
    M_R1_sMP_mism = y[15] # Region1
    M_R2_sMP_mism = y[16] # Region2
    M_R3_sMP_mism = y[17] # Region3
    
    ### Comp_4: Atmosphere ----------------------------------------------------
    M_sMP_atmo = y[18]
    
    ### Comp_5: Natural soil --------------------------------------------------
    ##  sMP
    M_R1_sMP_soil = y[19] # Region1
    M_R2_sMP_soil = y[20] # Region2
    M_R3_sMP_soil = y[21] # Region3
    
    ### Comp_6: Sea surface ---------------------------------------------------
    M_P_surf   = y[22]
    M_LMP_surf = y[23]
    M_sMP_surf = y[24]
    
    
    ### Comp_7: Beach ---------------------------------------------------------
    M_P_sand   = y[25]
    M_LMP_sand = y[26]
    M_sMP_sand = y[27]
    
    ### Comp_8: Shelf sediment ------------------------------------------------
    M_P_ssed   = y[28]
    M_LMP_ssed = y[29]
    M_sMP_ssed = y[30]
    
    ### Comp_9: Water column --------------------------------------------------
    M_LMP_wcol = y[31]
    M_sMP_wcol = y[32]
    
    ### Comp_10: Deep sediment ------------------------------------------------
    M_LMP_dsed = y[33]
    M_sMP_dsed = y[34]
    
    ### Comp_11: Cleaned ------------------------------------------------------
    M_P_clean   = y[35]
    M_LMP_clean = y[36]
    M_sMP_clean = y[37]
    
    ### Comp 12: Open burning
    M_R1_P_burn = y[38]
    M_R2_P_burn = y[39]
    M_R3_P_burn = y[40]
    
    M_P_waste = y[41]


    ####=======================================================================
    # First we get the forcings
    ### REGIONAL PLASTIC WASTE PRODUCTION
    #Regional waste curves    
    R_F_waste = FRCS.get_R_F_waste(t) * PARS["F_waste_random"]
    R1_F_waste = R_F_waste[0] #Region 1
    R2_F_waste = R_F_waste[1] #Region 2
    R3_F_waste = R_F_waste[2] #Region 3
    
    ### FRACTION OF WASTE
    #Regional recycled fraction
    R_f_rec = FRCS.get_R_f_rec(t) * PARS["f_rec_random"]
    R1_f_rec = R_f_rec[0] #Region 1
    R2_f_rec = R_f_rec[1] #Region 2
    R3_f_rec = R_f_rec[2] #Region 3
    
    #Regional incinerated fraction
    R_f_inc= FRCS.get_R_f_inc(t) * PARS["f_inc_random"]
    R1_f_inc = R_f_inc[0] #Region 1
    R2_f_inc = R_f_inc[1] #Region 2
    R3_f_inc = R_f_inc[2] #Region 3
    
    #Regional mismanaged fraction
    R_f_mism = FRCS.get_R_f_mism(t) * PARS["f_mism_random"]
    R1_f_mism = R_f_mism[0] #Region 1
    R2_f_mism = R_f_mism[1] #Region 2
    R3_f_mism = R_f_mism[2] #Region 3
    
    #Regional sanitary landfiled fraction
    R1_f_landf = 1 - (R1_f_rec + R1_f_inc + R1_f_mism)
    R2_f_landf = 1 - (R2_f_rec + R2_f_inc + R2_f_mism)
    R3_f_landf = 1 - (R3_f_rec + R3_f_inc + R3_f_mism)
   
    #CleanUp data
    CleanUp = FRCS.get_f_cleanUp(t)
    f_P_cleanUp   = CleanUp[0]
    f_LMP_cleanUp = CleanUp[1]
    f_sMP_cleanUp = CleanUp[2]
    
    
    ####=======================================================================
    # Here are the differential equation that define the model
    # dM/dt = Sum(F_in)-Sum(F_out) with F=k*M (the k values are read from the input .json file named PARS here)
    
    ### Comp_0: Recycled ------------------------------------------------------
    dM_R1_Ptot_rec_dt = R1_F_waste * R1_f_rec 
    dM_R2_Ptot_rec_dt = R2_F_waste * R2_f_rec
    dM_R3_Ptot_rec_dt = R3_F_waste * R3_f_rec
    
    ### Comp_1: Incinerated ---------------------------------------------------
    dM_R1_Ptot_inc_dt = R1_F_waste * R1_f_inc
    dM_R2_Ptot_inc_dt = R2_F_waste * R2_f_inc
    dM_R3_Ptot_inc_dt = R3_F_waste * R3_f_inc
    
    ### Comp_2: Landfilled (sanitary) -----------------------------------------
    dM_R1_Ptot_landf_dt = R1_F_waste * R1_f_landf
    dM_R2_Ptot_landf_dt = R2_F_waste * R2_f_landf
    dM_R3_Ptot_landf_dt = R3_F_waste * R3_f_landf
    
    ### Comp_1: Mismanaged ----------------------------------------------------
    ##  River fluxes
    #   P
    F_R1_P_mism_to_surf = PARS["k_R1_P_terr_to_surf"] * M_R1_P_mism
    F_R2_P_mism_to_surf = PARS["k_R2_P_terr_to_surf"] * M_R2_P_mism
    F_R3_P_mism_to_surf = PARS["k_R3_P_terr_to_surf"] * M_R3_P_mism
    F_P_mism_to_surf = F_R1_P_mism_to_surf + F_R2_P_mism_to_surf + F_R3_P_mism_to_surf
    #   LMP
    F_R1_LMP_mism_to_surf = PARS["k_R1_LMP_terr_to_surf"] * M_R1_LMP_mism
    F_R2_LMP_mism_to_surf = PARS["k_R2_LMP_terr_to_surf"] * M_R2_LMP_mism
    F_R3_LMP_mism_to_surf = PARS["k_R3_LMP_terr_to_surf"] * M_R3_LMP_mism
    F_LMP_mism_to_surf = F_R1_LMP_mism_to_surf + F_R2_LMP_mism_to_surf + F_R3_LMP_mism_to_surf
    #   sMP
    F_R1_sMP_mism_to_surf = PARS["k_R1_sMP_terr_to_surf"] * M_R1_sMP_mism
    F_R2_sMP_mism_to_surf = PARS["k_R2_sMP_terr_to_surf"] * M_R2_sMP_mism
    F_R3_sMP_mism_to_surf = PARS["k_R3_sMP_terr_to_surf"] * M_R3_sMP_mism 
    F_sMP_mism_to_surf = F_R1_sMP_mism_to_surf + F_R2_sMP_mism_to_surf + F_R3_sMP_mism_to_surf
    ##  Regional equations
    #   P
    dM_R1_P_mism_dt = R1_F_waste * R1_f_mism * (1-PARS["f_LMP"]) * (1 - PARS["f_burn_R1"]) - F_R1_P_mism_to_surf - PARS["k_mism_P_to_LMP"] * M_R1_P_mism - f_P_cleanUp[0] * M_R1_P_mism
    dM_R2_P_mism_dt = R2_F_waste * R2_f_mism * (1-PARS["f_LMP"]) * (1 - PARS["f_burn_R2"]) - F_R2_P_mism_to_surf - PARS["k_mism_P_to_LMP"] * M_R2_P_mism - f_P_cleanUp[1] * M_R2_P_mism
    dM_R3_P_mism_dt = R3_F_waste * R3_f_mism * (1-PARS["f_LMP"]) * (1 - PARS["f_burn_R3"]) - F_R3_P_mism_to_surf - PARS["k_mism_P_to_LMP"] * M_R3_P_mism - f_P_cleanUp[2] * M_R3_P_mism
    #   LMP
    dM_R1_LMP_mism_dt = R1_F_waste * R1_f_mism * PARS["f_LMP"] + PARS["k_mism_P_to_LMP"] * M_R1_P_mism - F_R1_LMP_mism_to_surf - PARS["k_mism_LMP_to_sMP"] * M_R1_LMP_mism - f_LMP_cleanUp[0] * M_R1_LMP_mism
    dM_R2_LMP_mism_dt = R2_F_waste * R2_f_mism * PARS["f_LMP"] + PARS["k_mism_P_to_LMP"] * M_R2_P_mism - F_R2_LMP_mism_to_surf - PARS["k_mism_LMP_to_sMP"] * M_R2_LMP_mism - f_LMP_cleanUp[1] * M_R2_LMP_mism
    dM_R3_LMP_mism_dt = R3_F_waste * R3_f_mism * PARS["f_LMP"] + PARS["k_mism_P_to_LMP"] * M_R3_P_mism - F_R3_LMP_mism_to_surf - PARS["k_mism_LMP_to_sMP"] * M_R3_LMP_mism - f_LMP_cleanUp[2] * M_R3_LMP_mism
    #   sMP
    dM_R1_sMP_mism_dt = PARS["k_mism_LMP_to_sMP"] * M_R1_LMP_mism + PARS["k_R1_sMP_atmo_to_terr"] * (1- PARS["f_soil_R1"]) * M_sMP_atmo - F_R1_sMP_mism_to_surf - PARS["k_R1_sMP_terr_to_atmo"] * (1- PARS["f_soil_R1"]) * M_R1_sMP_mism - f_sMP_cleanUp[0] * M_R1_sMP_mism
    dM_R2_sMP_mism_dt = PARS["k_mism_LMP_to_sMP"] * M_R2_LMP_mism + PARS["k_R2_sMP_atmo_to_terr"] * (1- PARS["f_soil_R2"]) * M_sMP_atmo - F_R2_sMP_mism_to_surf - PARS["k_R2_sMP_terr_to_atmo"] * (1- PARS["f_soil_R2"]) * M_R2_sMP_mism - f_sMP_cleanUp[1] * M_R2_sMP_mism
    dM_R3_sMP_mism_dt = PARS["k_mism_LMP_to_sMP"] * M_R3_LMP_mism + PARS["k_R3_sMP_atmo_to_terr"] * (1- PARS["f_soil_R3"]) * M_sMP_atmo - F_R3_sMP_mism_to_surf - PARS["k_R3_sMP_terr_to_atmo"] * (1- PARS["f_soil_R3"]) * M_R3_sMP_mism - f_sMP_cleanUp[2] * M_R3_sMP_mism
    
    
    
    ### Comp_2: Atmosphere ----------------------------------------------------
    F_sMP_terr_to_atmo = PARS["k_R1_sMP_terr_to_atmo"] * (1- PARS["f_soil_R1"]) * M_R1_sMP_mism + PARS["k_R2_sMP_terr_to_atmo"] * (1- PARS["f_soil_R2"]) * M_R2_sMP_mism + PARS["k_R3_sMP_terr_to_atmo"] * (1- PARS["f_soil_R3"]) * M_R3_sMP_mism + PARS["k_R1_sMP_terr_to_atmo"] * PARS["f_soil_R1"] * M_R1_sMP_soil + PARS["k_R2_sMP_terr_to_atmo"] * PARS["f_soil_R2"] * M_R2_sMP_soil + PARS["k_R3_sMP_terr_to_atmo"] * PARS["f_soil_R3"] * M_R3_sMP_soil
    F_sMP_atmo_to_terr = PARS["k_R1_sMP_atmo_to_terr"] * (1- PARS["f_soil_R1"]) * M_sMP_atmo    + PARS["k_R2_sMP_atmo_to_terr"] * (1- PARS["f_soil_R2"]) * M_sMP_atmo    + PARS["k_R3_sMP_atmo_to_terr"] * (1- PARS["f_soil_R3"]) * M_sMP_atmo    + PARS["k_R1_sMP_atmo_to_terr"] * PARS["f_soil_R1"] * M_sMP_atmo    + PARS["k_R2_sMP_atmo_to_terr"] * PARS["f_soil_R2"] * M_sMP_atmo    + PARS["k_R3_sMP_atmo_to_terr"] * PARS["f_soil_R3"] * M_sMP_atmo
    dM_sMP_atmo_dt = F_sMP_terr_to_atmo + PARS["k_sMP_surf_to_atmo"] * M_sMP_surf - F_sMP_atmo_to_terr - PARS["k_sMP_atmo_to_surf"] * M_sMP_atmo
        
    
    
    ### Comp_3: Natural soil --------------------------------------------------
    ##  River fluxes
    F_R1_sMP_soil_to_surf = PARS["k_R1_sMP_terr_to_surf"] * M_R1_sMP_soil 
    F_R2_sMP_soil_to_surf = PARS["k_R2_sMP_terr_to_surf"] * M_R2_sMP_soil 
    F_R3_sMP_soil_to_surf = PARS["k_R3_sMP_terr_to_surf"] * M_R3_sMP_soil 
    F_sMP_soil_to_surf = F_R1_sMP_soil_to_surf + F_R2_sMP_soil_to_surf + F_R3_sMP_soil_to_surf
    ## Regional equations
    dM_R1_sMP_soil_dt = PARS["k_R1_sMP_atmo_to_terr"] * PARS["f_soil_R1"] * M_sMP_atmo - PARS["k_R1_sMP_terr_to_atmo"] * PARS["f_soil_R1"] * M_R1_sMP_soil - F_R1_sMP_soil_to_surf
    dM_R2_sMP_soil_dt = PARS["k_R2_sMP_atmo_to_terr"] * PARS["f_soil_R2"] * M_sMP_atmo - PARS["k_R2_sMP_terr_to_atmo"] * PARS["f_soil_R2"] * M_R2_sMP_soil - F_R2_sMP_soil_to_surf
    dM_R3_sMP_soil_dt = PARS["k_R3_sMP_atmo_to_terr"] * PARS["f_soil_R3"] * M_sMP_atmo - PARS["k_R3_sMP_terr_to_atmo"] * PARS["f_soil_R3"] * M_R3_sMP_soil - F_R3_sMP_soil_to_surf
    
    
    
    ### Comp_4: Sea surface ---------------------------------------------------
    dM_P_surf_dt   = F_P_mism_to_surf   - PARS["k_P_surf_to_sand"]   * M_P_surf   - PARS["k_P_surf_to_ssed"]   * M_P_surf   * PARS["f_ssed"] - PARS["k_P_surf_to_wcol"]   * M_P_surf   * (1-PARS["f_ssed"]) - PARS["k_surf_P_to_LMP"]   * M_P_surf
    dM_LMP_surf_dt = F_LMP_mism_to_surf - PARS["k_LMP_surf_to_sand"] * M_LMP_surf - PARS["k_LMP_surf_to_ssed"] * M_LMP_surf * PARS["f_ssed"] - PARS["k_LMP_surf_to_wcol"] * M_LMP_surf * (1-PARS["f_ssed"]) - PARS["k_surf_LMP_to_sMP"] * M_LMP_surf + PARS["k_surf_P_to_LMP"] * M_P_surf
    dM_sMP_surf_dt = F_sMP_mism_to_surf + F_sMP_soil_to_surf + PARS["k_sMP_atmo_to_surf"] * M_sMP_atmo + PARS["k_surf_LMP_to_sMP"] * M_LMP_surf - PARS["k_sMP_surf_to_sand"] * M_sMP_surf - PARS["k_sMP_surf_to_ssed"] * M_sMP_surf * PARS["f_ssed"] - PARS["k_sMP_surf_to_wcol"] * M_sMP_surf *(1-PARS["f_ssed"]) - PARS["k_sMP_surf_to_atmo"] * M_sMP_surf
    
    ### Comp_5: Beach ---------------------------------------------------------
    dM_P_sand_dt   = PARS["k_P_surf_to_sand"]   * M_P_surf   - PARS["k_sand_P_to_LMP"] * M_P_sand
    dM_LMP_sand_dt = PARS["k_LMP_surf_to_sand"] * M_LMP_surf + PARS["k_sand_P_to_LMP"] * M_P_sand - PARS["k_sand_LMP_to_sMP"] * M_LMP_sand
    dM_sMP_sand_dt = PARS["k_sMP_surf_to_sand"] * M_sMP_surf + PARS["k_sand_LMP_to_sMP"] * M_LMP_sand
    
    ### Comp_6: Shelf sediment ------------------------------------------------
    dM_P_ssed   = PARS["k_P_surf_to_ssed"]   * M_P_surf   * PARS["f_ssed"]
    dM_LMP_ssed = PARS["k_LMP_surf_to_ssed"] * M_LMP_surf * PARS["f_ssed"]
    dM_sMP_ssed = PARS["k_sMP_surf_to_ssed"] * M_sMP_surf * PARS["f_ssed"]
    
    ### Comp_7: Water column --------------------------------------------------
    dM_LMP_wcol = PARS["k_LMP_surf_to_wcol"] * M_LMP_surf * (1-PARS["f_ssed"]) - PARS["k_LMP_wcol_to_dsed"] * M_LMP_wcol - PARS["k_wcol_LMP_to_sMP"] * M_LMP_wcol
    dM_sMP_wcol = PARS["k_sMP_surf_to_wcol"] * M_sMP_surf * (1-PARS["f_ssed"]) - PARS["k_sMP_wcol_to_dsed"] * M_sMP_wcol + PARS["k_wcol_LMP_to_sMP"] * M_LMP_wcol
    
    ### Comp_8: Deep sediment -------------------------------------------------
    dM_LMP_dsed = PARS["k_LMP_wcol_to_dsed"] * M_LMP_wcol
    dM_sMP_dsed = PARS["k_sMP_wcol_to_dsed"] * M_sMP_wcol
    
    ### Comp_9: Cleaned -------------------------------------------------------
    dM_P_clean_dt   = f_P_cleanUp[0]   * M_R1_P_mism   + f_P_cleanUp[1]   * M_R2_P_mism   + f_P_cleanUp[2]   * M_R3_P_mism
    dM_LMP_clean_dt = f_LMP_cleanUp[0] * M_R1_LMP_mism + f_LMP_cleanUp[1] * M_R2_LMP_mism + f_LMP_cleanUp[2] * M_R3_LMP_mism
    dM_sMP_clean_dt = f_sMP_cleanUp[0] * M_R1_sMP_mism + f_sMP_cleanUp[1] * M_R2_sMP_mism + f_sMP_cleanUp[2] * M_R3_sMP_mism
    
    ### Comp 10: Open burned
    dM_R1_P_burn_dt = R1_F_waste * R1_f_mism * (1-PARS["f_LMP"]) * PARS["f_burn_R1"]
    dM_R2_P_burn_dt = R2_F_waste * R2_f_mism * (1-PARS["f_LMP"]) * PARS["f_burn_R2"]
    dM_R3_P_burn_dt = R3_F_waste * R3_f_mism * (1-PARS["f_LMP"]) * PARS["f_burn_R3"]

    dM_Pwaste_dt = R1_F_waste + R2_F_waste + R3_F_waste

    return(np.array([dM_R1_Ptot_rec_dt, 
                     dM_R2_Ptot_rec_dt,
                     dM_R3_Ptot_rec_dt,
                     dM_R1_Ptot_inc_dt,
                     dM_R2_Ptot_inc_dt,
                     dM_R3_Ptot_inc_dt,
                     dM_R1_Ptot_landf_dt,
                     dM_R2_Ptot_landf_dt,
                     dM_R3_Ptot_landf_dt,
                     dM_R1_P_mism_dt, 
                     dM_R2_P_mism_dt, 
                     dM_R3_P_mism_dt, 
                     dM_R1_LMP_mism_dt, 
                     dM_R2_LMP_mism_dt, 
                     dM_R3_LMP_mism_dt, 
                     dM_R1_sMP_mism_dt, 
                     dM_R2_sMP_mism_dt, 
                     dM_R3_sMP_mism_dt, 
                     dM_sMP_atmo_dt, 
                     dM_R1_sMP_soil_dt, 
                     dM_R2_sMP_soil_dt, 
                     dM_R3_sMP_soil_dt, 
                     dM_P_surf_dt, 
                     dM_LMP_surf_dt, 
                     dM_sMP_surf_dt, 
                     dM_P_sand_dt, 
                     dM_LMP_sand_dt, 
                     dM_sMP_sand_dt, 
                     dM_P_ssed, 
                     dM_LMP_ssed, 
                     dM_sMP_ssed, 
                     dM_LMP_wcol, 
                     dM_sMP_wcol, 
                     dM_LMP_dsed, 
                     dM_sMP_dsed, 
                     dM_P_clean_dt, 
                     dM_LMP_clean_dt, 
                     dM_sMP_clean_dt,
                     dM_R1_P_burn_dt,
                     dM_R2_P_burn_dt,
                     dM_R3_P_burn_dt,
                     dM_Pwaste_dt])) #Carreful, the order in important here, and has to be the same as the y vector

################################
#Preparations before running the model
################################
#print("Taking folder input, looping through all parameter .json in a folder.")
myfiles = [os.path.basename(x) for x in glob.glob(input_relpath+"*.json")]
#print(f"{len(myfiles)} input files were found")

#stripping away the .json extension
for i in range(0,len(myfiles)):
    myfiles[i] = os.path.splitext(myfiles[i])[0]
    #print(f"Taking input parameter file {myfiles[i]}")
  
    
################################
#Main function that will run the model
################################
def run_this(input_fname):
    global current_time
    print(input_fname)
    with open(input_relpath + input_fname + ".json","r") as myfile:
        PARS = json.load(myfile) #loading the input file
        
    FRCS = boxmodel_forcings(scenario_release, scenario_cleanup)# here the forcing functions (produced, waste, etc). Note that this class was imported from "boxmodel_forcings.py", which must be in the same folder.

    eval_times = np.linspace(t_span[0],t_span[1],(t_span[1]-t_span[0])*lines_per_year+1) # time where we want this to be evaluated (note that the ODE solver determines the correct time step for calculation automatically, this is just for output)

    initial_cond = np.zeros(42)  #set all initial conditions to 0

    soln = solve_ivp(fun=lambda t, y: Med_boxmodel(t, y, PARS, FRCS), 
                     t_span = t_span, y0 = initial_cond, t_eval = eval_times,
                     method = solv_method) #4th order Runge-Kutta for integration. This is default, but we specify it explicitely for clarity 

    
    ###############################
    #Writing model output
    ###############################
    # All mass (Tg)
    data_out = {
        "Year"          : soln.t,
        "M_R1_Ptot_rec" : soln.y[0],
        "M_R2_Ptot_rec" : soln.y[1],
        "M_R3_Ptot_rec" : soln.y[2],
        "M_R1_Ptot_inc" : soln.y[3],
        "M_R2_Ptot_inc" : soln.y[4],
        "M_R3_Ptot_inc" : soln.y[5],
        "M_R1_Ptot_landf" : soln.y[6],
        "M_R2_Ptot_landf" : soln.y[7],
        "M_R3_Ptot_landf" : soln.y[8],
        "M_R1_P_mism"   : soln.y[9],
        "M_R2_P_mism"   : soln.y[10],
        "M_R3_P_mism"   : soln.y[11],
        "M_R1_LMP_mism" : soln.y[12],
        "M_R2_LMP_mism" : soln.y[13],
        "M_R3_LMP_mism" : soln.y[14],
        "M_R1_sMP_mism" : soln.y[15],
        "M_R2_sMP_mism" : soln.y[16],
        "M_R3_sMP_mism" : soln.y[17],
        "M_sMP_atmo"    : soln.y[18],
        "M_R1_sMP_soil" : soln.y[19],
        "M_R2_sMP_soil" : soln.y[20],
        "M_R3_sMP_soil" : soln.y[21],
        "M_P_surf"      : soln.y[22],
        "M_LMP_surf"    : soln.y[23],
        "M_sMP_surf"    : soln.y[24],
        "M_P_sand"      : soln.y[25],
        "M_LMP_sand"    : soln.y[26],
        "M_sMP_sand"    : soln.y[27],
        "M_P_ssed"      : soln.y[28],
        "M_LMP_ssed"    : soln.y[29],
        "M_sMP_ssed"    : soln.y[30],
        "M_LMP_wcol"    : soln.y[31],
        "M_sMP_wcol"    : soln.y[32],
        "M_LMP_dsed"    : soln.y[33],
        "M_sMP_dsed"    : soln.y[34],
        "M_P_clean"     : soln.y[35],
        "M_LMP_clean"   : soln.y[36],
        "M_sMP_clean"   : soln.y[37],
        "M_R1_P_burn"   : soln.y[38],
        "M_R2_P_burn"   : soln.y[39],
        "M_R3_P_burn"   : soln.y[40],
        "M_Pwaste"      : soln.y[41]
    } 
    
    df = pd.DataFrame(data_out)
  
    ### Summary of regional data 
    df["M_Ptot_rec"] = df["M_R1_Ptot_rec"] + df["M_R2_Ptot_rec"] + df["M_R3_Ptot_rec"]
    df["M_Ptot_inc"] = df["M_R1_Ptot_inc"] + df["M_R2_Ptot_inc"] + df["M_R3_Ptot_inc"]
    df["M_Ptot_landf"] = df["M_R1_Ptot_landf"] + df["M_R2_Ptot_landf"] + df["M_R3_Ptot_landf"]
    
    df["M_P_mism"]   = df["M_R1_P_mism"]   + df["M_R2_P_mism"]   + df["M_R3_P_mism"]
    df["M_LMP_mism"] = df["M_R1_LMP_mism"] + df["M_R2_LMP_mism"] + df["M_R3_LMP_mism"]
    df["M_sMP_mism"] = df["M_R1_sMP_mism"] + df["M_R2_sMP_mism"] + df["M_R3_sMP_mism"]  
    df["M_Ptot_mism"] = df["M_P_mism"] + df["M_LMP_mism"] + df["M_sMP_mism"]
    
    df["M_R1_Ptot_mism"] = df["M_R1_P_mism"] + df["M_R1_LMP_mism"] + df["M_R1_sMP_mism"]
    df["M_R2_Ptot_mism"] = df["M_R2_P_mism"] + df["M_R2_LMP_mism"] + df["M_R2_sMP_mism"]
    df["M_R3_Ptot_mism"] = df["M_R3_P_mism"] + df["M_R3_LMP_mism"] + df["M_R3_sMP_mism"]
    
    df["M_sMP_soil"] = df["M_R1_sMP_soil"] + df["M_R2_sMP_soil"] + df["M_R3_sMP_soil"]
    
    df["M_P_burn"] = df["M_R1_P_burn"] + df["M_R2_P_burn"] + df["M_R3_P_burn"]
    
    #For convinience during plotting of total plastic
    df["M_Ptot_burn"] = df["M_P_burn"]
    df["M_Ptot_soil"] = df["M_sMP_soil"]
    df["M_Ptot_atmo"] = df["M_sMP_atmo"]
    df["M_Ptot_surf"] = df["M_P_surf"] + df["M_LMP_surf"] + df["M_sMP_surf"]
    df["M_Ptot_sand"] = df["M_P_sand"] + df["M_LMP_sand"] + df["M_sMP_sand"]
    df["M_Ptot_ssed"] = df["M_P_ssed"] + df["M_LMP_ssed"] + df["M_sMP_ssed"]
    df["M_Ptot_wcol"] = df["M_LMP_wcol"] + df["M_sMP_wcol"]
    df["M_Ptot_dsed"] = df["M_LMP_dsed"] + df["M_sMP_dsed"]
    df["M_Ptot_sed"]  = df["M_Ptot_ssed"] + df["M_Ptot_dsed"]
    
    ### Terrestrial pool
    df["M_Ptot_terr"] = df["M_Ptot_landf"] + df["M_Ptot_mism"] + df["M_sMP_soil"]
    ### Marine pool
    df["M_P_mar"] = df["M_P_surf"] + df["M_P_sand"] + df["M_P_ssed"]
    df["M_LMP_mar"] = df["M_LMP_surf"] + df["M_LMP_sand"] + df["M_LMP_ssed"] + df["M_LMP_wcol"] + df["M_LMP_dsed"]
    df["M_sMP_mar"] = df["M_sMP_surf"] + df["M_sMP_sand"] + df["M_sMP_ssed"] + df["M_sMP_wcol"] + df["M_sMP_dsed"]
    df["M_Ptot_mar"] = df["M_P_mar"] + df["M_LMP_mar"] + df["M_sMP_mar"]
    
    df["M_Ptot"] = df["M_Ptot_terr"] + df["M_Ptot_mar"] + df["M_sMP_atmo"] + df["M_Ptot_rec"] + df["M_Ptot_inc"] + df["M_Ptot_burn"]

    
    ### All flux columns (Tg/y) ===============================================
    # Rq : we do this outside the ODE solver, but the introduced error should be minimal
    df["FLUXES_AFTER"] = df["Year"] * np.nan #empty separating column for convenience
    
    #Total plastic waste by region
    R_F_waste_tot = FRCS.get_R_F_waste(df["Year"]) * PARS["F_waste_random"]
    df["F_R1_waste"] = R_F_waste_tot[0]
    df["F_R2_waste"] = R_F_waste_tot[1]
    df["F_R3_waste"] = R_F_waste_tot[2]
    df["F_waste"] = df["F_R1_waste"] + df["F_R2_waste"] + df["F_R3_waste"]
    
    #Recycled waste
    R_F_rec = R_F_waste_tot * FRCS.get_R_f_rec(df["Year"]) * PARS["f_rec_random"]
    df["F_R1_rec"] = R_F_rec[0]
    df["F_R2_rec"] = R_F_rec[1]
    df["F_R3_rec"] = R_F_rec[2]
    df["F_rec"] = df["F_R1_rec"] + df["F_R2_rec"] + df["F_R3_rec"]
    
    #Incinerated waste
    R_F_inc = R_F_waste_tot * FRCS.get_R_f_inc(df["Year"]) * PARS["f_inc_random"]
    df["F_R1_inc"] = R_F_inc[0]
    df["F_R2_inc"] = R_F_inc[1]
    df["F_R3_inc"] = R_F_inc[2]
    df["F_inc"] = df["F_R1_inc"] + df["F_R2_inc"] + df["F_R3_inc"]
    
    #Mismanaged waste
    R_F_mism = R_F_waste_tot * FRCS.get_R_f_mism(df["Year"]) * PARS["f_mism_random"]
    df["F_R1_mism"] = R_F_mism[0]
    df["F_R2_mism"] = R_F_mism[1]
    df["F_R3_mism"] = R_F_mism[2]
    df["F_mism"] = df["F_R1_mism"] + df["F_R2_mism"] + df["F_R3_mism"]
    
    #Sanitary landfilled waste
    R_F_landf = R_F_waste_tot - (R_F_rec + R_F_inc + R_F_mism)
    df["F_R1_landf"] = R_F_landf[0]
    df["F_R2_landf"] = R_F_landf[1]
    df["F_R3_landf"] = R_F_landf[2]
    df["F_landf"] = df["F_R1_landf"] + df["F_R2_landf"] + df["F_R3_landf"]
      
    ##River flow from mismanaged(by P type)
    #P
    df["F_R1_P_mism_to_surf"] = df["M_R1_P_mism"] * PARS["k_R1_P_terr_to_surf"]
    df["F_R2_P_mism_to_surf"] = df["M_R2_P_mism"] * PARS["k_R2_P_terr_to_surf"]
    df["F_R3_P_mism_to_surf"] = df["M_R3_P_mism"] * PARS["k_R3_P_terr_to_surf"]
    df["F_P_mism_to_surf"] = df["F_R1_P_mism_to_surf"] + df["F_R2_P_mism_to_surf"] + df["F_R3_P_mism_to_surf"]
    #LMP
    df["F_R1_LMP_mism_to_surf"] = df["M_R1_LMP_mism"] * PARS["k_R1_LMP_terr_to_surf"]
    df["F_R2_LMP_mism_to_surf"] = df["M_R2_LMP_mism"] * PARS["k_R2_LMP_terr_to_surf"]
    df["F_R3_LMP_mism_to_surf"] = df["M_R3_LMP_mism"] * PARS["k_R3_LMP_terr_to_surf"]
    df["F_LMP_mism_to_surf"] = df["F_R1_LMP_mism_to_surf"] + df["F_R2_LMP_mism_to_surf"] + df["F_R3_LMP_mism_to_surf"]
    #sMP
    df["F_R1_sMP_mism_to_surf"] = df["M_R1_sMP_mism"] * PARS["k_R1_sMP_terr_to_surf"]
    df["F_R2_sMP_mism_to_surf"] = df["M_R2_sMP_mism"] * PARS["k_R2_sMP_terr_to_surf"]
    df["F_R3_sMP_mism_to_surf"] = df["M_R3_sMP_mism"] * PARS["k_R3_sMP_terr_to_surf"]
    df["F_sMP_mism_to_surf"] = df["F_R1_sMP_mism_to_surf"] + df["F_R2_sMP_mism_to_surf"] + df["F_R3_sMP_mism_to_surf"]
    
    ##River flow from remote soil
    #sMP
    df["F_R1_sMP_soil_to_surf"] = df["M_R1_sMP_soil"] * PARS["k_R1_sMP_terr_to_surf"]
    df["F_R2_sMP_soil_to_surf"] = df["M_R2_sMP_soil"] * PARS["k_R2_sMP_terr_to_surf"]
    df["F_R3_sMP_soil_to_surf"] = df["M_R3_sMP_soil"] * PARS["k_R3_sMP_terr_to_surf"]
    df["F_sMP_soil_to_surf"] = df["F_R1_sMP_soil_to_surf"] + df["F_R2_sMP_soil_to_surf"] + df["F_R3_sMP_soil_to_surf"] 
    
    ##Total sMP river input
    df["F_R1_sMP_terr_to_surf"] = df["F_R1_sMP_mism_to_surf"] + df["F_R1_sMP_soil_to_surf"]
    df["F_R2_sMP_terr_to_surf"] = df["F_R2_sMP_mism_to_surf"] + df["F_R2_sMP_soil_to_surf"]
    df["F_R3_sMP_terr_to_surf"] = df["F_R3_sMP_mism_to_surf"] + df["F_R3_sMP_soil_to_surf"]
    df["F_sMP_terr_to_surf"] = df["F_sMP_mism_to_surf"] + df["F_sMP_soil_to_surf"]
    
    ##Total river input
    df["F_Ptot_terr_to_surf"] =  df["F_P_mism_to_surf"] + df["F_LMP_mism_to_surf"] + df["F_sMP_terr_to_surf"]
    #df["F_MP_terr_to_surf"] = df["F_sMP_terr_to_surf"] + df["F_LMP_mism_to_surf"] #Not necessary for data analysis anymore
    
    ##Total river flow (by region)
    df["F_R1_Ptot_terr_to_surf"] = df["F_R1_P_mism_to_surf"] + df["F_R1_LMP_mism_to_surf"] + df["F_R1_sMP_mism_to_surf"] + df["F_R1_sMP_soil_to_surf"]
    df["F_R2_Ptot_terr_to_surf"] = df["F_R2_P_mism_to_surf"] + df["F_R2_LMP_mism_to_surf"] + df["F_R2_sMP_mism_to_surf"] + df["F_R2_sMP_soil_to_surf"]
    df["F_R3_Ptot_terr_to_surf"] = df["F_R3_P_mism_to_surf"] + df["F_R3_LMP_mism_to_surf"] + df["F_R3_sMP_mism_to_surf"] + df["F_R3_sMP_soil_to_surf"]
    
    ##Atmospheric emissions
    #from mismnosphere
    df["F_R1_sMP_mism_to_atmo"] = df["M_R1_sMP_mism"] * PARS["k_R1_sMP_terr_to_atmo"] * (1 - PARS["f_soil_R1"])
    df["F_R2_sMP_mism_to_atmo"] = df["M_R2_sMP_mism"] * PARS["k_R2_sMP_terr_to_atmo"] * (1 - PARS["f_soil_R2"])
    df["F_R3_sMP_mism_to_atmo"] = df["M_R3_sMP_mism"] * PARS["k_R3_sMP_terr_to_atmo"] * (1 - PARS["f_soil_R3"])
    df["F_sMP_mism_to_atmo"] = df["F_R1_sMP_mism_to_atmo"] + df["F_R2_sMP_mism_to_atmo"] + df["F_R3_sMP_mism_to_atmo"]
    #from remote soil
    df["F_R1_sMP_soil_to_atmo"] = df["M_R1_sMP_soil"] * PARS["k_R1_sMP_terr_to_atmo"] * PARS["f_soil_R1"]
    df["F_R2_sMP_soil_to_atmo"] = df["M_R2_sMP_soil"] * PARS["k_R2_sMP_terr_to_atmo"] * PARS["f_soil_R2"]
    df["F_R3_sMP_soil_to_atmo"] = df["M_R3_sMP_soil"] * PARS["k_R3_sMP_terr_to_atmo"] * PARS["f_soil_R3"]
    df["F_sMP_soil_to_atmo"] = df["F_R1_sMP_soil_to_atmo"] + df["F_R2_sMP_soil_to_atmo"] + df["F_R3_sMP_soil_to_atmo"]
    #Total terrestrial emissions
    df["F_sMP_terr_to_atmo"] = df["F_sMP_mism_to_atmo"] + df["F_sMP_soil_to_atmo"]
    #from sea surface
    df["F_sMP_surf_to_atmo"] = df["M_sMP_surf"] * PARS["k_sMP_surf_to_atmo"]
    
    ##Atmospheric deposition
    #on mismnosphere
    df["F_R1_sMP_atmo_to_mism"] = df["M_sMP_atmo"] * PARS["k_R1_sMP_atmo_to_terr"] * (1- PARS["f_soil_R1"])
    df["F_R2_sMP_atmo_to_mism"] = df["M_sMP_atmo"] * PARS["k_R2_sMP_atmo_to_terr"] * (1- PARS["f_soil_R2"])
    df["F_R3_sMP_atmo_to_mism"] = df["M_sMP_atmo"] * PARS["k_R3_sMP_atmo_to_terr"] * (1- PARS["f_soil_R3"])
    df["F_sMP_atmo_to_mism"] = df["F_R1_sMP_atmo_to_mism"] + df["F_R2_sMP_atmo_to_mism"] + df["F_R3_sMP_atmo_to_mism"]
    #on remote soil
    df["F_R1_sMP_atmo_to_soil"] = df["M_sMP_atmo"] * PARS["k_R1_sMP_atmo_to_terr"] * PARS["f_soil_R1"]
    df["F_R2_sMP_atmo_to_soil"] = df["M_sMP_atmo"] * PARS["k_R2_sMP_atmo_to_terr"] * PARS["f_soil_R2"]
    df["F_R3_sMP_atmo_to_soil"] = df["M_sMP_atmo"] * PARS["k_R3_sMP_atmo_to_terr"] * PARS["f_soil_R3"]
    df["F_sMP_atmo_to_soil"] = df["F_R1_sMP_atmo_to_soil"] + df["F_R2_sMP_atmo_to_soil"] + df["F_R3_sMP_atmo_to_soil"] 
    #Total terrestrial deposition
    df["F_sMP_atmo_to_terr"] = df["F_sMP_atmo_to_mism"] + df["F_sMP_atmo_to_soil"]
    #on sea surface
    df["F_sMP_atmo_to_surf"] = df["M_sMP_atmo"] * PARS["k_sMP_atmo_to_surf"]
    
    ##Beaching
    df["F_P_surf_to_sand"]   = df["M_P_surf"]   * PARS["k_P_surf_to_sand"]
    df["F_LMP_surf_to_sand"] = df["M_LMP_surf"] * PARS["k_LMP_surf_to_sand"]
    df["F_sMP_surf_to_sand"] = df["M_sMP_surf"] * PARS["k_sMP_surf_to_sand"]
    df["F_Ptot_surf_to_sand"] = df["F_P_surf_to_sand"] + df["F_LMP_surf_to_sand"] + df["F_sMP_surf_to_sand"]
    
    ##Sinking
    #to shelf sediment
    df["F_P_surf_to_ssed"]   = df["M_P_surf"]   * PARS["k_P_surf_to_ssed"]   * PARS["f_ssed"]
    df["F_LMP_surf_to_ssed"] = df["M_LMP_surf"] * PARS["k_LMP_surf_to_ssed"] * PARS["f_ssed"]
    df["F_sMP_surf_to_ssed"] = df["M_sMP_surf"] * PARS["k_sMP_surf_to_ssed"] * PARS["f_ssed"]
    df["F_Ptot_surf_to_ssed"] = df["F_P_surf_to_ssed"] + df["F_LMP_surf_to_ssed"] + df["F_sMP_surf_to_ssed"]
    #to water column
    df["F_P_surf_to_wcol"]   = df["M_P_surf"]   * PARS["k_P_surf_to_wcol"]   * (1-PARS["f_ssed"])
    df["F_LMP_surf_to_wcol"] = df["M_LMP_surf"] * PARS["k_LMP_surf_to_wcol"] * (1-PARS["f_ssed"])
    df["F_sMP_surf_to_wcol"] = df["M_sMP_surf"] * PARS["k_sMP_surf_to_wcol"] * (1-PARS["f_ssed"])
    df["F_Ptot_surf_to_wcol"] = df["F_P_surf_to_wcol"] + df["F_LMP_surf_to_wcol"] + df["F_sMP_surf_to_wcol"]
    #to deep sediment
    df["F_LMP_wcol_to_dsed"] = df["M_LMP_wcol"] * PARS["k_LMP_wcol_to_dsed"]
    df["F_sMP_wcol_to_dsed"] = df["M_sMP_wcol"] * PARS["k_sMP_wcol_to_dsed"]
    df["F_Ptot_wcol_to_dsed"] = df["F_LMP_wcol_to_dsed"] + df["F_sMP_wcol_to_dsed"]
    
    df["F_sink_MP"] = df["F_LMP_surf_to_ssed"] + df["F_sMP_surf_to_ssed"] + df["F_LMP_surf_to_wcol"] + df["F_sMP_surf_to_wcol"]
    df["F_sink_Ptot"] = df["F_sink_MP"] + df["F_P_surf_to_ssed"] + df["F_P_surf_to_wcol"]
    df["F_sed_MP"] = df["F_LMP_surf_to_ssed"] + df["F_sMP_surf_to_ssed"] + df["F_LMP_wcol_to_dsed"] + df["F_sMP_wcol_to_dsed"]
    df["F_sed_Ptot"] = df["F_sed_MP"] + df["F_P_surf_to_ssed"]
    
    #Cleaning
    df["F_P_mism_to_clean"]   = df["M_R1_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][0] + df["M_R2_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][1] + df["M_R3_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][2]
    df["F_LMP_mism_to_clean"] = df["M_R1_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][0] + df["M_R2_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][1] + df["M_R3_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][2]
    df["F_sMP_mism_to_clean"] = df["M_R1_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][0] + df["M_R2_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][1] + df["M_R3_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][2]
    
    df["F_R1_Ptot_mism_to_clean"] = df["M_R1_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][0] + df["M_R1_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][0] + df["M_R1_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][0]
    df["F_R2_Ptot_mism_to_clean"] = df["M_R2_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][1] + df["M_R2_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][1] + df["M_R2_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][1]
    df["F_R3_Ptot_mism_to_clean"] = df["M_R3_P_mism"]   * FRCS.get_f_cleanUp(df["Year"])[0][2] + df["M_R3_LMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[1][2] + df["M_R3_sMP_mism"] * FRCS.get_f_cleanUp(df["Year"])[2][2]
   
    df["F_Ptot_mism_to_clean"] = df["F_P_mism_to_clean"] + df["F_LMP_mism_to_clean"] + df["F_sMP_mism_to_clean"]
    
    #Open burning
    df["F_R1_P_mism_to_burn"] = (df["F_R1_waste"] + df["M_R1_P_mism"] * FRCS.get_f_cleanUp(df["Year"])[0][0]) * PARS["f_mism_random"] * FRCS.get_R_f_mism(df["Year"])[0] * (1-PARS["f_LMP"]) * PARS["f_burn_R1"]
    df["F_R2_P_mism_to_burn"] = (df["F_R2_waste"] + df["M_R2_P_mism"] * FRCS.get_f_cleanUp(df["Year"])[0][1]) * PARS["f_mism_random"] * FRCS.get_R_f_mism(df["Year"])[1] * (1-PARS["f_LMP"]) * PARS["f_burn_R2"]
    df["F_R3_P_mism_to_burn"] = (df["F_R3_waste"] + df["M_R3_P_mism"] * FRCS.get_f_cleanUp(df["Year"])[0][2]) * PARS["f_mism_random"] * FRCS.get_R_f_mism(df["Year"])[2] * (1-PARS["f_LMP"]) * PARS["f_burn_R3"]
    df["F_P_mism_to_burn"] = df["F_R1_P_mism_to_burn"] + df["F_R2_P_mism_to_burn"] + df["F_R3_P_mism_to_burn"]
    
    if extended_control == True:
        ### Diverse values for control
        df["DIVERSE_AFTER"] = df["Year"] * np.nan #empty separating column for convenience
        
        ## Waste fractions
        # Recycled
        f_rec = FRCS.get_R_f_rec(df["Year"]) * PARS["f_rec_random"]
        df["f_rec_R1"] = f_rec[0]
        df["f_rec_R2"] = f_rec[1]
        df["f_rec_R3"] = f_rec[2]
        # Incinerated
        f_inc = FRCS.get_R_f_inc(df["Year"]) * PARS["f_inc_random"]
        df["f_inc_R1"] = f_inc[0]
        df["f_inc_R2"] = f_inc[1]
        df["f_inc_R3"] = f_inc[2]
        # Mismanaged
        f_mism = FRCS.get_R_f_mism(df["Year"]) * PARS["f_mism_random"]
        df["f_mism_R1"] = f_mism[0]
        df["f_mism_R2"] = f_mism[1]
        df["f_mism_R3"] = f_mism[2]
        # Landfilled 
        df["f_landf_R1"] = 1 - (df["f_rec_R1"] + df["f_inc_R1"] + df["f_mism_R1"])
        df["f_landf_R2"] = 1 - (df["f_rec_R2"] + df["f_inc_R2"] + df["f_mism_R2"])
        df["f_landf_R3"] = 1 - (df["f_rec_R3"] + df["f_inc_R3"] + df["f_mism_R3"])
        
        CleanUp = FRCS.get_f_cleanUp(df["Year"])
        f_P_cleanUp   = CleanUp[0]
        f_LMP_cleanUp = CleanUp[1]
        f_sMP_cleanUp = CleanUp[2]
        
        df["f_R1_P_cleanup"] = f_P_cleanUp[0]
        df["f_R2_P_cleanup"] = f_P_cleanUp[1]
        df["f_R3_P_cleanup"] = f_P_cleanUp[2]
        df["f_R1_LMP_cleanup"] = f_LMP_cleanUp[0]
        df["f_R2_LMP_cleanup"] = f_LMP_cleanUp[1]
        df["f_R3_LMP_cleanup"] = f_LMP_cleanUp[2]
        df["f_R1_sMP_cleanup"] = f_sMP_cleanUp[0]
        df["f_R2_sMP_cleanup"] = f_sMP_cleanUp[1]
        df["f_R3_sMP_cleanup"] = f_sMP_cleanUp[2]

    #automatically created output file name
    fname = f"OUTP_{current_time}_INP_{input_fname}.csv"

    #writing the output as .csv
    with open(output_relpath + fname, 'w', newline = "") as fout:
        if (extended_meta): #Add the Tittle and rq of the run
            fout.write("Used settings below\n")
            fout.write(f"Timespan, {t_span[0]}-{t_span[1]}\n")
            fout.write(f"Input, {input_fname}\n")
            fout.write(f"Method, {solv_method}\n")
            fout.write(f"scenario_release,{str(scenario_release).replace(',','').replace('array','').replace('(','').replace(')','')}\n")
            fout.write(f"scenario_atm,{str(scenario_atm).replace(',','').replace('array','').replace('(','').replace(')','')}\n")
            fout.write(f"scenario_cleanup,{str(scenario_cleanup).replace(',','').replace('array','').replace('(','').replace(')','')}\n") 
            fout.write("Used parameters below\n")
            for key, value in PARS.items():
                fout.write(f"{key}, {value}\n")
            fout.write("###############\n")
            fout.write("Data below\n")
        df.to_csv(fout)

'''
################################
#Executing the model not in parallel.
################################
for file in myfiles:
    run_this(file)
    
'''
################################
#Executing the model in parallel.
################################
def mute_process():
    sys.stdout = open(os.devnull, 'w')    

from time import sleep

parallel_process_number = 8

if __name__ == '__main__':
    poolstart = timer()
    pool = multiprocessing.Pool(parallel_process_number,initializer=mute_process)
    tqdm(pool.map(run_this, myfiles)) #running the actual model
    pool.close()
    pool.join()
    poolend = timer()
    sleep(1)
    print(f"Finished!\nThis took {int(divmod(poolend-poolstart, 60)[0])} min and {int(divmod(poolend-poolstart, 60)[1])} sec")
    print(f'\n{len(os.listdir(output_relpath))} new input files successfully created!')    
    print(current_time)



'''
###############################
#Updating the logbook
###############################
print("\nUpdating logbook...")
print(os.getcwd().format()+"\Logbook.xlsx")

### Append metadata to logbook
workbook_name = 'Logbook.xlsx'
wb = load_workbook(workbook_name)
wb.active = wb['OUTPUT']
page = wb.active

# New data to write:
meta = [[current_time, title, input_relpath, output_relpath, t_span[0], t_span[1], lines_per_year, len(myfiles), round(poolend-poolstart), 
         str(scenario_atm).replace(",","").replace("array","").replace("(","").replace(")",""), 
         str(scenario_release).replace(",","").replace("array","").replace("(","").replace(")",""),
         str(scenario_cleanup).replace(",","").replace("array","").replace("(","").replace(")",""), 
         Rq]]
### add the time it took in second
for info in meta:
    page.append(info)

wb.save(filename=workbook_name)

print("\nDone.")
'''
#End alarm
winsound.Beep(500, 500)
