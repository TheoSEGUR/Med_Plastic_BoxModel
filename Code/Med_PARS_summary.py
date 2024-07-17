"""
Created on Fri Nov 24 10:18:56 2023

@author: theos

SUMMARY OF THE PARAMETERS
"""
import glob
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns

###Test for statistics on the parameters
#input_relpath = "./Input/MC_params_" + "20231129_1152" + "/" #Directory For my computer
#input_relpath = "./MC_params/" #Directory for the default setup
input_relpath = "./Input_temp/"

print(f'Searching inside {input_relpath}')


myfiles = [os.path.basename(x) for x in glob.glob(input_relpath+"*.json")] #list all the files names in the directory
print(f"{len(myfiles)} input parameter file(s) in process...")

PARS_list = pd.DataFrame() #create empty dataframe for stocking all the data
for input_fname in myfiles :
    with open(input_relpath + input_fname,"r") as myfile :
        PARS = json.load(myfile) #loading the input file
        PARS = pd.DataFrame(PARS.items()) #Turn the dict into dataframe
        PARS[2] = int(PARS[1][0]) #add a intex column corresponding to the seed
        PARS = PARS.pivot(columns=0, values=1, index=2) #rearrange the dataframe so that the parameter are in coluns
        PARS_list = pd.concat([PARS_list, PARS]) #merge the dataframe with the previous ones
print("\nDone")  

'''
### if you want to see one parameter in the console     
var_name = "k_LMP_surf_to_ssed" #choose the name of the parameter you want to see the distribution
PARS_list[var_name].describe(percentiles=[0.025,0.5,0.975])  #here, give the quantile you want to be displayed
plt.hist(PARS_list[var_name], bins=100)    #plot the histogram
plt.title(var_name)
plt.xscale("log")
plt.show()
'''
### if you want to save the stats for all parameters
PARS_summary = PARS_list.describe(percentiles=[0.25,0.5,0.75]).T  #create stat dataframe
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") #create timestamp
PARS_summary.to_csv(f"{input_relpath}PARS_summary_{timestamp}.csv")

### Plot regional k values
P_type = "LMP"
box_from = "terr" #Enter the compartment studied
box_to = "surf"
show_R1 = True
show_R2 = True
show_R3 = True
# R1
if show_R1 == True:
    R1 = 'k_R1_' + P_type + "_" + box_from + '_to_' + box_to
    plt.hist(PARS_list[R1], label = "Region 1", alpha=1)    #plot the histogram
# R2
if show_R2 == True:
    R2 = 'k_R2_' + P_type + "_" + box_from + '_to_' + box_to
    plt.hist(PARS_list[R2], label = "Region 2", alpha=0.3)    #plot the histogram
# R3
if show_R2 == True:
    R3 = 'k_R3_' + P_type + "_" + box_from + '_to_' + box_to
    plt.hist(PARS_list[R3], label = "Region 3", alpha=0.3)    #plot the histogram

plt.xscale("log")
plt.xlabel("k value (y-1)")
plt.title("k_"+P_type+"_"+box_from+"_to_"+box_to)
plt.legend(loc='upper left')
#plt.xlim(0,0.01)
plt.show()

sns.distplot(PARS_list["F_LMP_terr_to_surf"], hist=True, kde=True, 
             color = 'darkblue', 
             hist_kws={'edgecolor':'black'},
             kde_kws={'linewidth': 4})


#print some interesting values
def print_PARS(name, sig=1, unit='1/y'):
    Mean = PARS_summary["mean"][name].item()
    Qinf = PARS_summary["25%"][name].item()
    Qsup = PARS_summary["75%"][name].item()
    print(f'\t{name}: \t{Mean:.{sig}} \t{unit} \t({Qinf:.{sig}} - {Qsup:.{sig}})')

print_PARS("F_P_terr_to_surf", unit="Tg/y")
print_PARS("F_LMP_terr_to_surf", unit="Tg/y")
print_PARS("F_sMP_terr_to_surf", unit="Tg/y")
print("P:")
print_PARS("k_R1_P_terr_to_surf")
print_PARS("k_R2_P_terr_to_surf")
print_PARS("k_R3_P_terr_to_surf")
print_PARS("k_P_surf_to_ssed",4)
print_PARS("k_P_surf_to_wcol",3)
print("LMP:")
print_PARS("k_R1_LMP_terr_to_surf")
print_PARS("k_R2_LMP_terr_to_surf")
print_PARS("k_R3_LMP_terr_to_surf")
print_PARS("k_LMP_surf_to_ssed",4)
print_PARS("k_LMP_surf_to_wcol",3)
print("sMP:")
print_PARS("k_R1_sMP_terr_to_surf")
print_PARS("k_R2_sMP_terr_to_surf")
print_PARS("k_R3_sMP_terr_to_surf")
print_PARS("k_sMP_surf_to_ssed",4)
print_PARS("k_sMP_surf_to_wcol",3)