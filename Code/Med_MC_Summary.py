import pandas as pd
import numpy as np
import glob
import os
import matplotlib.pyplot as plt
import time
from datetime import datetime#for timestamps
import winsound

#AMK 2023/11/20

#This script does the following:
#1) Read all "*csv" boxmodel-output files in a given folder (created with "boxmodel_run_MC.py")
#2) Put all output files into one large dataframe, where each output file is marked by the (unique) random 
#   seed used to generate the parameters
#3) Group the model output by the "Year" column and calculate overview statistics for all columns
#   Currently calculated overview statistics:
#       mean: arithmetic mean
#       std: standard deviation
#4) Save the so-grouped model output (+timestamp) in the project folder. This file should be used in further
#   analysis and plotting scripts!
#5) Plot one of the variables as an example. However, in order to avoid repetition
#   of calculations (which might take a while in case we have many input files),
#   further plotting should be done in a different script as mentioned above, by importing the grouped model output

historic_mode = False #if True, will use the files corresponding to the input_relpath provided. If false, will use the file inside ./Output_temp
save_summary = True #if True, save a copy of the summary inside ./scenario with the name save_summary_name
#
save_summary_name = "BAU"
#save_summary_name = "Fullstop"
#save_summary_name = "Freeze"
#save_summary_name = "OECD_RA"
#save_summary_name = "OECD_GA"
#save_summary_name = "Remediation"

#path to the output files (csv) from the box model. All *csv in this folder will be read in,
#so make sure it only contains what you're interested in!

input_relpath = "./Output/MC_OUT_" + "20231129_1153" + "/"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

if historic_mode == False:
    input_relpath = "./Output_temp/"
    timestamp = "temp"
    

#Get the names of all files in the folder
myfiles = [os.path.basename(x) for x in glob.glob(input_relpath+"*.csv")]

print(f"I found {len(myfiles)} boxmodel output files.")
print('\nReading all the files...')

tstart = time.perf_counter() #benchmarking

#create a list of dataframes, one for each file, and add an additional column corresponding to the (unique)
#random seed for each file. 
dflist = list()
for i in range(0,len(myfiles)):
    #get the seed
    myseed = pd.read_csv(input_relpath+myfiles[i], index_col=None, header=0,skiprows=7,nrows=1).values[0]
    #get the data
    df_temp = pd.read_csv(input_relpath+myfiles[i], index_col=None, header=1,skiprows=73) #for skiprows, add 9 to the pardict size
    #add seed as metadata
    df_temp=df_temp.assign(seed = int(myseed[0]))
    #append to a list of dataframes
    dflist.append(df_temp)
    #print the advencement
    print(end = '\x1b[2K')
    avance = str(round(100*(i)/len(myfiles)))
    print(avance + "% completed...", end = '\r')

#now combine list of dataframes into one file
df_all = pd.concat(dflist)

print('\nReading completed!')


#---------------------------------------------------
print('\nNow computing summary statistics...')

df_s_list = list()
#definition of the 2 quantile functions
#95% confidence interval
#def q_inf(x): return x.quantile(0.025)
#def q_sup(x): return x.quantile(0.975)
#90% confidence interval
#def q_inf(x): return x.quantile(0.05)
#def q_sup(x): return x.quantile(0.95)
#50% confidence interval (Q25, Q75)
def q_inf(x): return x.quantile(0.25)
def q_sup(x): return x.quantile(0.75)

i=0 #helper counter
for col in df_all.columns:
    print(end = '\x1b[2K')
    avance = str(round(100*(i)/len(df_all.columns)))
    print(avance + "% completed...", end = '\r')
    if col not in ['Year', 'seed','Unnamed: 0']:
        i = i+1
        #Now get an aggregated dataframe, calculating overview statistics for the "Year" time index. 
        df_s_temp = df_all.groupby('Year').agg({col : ['mean', 'std', 'median', q_inf, q_sup]}).reset_index()
        
        #flatten this multiindex dataframe into regular column names
        df_s_temp.columns = [c[0]+"_"+c[1] if c[1] else c[0] for c in df_s_temp.columns.tolist()]
        
        if i > 1: # we don't need to repeat the Year column each time 
            df_s_temp = df_s_temp.drop(columns=['Year'])

        df_s_list.append(df_s_temp)

print("\nSummary completed!")
tend=time.perf_counter()#benchmarking
print(f"\nThis took {round(tend-tstart,1)} seconds")

#now combine list of grouped dataframes into one file
df_s_all = pd.concat(df_s_list, axis=1)



if save_summary == True:
    output_relpath = "./Scenario/"
    if not os.path.exists(output_relpath):  #if the output file does not exist
        os.mkdir(output_relpath)            #create a new directory
    #create sub folder for the scenario
    output_relpath = "./Scenario/" + save_summary_name + "/"
    if not os.path.exists(output_relpath):  #if the output file does not exist
        os.mkdir(output_relpath)            #create a new directory
    df_s_all.to_csv(output_relpath + f"{save_summary_name}.csv") #save a copy of this sceanrio summary
else:
    output_relpath = input_relpath
    #saving this file
    df_s_all.to_csv(output_relpath + f"Aggregated_results_{timestamp}.csv")


#---------------------------------------------------
#Save all 2015 points for calibration plot
df_2015 = df_all[df_all['Year']==2016] #2016.0 includes the whole 2015 year but none of the 2016 year
df_2015.to_csv(output_relpath + f"2015_data_{timestamp}.csv")
print(f'\nCalibration data saved as : 2015_data_{timestamp}.csv')

#Save all 2015 points for calibration plot
df_2060 = df_all[df_all['Year']==2061] #2016.0 includes the whole 2015 year but none of the 2016 year
df_2060.to_csv(output_relpath + f"2060_data_{timestamp}.csv")
print(f'\nCalibration data saved as : 2060_data_{timestamp}.csv')

#Save all 2015 points for calibration plot
df_2100 = df_all[df_all['Year']==2100] #2016.0 includes the whole 2015 year but none of the 2016 year
df_2100.to_csv(output_relpath + f"2100_data_{timestamp}.csv")
print(f'\nCalibration data saved as : 2100_data_{timestamp}.csv')

##########
#Now printing the ref year values
##########


'''
print(f"\nStocks for {Y0}")

print('Recycled (all regions):')
print_value("M_Ptot_rec", "Ptot", sig=2)
print('Incinerated (all regions):')
print_value("M_Ptot_inc", "Ptot", sig=2)
print('Landfilled (all regions):')
print_value("M_Ptot_landf", "Ptot", sig=3)

print('Mismanaged pool (all regions):')
print_value("M_Ptot_mism", "Ptot", sig=2)
print_value("M_P_mism", "  P", sig=2)
print_value("M_LMP_mism", "LMP", sig=2)
print_value("M_sMP_mism", "sMP", sig=2)

print('Mismanaged pool (by regions):')
print(f'-> R1  : {round(df_s_2015.M_R1_Ptot_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R1_Ptot_mism_mean.item()/df_s_2015.M_Ptot_mism_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.M_R1_P_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R1_P_mism_mean.item()/df_s_2015.M_R1_Ptot_mism_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.M_R1_LMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R1_LMP_mism_mean.item()/df_s_2015.M_R1_Ptot_mism_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.M_R1_sMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R1_sMP_mism_mean.item()/df_s_2015.M_R1_Ptot_mism_mean.item(),1)} %)')

print(f'-> R2  : {round(df_s_2015.M_R2_Ptot_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R2_Ptot_mism_mean.item()/df_s_2015.M_Ptot_mism_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.M_R2_P_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R2_P_mism_mean.item()/df_s_2015.M_R2_Ptot_mism_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.M_R2_LMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R2_LMP_mism_mean.item()/df_s_2015.M_R2_Ptot_mism_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.M_R2_sMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R2_sMP_mism_mean.item()/df_s_2015.M_R2_Ptot_mism_mean.item(),1)} %)')

print(f'-> R3  : {round(df_s_2015.M_R3_Ptot_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R3_Ptot_mism_mean.item()/df_s_2015.M_Ptot_mism_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.M_R3_P_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R3_P_mism_mean.item()/df_s_2015.M_R3_Ptot_mism_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.M_R3_LMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R3_LMP_mism_mean.item()/df_s_2015.M_R3_Ptot_mism_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.M_R3_sMP_mism_mean.item(),3)} \tTg ({round(100*df_s_2015.M_R3_sMP_mism_mean.item()/df_s_2015.M_R3_Ptot_mism_mean.item(),1)} %)')


print('Soil (all regions):')
print_value("M_sMP_soil", "sMP")
print('Atmo :')
print_value("M_sMP_atmo", "sMP")
print('Surf :')
print_value("M_Ptot_surf", "Ptot")
print_value("M_P_surf", "  P")
print_value("M_LMP_surf", "LMP")
print_value("M_sMP_surf", "sMP")
print(f'\t %P: {round(100*df_s_2015.M_P_surf_mean.item()/(df_s_2015.M_P_surf_mean.item()+df_s_2015.M_LMP_surf_mean.item()+df_s_2015.M_sMP_surf_mean.item()),0)}%')
print('Sand :')
print_value("M_Ptot_sand", "Ptot")
print_value("M_P_sand", "  P")
print_value("M_LMP_sand", "LMP")
print_value("M_sMP_sand", "sMP")
print('Ssed :')
print_value("M_Ptot_ssed", "Ptot")
print_value("M_P_ssed", "  P")
print_value("M_LMP_ssed", "LMP")
print_value("M_sMP_ssed", "sMP")
print('Wcol :')
print_value("M_Ptot_wcol", "Ptot")
print_value("M_LMP_wcol", "LMP")
print_value("M_sMP_wcol", "sMP")
print('Dsed :')
print_value("M_Ptot_dsed", "Ptot")
print_value("M_LMP_dsed", "LMP")
print_value("M_sMP_dsed", "sMP")


print(f'\nFluxes for {Y0} :')
print('\nWaste flux :')
print(f'   Total waste: {round(df_s_2015.F_waste_mean.item(),3)} Tg/y')
print(f'   ---> R1 : {round(df_s_2015.F_R1_waste_mean.item(),3)} Tg/y')
print(f'   ---> R2 : {round(df_s_2015.F_R2_waste_mean.item(),3)} Tg/y')
print(f'   ---> R3 : {round(df_s_2015.F_R3_waste_mean.item(),3)} Tg/y')
print(f'   Recycled: {round(df_s_2015.F_rec_mean.item(),3)} Tg/y')
print(f'   ---> R1 : {round(df_s_2015.F_R1_rec_mean.item(),3)} Tg/y')
print(f'   ---> R2 : {round(df_s_2015.F_R2_rec_mean.item(),3)} Tg/y')
print(f'   ---> R3 : {round(df_s_2015.F_R3_rec_mean.item(),3)} Tg/y')
print(f'   Incinerated: {round(df_s_2015.F_inc_mean.item(),3)} Tg/y')
print(f'   ---> R1 : {round(df_s_2015.F_R1_inc_mean.item(),3)} Tg/y')
print(f'   ---> R2 : {round(df_s_2015.F_R2_inc_mean.item(),3)} Tg/y')
print(f'   ---> R3 : {round(df_s_2015.F_R3_inc_mean.item(),3)} Tg/y')
print(f'   landfilled: {round(df_s_2015.F_landf_mean.item(),3)} Tg/y')
print(f'   ---> R1 : {round(df_s_2015.F_R1_landf_mean.item(),3)} Tg/y')
print(f'   ---> R2 : {round(df_s_2015.F_R2_landf_mean.item(),3)} Tg/y')
print(f'   ---> R3 : {round(df_s_2015.F_R3_landf_mean.item(),3)} Tg/y')
print(f'   Mismanaged: {round(df_s_2015.F_mism_mean.item(),3)} Tg/y')
print(f'   ---> R1 : {round(df_s_2015.F_R1_mism_mean.item(),3)} Tg/y')
print(f'   ---> R2 : {round(df_s_2015.F_R2_mism_mean.item(),3)} Tg/y')
print(f'   ---> R3 : {round(df_s_2015.F_R3_mism_mean.item(),3)} Tg/y')

print('\nRiver Plastic flux :')
print(f'   Ptot: {round(df_s_2015.F_Ptot_terr_to_surf_mean.item(),3)} Tg/y ({round(df_s_2015.F_Ptot_terr_to_surf_q_inf.item(),3)}-{round(df_s_2015.F_Ptot_terr_to_surf_q_sup.item(),3)})')
print(f'   P   : {round(df_s_2015.F_P_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_P_mism_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'   LMP : {round(df_s_2015.F_LMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_LMP_mism_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'   sMP : {round(df_s_2015.F_sMP_terr_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_sMP_terr_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')

print(f'-> R1  : {round(df_s_2015.F_R1_Ptot_terr_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_Ptot_terr_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.F_R1_P_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_P_mism_to_surf_mean.item()/df_s_2015.F_R1_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.F_R1_LMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_LMP_mism_to_surf_mean.item()/df_s_2015.F_R1_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.F_R1_sMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_sMP_mism_to_surf_mean.item()/df_s_2015.F_R1_Ptot_terr_to_surf_mean.item(),1)} %)')

print(f'-> R2  : {round(df_s_2015.F_R2_Ptot_terr_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_Ptot_terr_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.F_R2_P_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_P_mism_to_surf_mean.item()/df_s_2015.F_R2_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.F_R2_LMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_LMP_mism_to_surf_mean.item()/df_s_2015.F_R2_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.F_R2_sMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_sMP_mism_to_surf_mean.item()/df_s_2015.F_R2_Ptot_terr_to_surf_mean.item(),1)} %)')

print(f'-> R3  : {round(df_s_2015.F_R3_Ptot_terr_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R3_Ptot_terr_to_surf_mean.item()/df_s_2015.F_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> P  : {round(df_s_2015.F_R3_P_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R3_P_mism_to_surf_mean.item()/df_s_2015.F_R3_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> LMP: {round(df_s_2015.F_R3_LMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R3_LMP_mism_to_surf_mean.item()/df_s_2015.F_R3_Ptot_terr_to_surf_mean.item(),1)} %)')
print(f'  --> sMP: {round(df_s_2015.F_R3_sMP_mism_to_surf_mean.item(),3)} \tTg/y ({round(100*df_s_2015.F_R3_sMP_mism_to_surf_mean.item()/df_s_2015.F_R3_Ptot_terr_to_surf_mean.item(),1)} %)')

print('\nRiver sMP flux :')
print(f'   from mism: {round(df_s_2015.F_sMP_mism_to_surf_mean.item(),3)} Tg/y')
print(f'   from soil: {round(df_s_2015.F_sMP_soil_to_surf_mean.item(),5)} Tg/y ({round(100*df_s_2015.F_sMP_soil_to_surf_mean.item()/df_s_2015.F_sMP_terr_to_surf_mean.item(),1)}% of total sMP river flux)')

print('\nSinking fluxes :')
print(f'   Ptot to ssed: {round(df_s_2015.F_Ptot_surf_to_ssed_mean.item(),2)} Tg/y')
print(f'              P: {round(df_s_2015.F_P_surf_to_ssed_mean.item(),2)} Tg/y ({round(df_s_2015.F_P_surf_to_ssed_mean.item()/df_s_2015.F_P_mism_to_surf_mean.item()*100,0)}% of river P flux)')
print(f'            LMP: {round(df_s_2015.F_LMP_surf_to_ssed_mean.item(),2)} Tg/y ({round(df_s_2015.F_LMP_surf_to_ssed_mean.item()/df_s_2015.F_LMP_mism_to_surf_mean.item()*100,0)}% of river LMP flux)')
print(f'            sMP: {round(df_s_2015.F_sMP_surf_to_ssed_mean.item(),2)} Tg/y ({round(df_s_2015.F_sMP_surf_to_ssed_mean.item()/df_s_2015.F_sMP_mism_to_surf_mean.item()*100,0)}% of river sMP flux)')
print(f'   Ptot to wcol: {round(df_s_2015.F_Ptot_surf_to_wcol_mean.item(),2)} Tg/y')
print(f'            LMP: {round(df_s_2015.F_LMP_surf_to_wcol_mean.item(),2)} Tg/y ({round(df_s_2015.F_LMP_surf_to_wcol_mean.item()/df_s_2015.F_LMP_mism_to_surf_mean.item()*100,0)}% of river LMP flux)')
print(f'            sMP: {round(df_s_2015.F_sMP_surf_to_wcol_mean.item(),2)} Tg/y ({round(df_s_2015.F_sMP_surf_to_wcol_mean.item()/df_s_2015.F_sMP_mism_to_surf_mean.item()*100,0)}% of river sMP flux)')
print(f'   Ptot to dsed: {round(df_s_2015.F_Ptot_wcol_to_dsed_mean.item(),5)} Tg/y')
print(f'            LMP: {round(df_s_2015.F_LMP_wcol_to_dsed_mean.item(),5)} Tg/y')
print(f'            sMP: {round(df_s_2015.F_sMP_wcol_to_dsed_mean.item(),5)} Tg/y')

print('\nBeaching fluxes :')
print(f'   Ptot to sand: {round(df_s_2015.F_Ptot_surf_to_sand_mean.item(),5)} Tg/y')

print('\nAtmospheric fluxes :')
print('   Deposition:')
print(f'   Total : {round(df_s_2015.F_sMP_atmo_to_surf_mean.item() + df_s_2015.F_sMP_atmo_to_mism_mean.item() + df_s_2015.F_sMP_atmo_to_soil_mean.item(),3)} Tg/y')
print(f'   sMP to surf: {round(df_s_2015.F_sMP_atmo_to_surf_mean.item(),3)} Tg/y')
print(f'   sMP to mism: {round(df_s_2015.F_sMP_atmo_to_mism_mean.item(),3)} Tg/y')
print(f'   sMP to soil: {round(df_s_2015.F_sMP_atmo_to_soil_mean.item(),3)} Tg/y')
print('   Emission:')
print(f'   Total : {round(df_s_2015.F_sMP_surf_to_atmo_mean.item() + df_s_2015.F_sMP_mism_to_atmo_mean.item() + df_s_2015.F_sMP_soil_to_atmo_mean.item(),3)} Tg/y')
print(f'   sMP from surf: {round(df_s_2015.F_sMP_surf_to_atmo_mean.item(),3)} Tg/y')
print(f'   sMP from mism: {round(df_s_2015.F_sMP_mism_to_atmo_mean.item(),3)} Tg/y')
print(f'   sMP from soil: {round(df_s_2015.F_sMP_soil_to_atmo_mean.item(),5)} Tg/y')
#---------------------------------------------------
#For control
print('\n=========== For Control ============')
print(f'Total waste produced (box version) : {round(df_s_2015.M_Pwaste_mean.item(),3)} Tg')

print(f'Total plastic in the model : {round(df_s_2015.M_Ptot_mean.item(),3)} Tg')
print(f'Difference: {round(df_s_2015.M_Pwaste_mean.item() - df_s_2015.M_Ptot_mean.item(),10)} Tg')
print(f'which corresponds to {round(100*(df_s_2015.M_Pwaste_mean.item() - df_s_2015.M_Ptot_mean.item())/df_s_2015.M_Pwaste_mean.item(),3)} % of the total waste produced')

print(f'Total marine plastic : {round(df_s_2015.M_Ptot_mar_mean.item(),3)} Tg (P: {round(df_s_2015.M_P_mar_mean.item(),3)} Tg, LMP: {round(df_s_2015.M_LMP_mar_mean.item(),3)} Tg, sMP: {round(df_s_2015.M_sMP_mar_mean.item(),3)} Tg)')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_mar_mean.item()/df_s_2015.M_Pwaste_mean.item(),2)} % of the total waste produced')
print(f'               or to {round(100*df_s_2015.M_Ptot_mar_mean.item()/df_s_2015.M_Ptot_terr_mean.item(),2)} % of the total terrestrial plastics')
print(f'               or to {round(100*df_s_2015.M_Ptot_mar_mean.item()/df_s_2015.M_Ptot_mism_mean.item(),2)} % of the total mismanaged waste')

print(f'Total terrestrial plastic : {round(df_s_2015.M_Ptot_terr_mean.item(),3)} Tg')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_terr_mean.item()/df_s_2015.M_Pwaste_mean.item(),1)} % of the total waste produced')

print(f'Total recycled plastic : {round(df_s_2015.M_Ptot_rec_mean.item(),3)} Tg')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_rec_mean.item()/df_s_2015.M_Pwaste_mean.item(),1)} % of the total waste produced')

print(f'Total incinerated plastic : {round(df_s_2015.M_Ptot_inc_mean.item(),3)} Tg')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_inc_mean.item()/df_s_2015.M_Pwaste_mean.item(),1)} % of the total waste produced')

print(f'Total landfilled plastic : {round(df_s_2015.M_Ptot_landf_mean.item(),3)} Tg')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_landf_mean.item()/df_s_2015.M_Pwaste_mean.item(),1)} % of the total waste produced')

print(f'Total mismanaged plastic : {round(df_s_2015.M_Ptot_mism_mean.item(),3)} Tg')
print(f'which corresponds to {round(100*df_s_2015.M_Ptot_mism_mean.item()/df_s_2015.M_Pwaste_mean.item(),1)} % of the total waste produced')

'''

#---------------------------------------------------
def summary_year(Y0=2016):
    
    df_s_2015 = df_s_all[df_s_all['Year'] == Y0]
    
    #Defining printing function
    def print_value_median(name, label, file, sig=1):
        Med = df_s_2015[name+"_median"].item()
        Qinf = df_s_2015[name+"_q_inf"].item()
        Qsup = df_s_2015[name+"_q_sup"].item()
        print(f'\t{label}: \t{Med:.{sig}} Tg \t({Qinf:.{sig}} - {Qsup:.{sig}})', file=file)

    with open(output_relpath + f"Summary_{save_summary_name}_{Y0}.txt", "w") as f:
        print(f"Stocks for {Y0}", file=f)
    
        print('\nRecycled (all regions):', file=f)
        print_value_median("M_Ptot_rec", "Ptot", sig=2, file=f)
        print('Incinerated (all regions):', file=f)
        print_value_median("M_Ptot_inc", "Ptot", sig=2, file=f)
        print('Landfilled (all regions):', file=f)
        print_value_median("M_Ptot_landf", "Ptot", sig=3, file=f)
        print('Open burned (all regions):', file=f)
        print_value_median("M_P_burn", "P", sig=3, file=f)
        
        print('Mismanaged pool (all regions):', file=f)
        print_value_median("M_Ptot_mism", "Ptot", sig=2, file=f)
        print_value_median("M_P_mism", "  P", sig=2, file=f)
        print_value_median("M_LMP_mism", "LMP", sig=2, file=f)
        print_value_median("M_sMP_mism", "sMP", sig=2, file=f)
    
        print('Mismanaged pool (by regions):', file=f)
        print(f'-> R1  : {round(df_s_2015.M_R1_Ptot_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R1_Ptot_mism_median.item()/df_s_2015.M_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.M_R1_P_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R1_P_mism_median.item()/df_s_2015.M_R1_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.M_R1_LMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R1_LMP_mism_median.item()/df_s_2015.M_R1_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.M_R1_sMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R1_sMP_mism_median.item()/df_s_2015.M_R1_Ptot_mism_median.item(),1)} %)', file=f)
    
        print(f'-> R2  : {round(df_s_2015.M_R2_Ptot_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R2_Ptot_mism_median.item()/df_s_2015.M_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.M_R2_P_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R2_P_mism_median.item()/df_s_2015.M_R2_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.M_R2_LMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R2_LMP_mism_median.item()/df_s_2015.M_R2_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.M_R2_sMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R2_sMP_mism_median.item()/df_s_2015.M_R2_Ptot_mism_median.item(),1)} %)', file=f)
    
        print(f'-> R3  : {round(df_s_2015.M_R3_Ptot_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R3_Ptot_mism_median.item()/df_s_2015.M_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.M_R3_P_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R3_P_mism_median.item()/df_s_2015.M_R3_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.M_R3_LMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R3_LMP_mism_median.item()/df_s_2015.M_R3_Ptot_mism_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.M_R3_sMP_mism_median.item(),3)} \tTg ({round(100*df_s_2015.M_R3_sMP_mism_median.item()/df_s_2015.M_R3_Ptot_mism_median.item(),1)} %)', file=f)
    
    
        print('Soil (all regions):', file=f)
        print_value_median("M_sMP_soil", "sMP", file=f)
        print('Atmo :', file=f)
        print_value_median("M_sMP_atmo", "sMP", file=f)
        print('Surf :', file=f)
        print_value_median("M_Ptot_surf", "Ptot", sig=2, file=f)
        print_value_median("M_P_surf", "  P", sig=2, file=f)
        print_value_median("M_LMP_surf", "LMP", sig=2, file=f)
        print_value_median("M_sMP_surf", "sMP", sig=2, file=f)
        print(f'\t %P: {round(100*df_s_2015.M_P_surf_median.item()/(df_s_2015.M_P_surf_median.item()+df_s_2015.M_LMP_surf_median.item()+df_s_2015.M_sMP_surf_median.item()),0)}%', file=f)
        print('Sand :', file=f)
        print_value_median("M_Ptot_sand", "Ptot", sig=2, file=f)
        print_value_median("M_P_sand", "  P", sig=2, file=f)
        print_value_median("M_LMP_sand", "LMP", sig=2, file=f)
        print_value_median("M_sMP_sand", "sMP", sig=2, file=f)
        print('Ssed :', file=f)
        print_value_median("M_Ptot_ssed", "Ptot", sig=2, file=f)
        print_value_median("M_P_ssed", "  P", sig=2, file=f)
        print_value_median("M_LMP_ssed", "LMP", sig=2, file=f)
        print_value_median("M_sMP_ssed", "sMP", sig=2, file=f)
        print('Wcol :', file=f)
        print_value_median("M_Ptot_wcol", "Ptot", sig=2, file=f)
        print_value_median("M_LMP_wcol", "LMP", sig=2, file=f)
        print_value_median("M_sMP_wcol", "sMP", sig=2, file=f)
        print('Dsed :', file=f)
        print_value_median("M_Ptot_dsed", "Ptot", sig=2, file=f)
        print_value_median("M_LMP_dsed", "LMP", sig=2, file=f)
        print_value_median("M_sMP_dsed", "sMP", sig=2, file=f)
    
    
        print(f'\nFluxes for {Y0} :', file=f)
        print('\nWaste flux :', file=f)
        print(f'   Total waste: {round(df_s_2015.F_waste_median.item(),3)} Tg/y ({round(df_s_2015.F_waste_q_inf.item(),3)}-{round(df_s_2015.F_waste_q_sup.item(),3)})', file=f)
        print(f'   ---> R1 : {round(df_s_2015.F_R1_waste_median.item(),3)} Tg/y ({round(df_s_2015.F_R1_waste_q_inf.item(),3)}-{round(df_s_2015.F_R1_waste_q_sup.item(),3)})', file=f)
        print(f'   ---> R2 : {round(df_s_2015.F_R2_waste_median.item(),3)} Tg/y ({round(df_s_2015.F_R2_waste_q_inf.item(),3)}-{round(df_s_2015.F_R2_waste_q_sup.item(),3)})', file=f)
        print(f'   ---> R3 : {round(df_s_2015.F_R3_waste_median.item(),3)} Tg/y ({round(df_s_2015.F_R3_waste_q_inf.item(),3)}-{round(df_s_2015.F_R3_waste_q_sup.item(),3)})', file=f)
        print(f'   Recycled: {round(df_s_2015.F_rec_median.item(),3)} Tg/y ({round(df_s_2015.F_rec_q_inf.item(),3)}-{round(df_s_2015.F_rec_q_sup.item(),3)})', file=f)
        print(f'   ---> R1 : {round(df_s_2015.F_R1_rec_median.item(),3)} Tg/y ({round(df_s_2015.F_R1_rec_q_inf.item(),3)}-{round(df_s_2015.F_R1_rec_q_sup.item(),3)})', file=f)
        print(f'   ---> R2 : {round(df_s_2015.F_R2_rec_median.item(),3)} Tg/y ({round(df_s_2015.F_R2_rec_q_inf.item(),3)}-{round(df_s_2015.F_R2_rec_q_sup.item(),3)})', file=f)
        print(f'   ---> R3 : {round(df_s_2015.F_R3_rec_median.item(),3)} Tg/y ({round(df_s_2015.F_R3_rec_q_inf.item(),3)}-{round(df_s_2015.F_R3_rec_q_sup.item(),3)})', file=f)
        print(f'   Incinerated: {round(df_s_2015.F_inc_median.item(),3)} Tg/y ({round(df_s_2015.F_inc_q_inf.item(),3)}-{round(df_s_2015.F_inc_q_sup.item(),3)})', file=f)
        print(f'   ---> R1 : {round(df_s_2015.F_R1_inc_median.item(),3)} Tg/y ({round(df_s_2015.F_R1_inc_q_inf.item(),3)}-{round(df_s_2015.F_R1_inc_q_sup.item(),3)})', file=f)
        print(f'   ---> R2 : {round(df_s_2015.F_R2_inc_median.item(),3)} Tg/y ({round(df_s_2015.F_R2_inc_q_inf.item(),3)}-{round(df_s_2015.F_R2_inc_q_sup.item(),3)})', file=f)
        print(f'   ---> R3 : {round(df_s_2015.F_R3_inc_median.item(),3)} Tg/y ({round(df_s_2015.F_R3_inc_q_inf.item(),3)}-{round(df_s_2015.F_R3_inc_q_sup.item(),3)})', file=f)
        print(f'   landfilled: {round(df_s_2015.F_landf_median.item(),3)} Tg/y ({round(df_s_2015.F_landf_q_inf.item(),3)}-{round(df_s_2015.F_landf_q_sup.item(),3)})', file=f)
        print(f'   ---> R1 : {round(df_s_2015.F_R1_landf_median.item(),3)} Tg/y ({round(df_s_2015.F_R1_landf_q_inf.item(),3)}-{round(df_s_2015.F_R1_landf_q_sup.item(),3)})', file=f)
        print(f'   ---> R2 : {round(df_s_2015.F_R2_landf_median.item(),3)} Tg/y ({round(df_s_2015.F_R2_landf_q_inf.item(),3)}-{round(df_s_2015.F_R2_landf_q_sup.item(),3)})', file=f)
        print(f'   ---> R3 : {round(df_s_2015.F_R3_landf_median.item(),3)} Tg/y ({round(df_s_2015.F_R3_landf_q_inf.item(),3)}-{round(df_s_2015.F_R3_landf_q_sup.item(),3)})', file=f)
        print(f'   Mismanaged: {round(df_s_2015.F_mism_median.item(),3)} Tg/y ({round(df_s_2015.F_mism_q_inf.item(),3)}-{round(df_s_2015.F_mism_q_sup.item(),3)})', file=f)
        print(f'   ---> R1 : {round(df_s_2015.F_R1_mism_median.item(),3)} Tg/y ({round(df_s_2015.F_R1_mism_q_inf.item(),3)}-{round(df_s_2015.F_R1_mism_q_sup.item(),3)})', file=f)
        print(f'   ---> R2 : {round(df_s_2015.F_R2_mism_median.item(),3)} Tg/y ({round(df_s_2015.F_R2_mism_q_inf.item(),3)}-{round(df_s_2015.F_R2_mism_q_sup.item(),3)})', file=f)
        print(f'   ---> R3 : {round(df_s_2015.F_R3_mism_median.item(),3)} Tg/y ({round(df_s_2015.F_R3_mism_q_inf.item(),3)}-{round(df_s_2015.F_R3_mism_q_sup.item(),3)})', file=f)
    
        print('\nRiver Plastic flux :', file=f)
        print(f'   Ptot: {round(df_s_2015.F_Ptot_terr_to_surf_median.item(),3)} Tg/y ({round(df_s_2015.F_Ptot_terr_to_surf_q_inf.item(),3)}-{round(df_s_2015.F_Ptot_terr_to_surf_q_sup.item(),3)})', file=f)
        print(f'   P   : {round(df_s_2015.F_P_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_P_mism_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'   LMP : {round(df_s_2015.F_LMP_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_LMP_mism_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'   sMP : {round(df_s_2015.F_sMP_terr_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_sMP_terr_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
    
        print(f'-> R1  : {round(df_s_2015.F_R1_Ptot_terr_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_Ptot_terr_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.F_R1_P_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_P_mism_to_surf_median.item()/df_s_2015.F_R1_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.F_R1_LMP_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_LMP_mism_to_surf_median.item()/df_s_2015.F_R1_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.F_R1_sMP_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R1_sMP_mism_to_surf_median.item()/df_s_2015.F_R1_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
    
        print(f'-> R2  : {round(df_s_2015.F_R2_Ptot_terr_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_Ptot_terr_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.F_R2_P_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_P_mism_to_surf_median.item()/df_s_2015.F_R2_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.F_R2_LMP_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_LMP_mism_to_surf_median.item()/df_s_2015.F_R2_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.F_R2_sMP_mism_to_surf_median.item(),3)} \tTg/y ({round(100*df_s_2015.F_R2_sMP_mism_to_surf_median.item()/df_s_2015.F_R2_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
    
        print(f'-> R3  : {round(df_s_2015.F_R3_Ptot_terr_to_surf_median.item(),5)} \tTg/y ({round(100*df_s_2015.F_R3_Ptot_terr_to_surf_median.item()/df_s_2015.F_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> P  : {round(df_s_2015.F_R3_P_mism_to_surf_median.item(),5)} \tTg/y ({round(100*df_s_2015.F_R3_P_mism_to_surf_median.item()/df_s_2015.F_R3_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> LMP: {round(df_s_2015.F_R3_LMP_mism_to_surf_median.item(),5)} \tTg/y ({round(100*df_s_2015.F_R3_LMP_mism_to_surf_median.item()/df_s_2015.F_R3_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
        print(f'  --> sMP: {round(df_s_2015.F_R3_sMP_mism_to_surf_median.item(),5)} \tTg/y ({round(100*df_s_2015.F_R3_sMP_mism_to_surf_median.item()/df_s_2015.F_R3_Ptot_terr_to_surf_median.item(),1)} %)', file=f)
    
        print('\nRiver sMP flux :', file=f)
        print(f'   from mism: {round(df_s_2015.F_sMP_mism_to_surf_median.item(),3)} Tg/y', file=f)
        print(f'   from soil: {round(df_s_2015.F_sMP_soil_to_surf_median.item(),5)} Tg/y ({round(100*df_s_2015.F_sMP_soil_to_surf_median.item()/df_s_2015.F_sMP_terr_to_surf_median.item(),1)}% of total sMP river flux)', file=f)
    
        print('\nSinking fluxes :', file=f)
        print(f'   Ptot to ssed: {round(df_s_2015.F_Ptot_surf_to_ssed_median.item(),3)} Tg/y', file=f)
        print(f'              P: {round(df_s_2015.F_P_surf_to_ssed_median.item(),3)} Tg/y ({round(df_s_2015.F_P_surf_to_ssed_median.item()/df_s_2015.F_P_mism_to_surf_median.item()*100,0)}% of river P flux)', file=f)
        print(f'            LMP: {round(df_s_2015.F_LMP_surf_to_ssed_median.item(),3)} Tg/y ({round(df_s_2015.F_LMP_surf_to_ssed_median.item()/df_s_2015.F_LMP_mism_to_surf_median.item()*100,0)}% of river LMP flux)', file=f)
        print(f'            sMP: {round(df_s_2015.F_sMP_surf_to_ssed_median.item(),3)} Tg/y ({round(df_s_2015.F_sMP_surf_to_ssed_median.item()/df_s_2015.F_sMP_mism_to_surf_median.item()*100,0)}% of river sMP flux)', file=f)
        print(f'   Ptot to wcol: {round(df_s_2015.F_Ptot_surf_to_wcol_median.item(),3)} Tg/y', file=f)
        print(f'            LMP: {round(df_s_2015.F_LMP_surf_to_wcol_median.item(),3)} Tg/y ({round(df_s_2015.F_LMP_surf_to_wcol_median.item()/df_s_2015.F_LMP_mism_to_surf_median.item()*100,0)}% of river LMP flux)', file=f)
        print(f'            sMP: {round(df_s_2015.F_sMP_surf_to_wcol_median.item(),3)} Tg/y ({round(df_s_2015.F_sMP_surf_to_wcol_median.item()/df_s_2015.F_sMP_mism_to_surf_median.item()*100,0)}% of river sMP flux)', file=f)
        print(f'   Ptot to dsed: {round(df_s_2015.F_Ptot_wcol_to_dsed_median.item(),5)} Tg/y', file=f)
        print(f'            LMP: {round(df_s_2015.F_LMP_wcol_to_dsed_median.item(),5)} Tg/y', file=f)
        print(f'            sMP: {round(df_s_2015.F_sMP_wcol_to_dsed_median.item(),5)} Tg/y', file=f)
    
        print('\nBeaching fluxes :', file=f)
        print(f'   Ptot to sand: {round(df_s_2015.F_Ptot_surf_to_sand_median.item(),5)} Tg/y', file=f)
    
        print('\nAtmospheric fluxes :', file=f)
        print('   Deposition:', file=f)
        print(f'   Total : {round(df_s_2015.F_sMP_atmo_to_surf_median.item() + df_s_2015.F_sMP_atmo_to_mism_median.item() + df_s_2015.F_sMP_atmo_to_soil_median.item(),4)} Tg/y', file=f)
        print(f'   sMP to surf: {round(df_s_2015.F_sMP_atmo_to_surf_median.item(),4)} Tg/y', file=f)
        print(f'   sMP to mism: {round(df_s_2015.F_sMP_atmo_to_mism_median.item(),4)} Tg/y', file=f)
        print(f'   sMP to soil: {round(df_s_2015.F_sMP_atmo_to_soil_median.item(),4)} Tg/y', file=f)
        print('   Emission:', file=f)
        print(f'   Total : {round(df_s_2015.F_sMP_surf_to_atmo_median.item() + df_s_2015.F_sMP_mism_to_atmo_median.item() + df_s_2015.F_sMP_soil_to_atmo_median.item(),4)} Tg/y', file=f)
        print(f'   sMP from surf: {round(df_s_2015.F_sMP_surf_to_atmo_median.item(),4)} Tg/y', file=f)
        print(f'   sMP from mism: {round(df_s_2015.F_sMP_mism_to_atmo_median.item(),4)} Tg/y', file=f)
        print(f'   sMP from soil: {round(df_s_2015.F_sMP_soil_to_atmo_median.item(),4)} Tg/y', file=f)
        #---------------------------------------------------
        #For control
        print('\n=========== For Control ============', file=f)
        print(f'Total waste produced (box version) : {round(df_s_2015.M_Pwaste_median.item(),3)} Tg', file=f)
    
        print(f'Total plastic in the model : {round(df_s_2015.M_Ptot_median.item(),3)} Tg', file=f)
        print(f'Difference: {round(df_s_2015.M_Pwaste_median.item() - df_s_2015.M_Ptot_median.item(),10)} Tg', file=f)
        print(f'which corresponds to {round(100*(df_s_2015.M_Pwaste_median.item() - df_s_2015.M_Ptot_median.item())/df_s_2015.M_Pwaste_median.item(),3)} % of the total waste produced', file=f)

        print_value_median("M_Ptot_mar", "Total marine plastic", file=f, sig=2)
        print(f'(P: {round(df_s_2015.M_P_mar_median.item(),3)} Tg, LMP: {round(df_s_2015.M_LMP_mar_median.item(),3)} Tg, sMP: {round(df_s_2015.M_sMP_mar_median.item(),3)} Tg)', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_mar_median.item()/df_s_2015.M_Pwaste_median.item(),2)} % of the total waste produced', file=f)
        print(f'               or to {round(100*df_s_2015.M_Ptot_mar_median.item()/df_s_2015.M_Ptot_terr_median.item(),2)} % of the total terrestrial plastics', file=f)
        print(f'               or to {round(100*df_s_2015.M_Ptot_mar_median.item()/df_s_2015.M_Ptot_mism_median.item(),2)} % of the total mismanaged waste', file=f)
    
        print(f'Total terrestrial plastic : {round(df_s_2015.M_Ptot_terr_median.item(),3)} Tg', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_terr_median.item()/df_s_2015.M_Pwaste_median.item(),1)} % of the total waste produced', file=f)
    
        print(f'Total recycled plastic : {round(df_s_2015.M_Ptot_rec_median.item(),3)} Tg', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_rec_median.item()/df_s_2015.M_Pwaste_median.item(),1)} % of the total waste produced', file=f)
    
        print(f'Total incinerated plastic : {round(df_s_2015.M_Ptot_inc_median.item(),3)} Tg', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_inc_median.item()/df_s_2015.M_Pwaste_median.item(),1)} % of the total waste produced', file=f)
    
        print(f'Total landfilled plastic : {round(df_s_2015.M_Ptot_landf_median.item(),3)} Tg', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_landf_median.item()/df_s_2015.M_Pwaste_median.item(),1)} % of the total waste produced', file=f)
    
        print(f'Total mismanaged plastic : {round(df_s_2015.M_Ptot_mism_median.item(),3)} Tg', file=f)
        print(f'which corresponds to {round(100*df_s_2015.M_Ptot_mism_median.item()/df_s_2015.M_Pwaste_median.item(),1)} % of the total waste produced', file=f)

summary_year(2016)
summary_year(2024)
summary_year(2061)
summary_year(2100)
    
Selected_years = [2016,2024,2061,2100]

Annual_s = df_s_all.loc[df_s_all['Year'].isin(Selected_years)].transpose()
Annual_s.columns = Selected_years
Annual_s = Annual_s[1:]
Annual_s["Name"] = Annual_s.index


Annual_s_mean = Annual_s[Annual_s['Name'].str.contains("median")]
Annual_s_mean = Annual_s_mean.reset_index(drop=True)

Annual_s_mean["2015_to_2024"] = (Annual_s_mean[Selected_years[1]]-Annual_s_mean[Selected_years[0]])/Annual_s_mean[Selected_years[0]]
Annual_s_mean["2015_to_2060"] = (Annual_s_mean[Selected_years[2]]-Annual_s_mean[Selected_years[0]])/Annual_s_mean[Selected_years[0]]
Annual_s_mean["2015_to_2100"] = (Annual_s_mean[Selected_years[3]]-Annual_s_mean[Selected_years[0]])/Annual_s_mean[Selected_years[0]]
Annual_s_mean["2024_to_2060"] = (Annual_s_mean[Selected_years[2]]-Annual_s_mean[Selected_years[1]])/Annual_s_mean[Selected_years[1]]
Annual_s_mean["2024_to_2100"] = (Annual_s_mean[Selected_years[3]]-Annual_s_mean[Selected_years[1]])/Annual_s_mean[Selected_years[1]]

Annual_s_mean.to_csv(output_relpath + f"{save_summary_name}_change.csv")

#End alarm
winsound.Beep(500, 500)
