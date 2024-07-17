import numpy as np
import datetime
import pandas as pd
from scipy.interpolate import CubicSpline


# importing data for interpolation
with open("./Forcings.txt","r") as f:
    Forcings = pd.read_table(f)
    Year = Forcings["Year"][~np.isnan(Forcings["Year"])]
extra = True    
F_waste_R1 = CubicSpline(Forcings["Year_waste"],Forcings["R1_F_waste"], extrapolate=extra)
F_waste_R2 = CubicSpline(Forcings["Year_waste"],Forcings["R2_F_waste"], extrapolate=extra)
F_waste_R3 = CubicSpline(Forcings["Year_waste"],Forcings["R3_F_waste"], extrapolate=extra)

OECD_RA_F_waste_R1  = CubicSpline(Year,Forcings["OECD_RA_F_waste_R1"][~np.isnan(Forcings["OECD_RA_F_waste_R1"])])
OECD_RA_F_waste_R23 = CubicSpline(Year,Forcings["OECD_RA_F_waste_R23"][~np.isnan(Forcings["OECD_RA_F_waste_R23"])])

OECD_GA_F_waste_R123 = CubicSpline(Year,Forcings["OECD_GA_F_waste_R123"][~np.isnan(Forcings["OECD_GA_F_waste_R123"])])
    
f_rec_R1  = CubicSpline(Year,Forcings["f_rec_R1"][~np.isnan(Forcings["f_rec_R1"])])
f_rec_R23 = CubicSpline(Year,Forcings["f_rec_R23"][~np.isnan(Forcings["f_rec_R23"])])

f_inc_R1  = CubicSpline(Year,Forcings["f_inc_R1"][~np.isnan(Forcings["f_inc_R1"])])
f_inc_R23 = CubicSpline(Year,Forcings["f_inc_R23"][~np.isnan(Forcings["f_inc_R23"])])

f_mism_R1  = CubicSpline(Year,Forcings["f_mism_R1"][~np.isnan(Forcings["f_mism_R1"])])
f_mism_R23 = CubicSpline(Year,Forcings["f_mism_R23"][~np.isnan(Forcings["f_mism_R23"])])

'''
import matplotlib.pyplot as plt
x = np.linspace(1950,2060, num=10000)
plt.plot(Forcings["Year"],Forcings["f_mism_R23"], 'o', label='data')
plt.plot(x,f_mism_R23(x))
plt.show()
'''

#This is the forcing class for the microplastics boxmodel. Here forcing functions on produced, wasted, discarded, incinerated, recycled plastics are saved ...
#... as well as a function describing cleanup scenarios
class boxmodel_forcings():
    
    def __init__(self, scenario_release = ("BAU"), scenario_cleanup = ("no_cleanup")):
        self.scenario_release = scenario_release
        if not self.scenario_release[0] in ["BAU","fullstop","freeze","pulse","OECD_RA","OECD_GA"]:
            raise Exception("Error. Undefined release scenario. Be sure to initiate your 'forcings' class with a valid release scenario! Typo?")
        if (self.scenario_release[0] == "OECD_RA" or self.scenario_release[0] == "OECD_GA"):
            if (self.scenario_release[1][0] < datetime.date.today().year):
                raise Exception("Error. OECD scenarios can not start in the past. Try a bigger year")
        
        self.scenario_cleanup = scenario_cleanup
        if not self.scenario_cleanup[0] in ["no_cleanup","cleanup_mismanaged_fixedfrac",
                                            "cleanup_mismanaged_linear_increment"]:
            raise Exception("Error. Undefined cleanup scenario. Be sure to initiate your 'forcings' class with a valid cleanup scenario! Typo?")
        
        if (self.scenario_cleanup[0] in["cleanup_mismanaged_fixedfrac","cleanup_mismanaged_linear_increment"]):
            if (len(self.scenario_cleanup[2]) != 9): 
                raise Exception("Error. The last argument of scenario_cleanup should contain 9 coefficients (one for each pair of Region and plastic size)")

    
#### WASTE ====================================================================    
    def get_R_F_waste(self,time):
        #base scenario
        R1_F_waste = np.where(time < 1950, 0, np.where(time >= 2120, F_waste_R1(2120), F_waste_R1(time)))
        R2_F_waste = np.where(time < 1950, 0, np.where(time >= 2115, F_waste_R2(2115), F_waste_R2(time)))
        R3_F_waste = np.where(time < 1950, 0, np.where(time >= 2120, F_waste_R3(2120), F_waste_R3(time)))
        
        if (self.scenario_release[0] == "fullstop"): #0 before 1950, then = to R_F_waste until the year specified by user, and 0 after
            R1_F_waste = np.where(time >= self.scenario_release[1], 0, R1_F_waste)
            R2_F_waste = np.where(time >= self.scenario_release[1], 0, R2_F_waste)
            R3_F_waste = np.where(time >= self.scenario_release[1], 0, R3_F_waste)
            
        if (self.scenario_release[0] == "freeze"): #0 before 1950, then = to R_F_waste until the year specified by user, and set to the same value after
            time_freeze = self.scenario_release[1]

            R1_F_waste = np.where(time >= time_freeze, F_waste_R1(time_freeze), R1_F_waste)
            R2_F_waste = np.where(time >= time_freeze, F_waste_R2(time_freeze), R2_F_waste)
            R3_F_waste = np.where(time >= time_freeze, F_waste_R3(time_freeze), R3_F_waste)
        
        if (self.scenario_release[0] == "OECD_RA"):
            R1_F_waste = np.where(time > 2060, R1_F_waste * (1 + OECD_RA_F_waste_R1(2060)),  R1_F_waste * (1 + OECD_RA_F_waste_R1(time)))
            R2_F_waste = np.where(time > 2060, R2_F_waste * (1 + OECD_RA_F_waste_R23(2060)), R2_F_waste * (1 + OECD_RA_F_waste_R23(time)))
            R3_F_waste = np.where(time > 2060, R3_F_waste * (1 + OECD_RA_F_waste_R23(2060)), R3_F_waste * (1 + OECD_RA_F_waste_R23(time)))
        
        if (self.scenario_release[0] == "OECD_GA"):
            R1_F_waste = np.where(time > 2060, R1_F_waste * (1 + OECD_GA_F_waste_R123(2060)), R1_F_waste * (1 + OECD_GA_F_waste_R123(time)))
            R2_F_waste = np.where(time > 2060, R2_F_waste * (1 + OECD_GA_F_waste_R123(2060)), R2_F_waste * (1 + OECD_GA_F_waste_R123(time)))
            R3_F_waste = np.where(time > 2060, R3_F_waste * (1 + OECD_GA_F_waste_R123(2060)), R3_F_waste * (1 + OECD_GA_F_waste_R123(time))) 
        
        return (np.array([R1_F_waste, R2_F_waste, R3_F_waste]))
    
#### RECYCLING RATES ==========================================================   
    def get_R_f_rec(self,time):
        R1 = np.where(time < 1950, 0, np.where(time > 2060, f_rec_R1(2060), f_rec_R1(time)))
        R2 = np.where(time < 1950, 0, np.where(time > 2060, f_rec_R23(2060), f_rec_R23(time)))
        R3 = R2
        
        if (self.scenario_release[0] == "freeze"): #0 before 1950, then = to R_f_rec until the year specified by user, and set to the same value after
            time_freeze = self.scenario_release[1]

            R1 = np.where(time > time_freeze, f_rec_R1(time_freeze), R1)
            R2 = np.where(time > time_freeze, f_rec_R23(time_freeze), R2)
            R3 = R2
        
        if (self.scenario_release[0] == "OECD_RA"):
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
            
            #Region 1
            R1_f_ini = f_rec_R1(t_ini) #Value of f_rec at t_ini for Region 1
            R1_f_fin = 0.40 #objective value of f_rec at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_rec_R23(t_ini) #Value of f_rec at t_ini for Region 1
            R2_f_fin = 0.20 #objective value of f_rec at t_fin for Region 1
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
            
        if (self.scenario_release[0] == "OECD_GA"):
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
            
            #Region 1
            R1_f_ini = f_rec_R1(t_ini) #Value of f_rec at t_ini for Region 1
            R1_f_fin = 0.80 #objective value of f_rec at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_rec_R23(t_ini) #Value of f_rec at t_ini for Region 2
            R2_f_fin = 0.60 #objective value of f_rec at t_fin for Region 2
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
        
        return(np.array([R1, R2, R3]))


#### INCINERATION RATES =======================================================     
    def get_R_f_inc(self,time):
        R1 = np.where(time < 1950, 0, np.where(time > 2060, f_inc_R1(2060), f_inc_R1(time)))
        R2 = np.where(time < 1950, 0, np.where(time > 2060, f_inc_R23(2060), f_inc_R23(time)))
        R3 = R2
        
        if (self.scenario_release[0] == "freeze"): #0 before 1950, then = to R_f_rec until the year specified by user, and set to the same value after
            time_freeze = self.scenario_release[1]

            R1 = np.where(time >= time_freeze, f_inc_R1(time_freeze), R1)
            R2 = np.where(time >= time_freeze, f_inc_R23(time_freeze), R2)
            R3 = R2
        
        if (self.scenario_release[0] == "OECD_RA"):
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
            
            #Region 1
            R1_f_ini = f_inc_R1(t_ini) #Value of f_inc at t_ini for Region 1
            R1_f_fin = 0.19 #objective value of f_inc at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_inc_R23(t_ini) #Value of f_rec at t_ini for Region 1
            R2_f_fin = 0.19 #objective value of f_rec at t_fin for Region 1
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
            
        if (self.scenario_release[0] == "OECD_GA"):
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
            
            #Region 1
            R1_f_ini = f_inc_R1(t_ini) #Value of f_inc at t_ini for Region 1
            R1_f_fin = 0.20 #objective value of f_inc at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_inc_R23(t_ini) #Value of f_rec at t_ini for Region 1
            R2_f_fin = 0.20 #objective value of f_rec at t_fin for Region 1
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
            
        return(np.array([R1, R2, R3]))

#### MISMANAGED FRACTION ======================================================
    def get_R_f_mism(self,time):
        R1 = np.where(time < 1950, 0, np.where(time > 2060, f_mism_R1(2060), f_mism_R1(time)))
        R2 = np.where(time < 1950, 0, np.where(time > 2060, f_mism_R23(2060), f_mism_R23(time)))
        R3 = R2
        
        if (self.scenario_release[0] == "freeze"): #0 before 1950, then = to R_f_rec until the year specified by user, and set to the same value after
            time_freeze = self.scenario_release[1]

            R1 = np.where(time >= time_freeze, f_mism_R1(time_freeze), R1)
            R2 = np.where(time >= time_freeze, f_mism_R23(time_freeze), R2)
            R3 = R2
        
        if (self.scenario_release[0] == "OECD_RA"):
    ### first approach : same as above (using OECD fig 7.9)====================
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
            
            #Region 1
            R1_f_ini = f_mism_R1(t_ini) #Value of f_inc at t_ini for Region 1
            R1_f_fin = 0.007 #objective value of f_inc at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_mism_R23(t_ini) #Value of f_rec at t_ini for Region 2&3
            R2_f_fin = 0.07 #objective value of f_rec at t_fin for Region 2&3
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
            
        if (self.scenario_release[0] == "OECD_GA"):
    ### first approach : same as above (using OECD fig 7.9)====================
            t_ini = self.scenario_release[1][0] #start of the OECD measures
            t_fin = self.scenario_release[1][1] #year goal for OECD (usualy 2060)
                
            #Region 1
            R1_f_ini = f_mism_R1(t_ini) #Value of f_inc at t_ini for Region 1
            R1_f_fin = 0.001 #objective value of f_inc at t_fin for Region 1
            slope = (R1_f_fin - R1_f_ini)/(t_fin - t_ini)
            R1 = np.where(time <= t_ini, R1, np.where(time > t_fin, (t_fin - t_ini)*slope + R1_f_ini, (time - t_ini)*slope + R1_f_ini))
            
            #Region 2
            R2_f_ini = f_mism_R23(t_ini) #Value of f_rec at t_ini for Region 1
            R2_f_fin = 0.01 #objective value of f_rec at t_fin for Region 1
            slope = (R2_f_fin - R2_f_ini)/(t_fin - t_ini)
            R2 = np.where(time <= t_ini, R2, np.where(time > t_fin, (t_fin - t_ini)*slope + R2_f_ini, (time - t_ini)*slope + R2_f_ini))
        
            #Region 3
            R3 = R2
        
        return(np.array([R1, R2, R3]))
  
    
####CLEANUP (REGIONAL) ========================================================
    def get_f_cleanUp(self,time):
        
        if (self.scenario_cleanup[0] == "no_cleanup"):
            f_P_cleanUp   = [0,0,0]
            f_LMP_cleanUp = [0,0,0]
            f_sMP_cleanUp = [0,0,0]
            
            return (np.array([f_P_cleanUp, f_LMP_cleanUp, f_sMP_cleanUp]))
        
        if (self.scenario_cleanup[0] == "cleanup_mismanaged_fixedfrac"):
            t_ini = self.scenario_cleanup[1][0] #when the cleaning starts
            t_fin = self.scenario_cleanup[1][1] #when it finishes
            slope = self.scenario_cleanup[2]
            
            f_P_cleanUp   = [0,0,0]
            f_LMP_cleanUp = [0,0,0]
            f_sMP_cleanUp = [0,0,0]
            
            f_P_cleanUp[0]   = np.where(time < t_ini, 0, np.where(time < t_fin, slope[0], 0)) #clean x% between t_ini and t_fin, than 0% after
            f_P_cleanUp[1]   = np.where(time < t_ini, 0, np.where(time < t_fin, slope[1], 0))
            f_P_cleanUp[2]   = np.where(time < t_ini, 0, np.where(time < t_fin, slope[2], 0))
            
            f_LMP_cleanUp[0] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[3], 0))
            f_LMP_cleanUp[1] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[4], 0))
            f_LMP_cleanUp[2] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[5], 0))
            
            f_sMP_cleanUp[0] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[6], 0))
            f_sMP_cleanUp[1] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[7], 0))
            f_sMP_cleanUp[2] = np.where(time < t_ini, 0, np.where(time < t_fin, slope[8], 0))
    
            return (np.array([f_P_cleanUp, f_LMP_cleanUp, f_sMP_cleanUp]))
            
        if (self.scenario_cleanup[0] == "cleanup_mismanaged_linear_increment"):
            t_ini = self.scenario_cleanup[1][0] #when the increment starts
            t_fin = self.scenario_cleanup[1][1] #when it finishes
            slope = self.scenario_cleanup[2]/(t_fin - t_ini)
            
            f_P_cleanUp   = [0,0,0]
            f_LMP_cleanUp = [0,0,0]
            f_sMP_cleanUp = [0,0,0]
            
            f_P_cleanUp[0]   = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[0], (t_fin-t_ini)*slope[0]))
            f_P_cleanUp[1]   = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[1], (t_fin-t_ini)*slope[1]))
            f_P_cleanUp[2]   = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[2], (t_fin-t_ini)*slope[2]))
            
            f_LMP_cleanUp[0] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[3], (t_fin-t_ini)*slope[3]))
            f_LMP_cleanUp[1] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[4], (t_fin-t_ini)*slope[4]))
            f_LMP_cleanUp[2] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[5], (t_fin-t_ini)*slope[5]))
            
            f_sMP_cleanUp[0] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[6], (t_fin-t_ini)*slope[6]))
            f_sMP_cleanUp[1] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[7], (t_fin-t_ini)*slope[7]))
            f_sMP_cleanUp[2] = np.where(time < t_ini, 0, np.where(time < t_fin, (time-t_ini)*slope[8], (t_fin-t_ini)*slope[8]))
    
            return (np.array([f_P_cleanUp, f_LMP_cleanUp, f_sMP_cleanUp]))