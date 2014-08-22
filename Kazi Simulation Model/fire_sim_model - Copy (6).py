from __future__ import division #Stops int / int being integer division
import math #for many functions, pi, sqrt etc.
import random #for adding variations in the amount of time events take
import simpy #for handling events and resources
import time #Time how long it took
import fbpline2 #fbp system for fire ROS calculations
from haversine import * #mathematical functions written in C
#Airtanker Simulation Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

#Please note that values of -1.0 are unchanged or erroneous values

#POINTS BROKEN *fixed

EPS = 0.000001 #Epsilon for float comparisons

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                           Read-only Variables (editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

#Location of forest cells with information such as fueltype+location for each
FOREST_DATA_LOCATION = "canadian_forest_data.txt"
#File listing the types of airtankers and the stats to use for each
AIRTANKER_DATA_LOCATION = "airtanker_data.txt"
#File listing values to use for various constants in this simulation
READ_ONLY_CONSTANTS = "read_only_constants.txt"
#sets constant values from file, if there is an error use the defaults
try:
    in_file = open(READ_ONLY_CONSTANTS, 'r')
    #File is CSV so seperate the values into a list
    values = in_file.readline().split(',')
    #radius of EARTH in km 0 < x (haversine calculations always assume 6371)
    EARTHS_RADIUS = float(values[0])
    #If false uses randomly generated forest instead of forest data file
    if values[1] == "True":
        USE_FOREST_DATA = True
    else:
        USE_FOREST_DATA = False
    #Improves calculation accuracy of determing if points are burned, but slower
    if values[2] == "True":
        IMPROVE_POINTS_BURN = True
    else:
        IMPROVE_POINTS_BURN = False
    #In the coordinate system what radian value is east 0 <= x <= 2pi
    EAST_DIRECTION = float(values[3])
    #If True, the coordinate system has counter clock wise as increasing radians
    if values[4] == "True":
        CCW_IS_POS = True
    else:
        CCW_IS_POS = False
    #percent of fire airtanker needs to control 0 <= x <= 1 
    BHE = float(values[5])
    # Time it takes for an airtanker to complete one drop of water NOT USED!!!
    DROP_TIME = float(values[6])
    #probability a lightning caused fire gets detected 0 <= x <= 1
    PROB_DETECTED_LIGHTNING = float(values[7])
    #probability a human caused fire gets detected 0 <= x <= 1
    PROB_DETECTED_HUMAN = float(values[8])
    #Number of hours in a day 0 < x
    LENGTH_DAY = float(values[9])
    #Mean time to detect a lightning caused fire in minutes 0 <= x
    DETECT_TIME_LIGHTNING = float(values[10])
    #Mean time to detect a human caused fire in minutes 0 <= x
    DETECT_TIME_HUMAN = float(values[11])
    #Mean time to report a lightning caused fire (airtanker requested this time)
    REPORT_TIME_LIGHTNING = float(values[12])
    #Mean time to report a human caused fire in minutes 0 <= x
    REPORT_TIME_HUMAN = float(values[13])
    #Constants used for fire arrival equation cause: H = human L = lightning
    #Equation is: delta_m(t) = delta_m_mean - AMP * cos(2pi * (t - LAG) / delta)
    #delta_m is fire arrival rate, delta is portion of day fires can occur
    AMP_H = float(values[14])
    LAG_H = float(values[15])
    AMP_L = float(values[16])
    LAG_L = float(values[17])
    #Estimated lake distance used by airtankers when determining if still avail
    LAKE_DIST = float(values[18])
    #Constant time before a_t end service time a_t cant be dispatched after
    AT_AVAIL_CONST = float(values[19])
    in_file.close()
except (IOError, ValueError, IndexError):
    #If there is an error in file, create a new file with default values to use
    try:
        in_file.close()
    except IOError:
        pass
    new_file = open(READ_ONLY_CONSTANTS, 'w')
    new_file.write("6371,True,True,0.0,True,0.4,1.0,0.8,0.8," +
                       "24.0,120.0,120.0,10.0,10.0")
    new_file.close()
    EARTHS_RADIUS = 6371.0 #KM
    USE_FOREST_DATA = True
    IMPROVE_POINTS_BURN = True #Better check, costs time
    EAST_DIRECTION = 0.0 #Set Default Direction in RADIANS
    CCW_IS_POS = True #Set counter-clock-wise is positive direction
    BHE = 0.4 #When airtanker covers 40% of perimeter, fire is controlled
    DROP_TIME = 1.0 #Time for one airtanker water drop (excluding travel time)
    PROB_DETECTED_LIGHTNING = 0.8 #probability lightning fire is detected
    PROB_DETECTED_HUMAN = 0.8 #probability human fire is detected
    LENGTH_DAY = 24.0 #Number of hours fires are generated for
    DETECT_TIME_LIGHTNING = 120.0 #minutes for mean
    DETECT_TIME_HUMAN = 120.0 #minutes for mean
    REPORT_TIME_LIGHTNING = 10.0 #minutes for mean
    REPORT_TIME_HUMAN = 10.0 #minutes for mean
    AMP_H = 0.2
    LAG_H = 0.0
    AMP_L = 0.2
    LAG_L = 0.0
    LAKE_DIST = 15.0
    AT_AVAIL_CONST = 30.0

def airtanker_values(airtanker_name):
    '''Open AIRTANKER_DATA_LOCATION file and find the stats for the airtanker
    input file must have a header with properly identified headers
name,cruising_airspeed,fight_airspeed,circling_speed,fly_when_dark,drop_type,
size,fuel_capacity,fuel_consumption,after_fire_protocol,initial_attack_radius,
start_time,end_time,max_flight_time,max_serv_time,drop_time'''
    in_file = open(AIRTANKER_DATA_LOCATION, 'r')
    temp = in_file.readline()
    while temp!= '' and temp.split(',')[0] != airtanker_name:
        temp = in_file.readline()
        if temp == '':
            print "Invalid airtanker name entered\n"
            raise SystemExit
    temp2 = temp.split(',')
    if temp2[-1][-1] == '\n':
        temp2[-1] = temp2[-1][:-1]
    for x in xrange(len(temp2)):
        if temp2[x] == "True":
            temp2[x] = True
        elif temp2[x] == "False":
            temp2[x] = False
        else:
            try:
                temp2[x] = float(temp2[x])
            except ValueError:
                pass
    in_file.close()
    return temp2
        

class User_input(object):
    '''Class containing the user inputted values to be used in the simulation'''
    def __init__(self, inputs):
        #Simulation

        #Number of "days" simulation repeats itself for 1 <= x (int)
        self.number_runs = inputs[0]

        #number of minutes per run (should equal length day but can be longer)
        self.length_run = inputs[1] #minutes
        #If True, shows all of the data for every fire
        #self.time_until_start = inputs[47] #~ NEED TO ADD, minutes
        #Time in day at which fires can start being ignited in minutes 0 <= x
        self.time_until_start = 60
        #Time in day when fires stop starting in minutes time_until_start < x
        self.time_until_dark = inputs[2]
        #Expected number of lightning fires per day, used to calc arrival times
        self.lightning_fires_day = inputs[3]
        #Expected number of human caused fires per day
        self.human_fires_day = inputs[4]
        #NOT CURRENTLY USED ANYWHERE
        self.check_distance = inputs[5]
        #If true, shows info about every airtanker and fire for each run
        self.show_fire_attributes = inputs[6]
        #If True save more statistics at the cost of memory (FALSE IS BETTER)
        self.save_daily_averages = inputs[7]

        #FBP Info
        #NEED TO ADD INPUT FILE FOR THIS DATA BASED ON FOREST CELL !!!
        #Values used by FBP for determing ROS of fires
        self.month = inputs[8]
        self.day = inputs[9]
        self.min_fmc_month = inputs[10]
        self.min_fmc_day = inputs[11]
        self.FFMC = inputs[12]
        self.BUI = inputs[13]
        self.wind_speed = inputs[14]
        self.wind_direction = inputs[15]
        #For M1, M2 fuel types, needs 0.0 <= PC <= 100.0
        self.PC = inputs[16]
        #For M3, M4 fuel types, needs 0.0 <= PDF <= 100.0
        self.PDF = inputs[17]
        self.GFL = inputs[18]
        self.PCUR = inputs[19]

        #Forest

        
        self.min_lat = inputs[20]
        self.max_lat = inputs[21]
        self.min_long = inputs[22]
        self.max_long = inputs[23]
        #Number of forest stands in each row
        self.num_rows = inputs[24]
        #Number of forest stands in each column
        self.num_columns = inputs[25]

        #Bases
        #Open a CSV of base information, each base should be on its own line
        #latitude,longitude,num_airtankers,airtanker_models....,
        #number_bird_dogs,bird_dog_models....
        inputs.append('')
        inputs.append('')
        inputs.append("base_location_file.txt")
        inputs.append("Airtanker_information_file.txt")
        try:
            in_file = open(inputs[46], "r")
            self.airtanker_models = []
            self.bird_dogs_models = []
            for x in range(26, 31):
                inputs[x] = []
            temp = in_file.readline()
            num_bases = 0
            while temp != '' and temp != '\n':
                if temp[-1] == '\n':
                    temp2 = temp[:-1].split(',')
                else:
                    temp2 = temp.split(',')
                num_bases += 1
                inputs[27].append(float(temp2[0]))
                inputs[28].append(float(temp2[1]))
                inputs[29].append(int(temp2[2]))
                self.airtanker_models.append(temp2[3:3+int(temp2[2])])
                inputs[30].append(float(temp2[3+int(temp2[2])]))
                if inputs[30] > 0:
                    self.bird_dogs_models.append(temp2[4+int(temp2[2]):])
                temp = in_file.readline()
            inputs[26] = num_bases
            in_file.close()
        except (IOError, ValueError, IndexError):
            pass
            
        #BELOW IS AIRTANKER+BASE INFO ONLY USED IF FILES ARE NOT PRESENT
        self.num_bases = inputs[26]
        #If len < num_bases, random number n, min_lat <= x <= max_lat
        self.bases_lat = inputs[27]
        #If len < num_bases, random number n, min_long <= x <= max_long
        self.bases_long = inputs[28]
        #list of the number of airtankers at each base
        self.base_num_airtankers = inputs[29]
        #list of the number of bird dogs at each base
        self.base_num_bird_dogs = inputs[30]
        #Cruising speed of each airtanker, km/min
        self.base_airtankers_cruising=[[inputs[31][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        #Fight fire flying speed of each airtanker km/min
        self.base_airtankers_fight = [[inputs[32][x +int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        #circling speed of each airtanker km/min
        self.base_airtankers_circling =[[inputs[33][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        #Bird dogs cruising speed km/min
        self.base_bird_dogs_cruising = [[inputs[34][x+int(sum(inputs[30][:y]))]\
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]
        #Bird dog speed when at fire km/min
        self.base_bird_dogs_fight = [[inputs[35][x +int(sum(inputs[30][:y]))] \
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]
        #Bird dogs circling speed km/min
        self.base_bird_dogs_circling = [[inputs[36][x+int(sum(inputs[30][:y]))]\
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]
        #Airtanker Fuel Capacity
        self.base_airtankers_fuel_cap =[[inputs[37][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        #Airtanker Fuel Consumption
        self.base_airtankers_fuel_con =[[inputs[38][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        #bird dogs Fuel Capacity
        self.base_bird_dogs_fuel_cap = [[inputs[39][x+int(sum(inputs[30][:y]))]\
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]
        #bird dogs Fuel Consumption
        self.base_bird_dogs_fuel_con = [[inputs[40]\
                                             [x +int(sum(inputs[30][:y]))]\
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]

        #Airtanker start times
        #CHANGE TO INPUTS[47]
        self.base_airtankers_start_time=[[inputs[37][x+int(sum(inputs[29][:y]))]
                                           for x in xrange(int(inputs[29][y]))]
                                          for y in xrange(len(inputs[29]))]

        #Airtanker End Times
        #CHANGE TO INPUTS[48]
        self.base_airtankers_end_time =[[inputs[38][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]

        try:
            self.airtanker_models = [[inputs[44][x+int(sum(inputs[29][:y]))]\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]
        except IndexError:
            self.airtanker_models = ''
            self.airtanker_models = [["C15"\
                                           for x in xrange(int(inputs[29][y]))]\
                                           for y in xrange(len(inputs[29]))]

        try:
            self.bird_dogs_models = [[inputs[45][x +int(sum(inputs[30][:y]))]\
                                           for x in xrange(int(inputs[30][y]))]\
                                           for y in xrange(len(inputs[30]))]
        except IndexError:
            self.bird_dogs_models = ''

        try:
            self.fire_location_file = inputs[49]
        except IndexError:
            self.fire_location_file = "Prediction 29 July 2014.csv"


        #Random Points


        #Number of points in forest to track
        self.num_points = inputs[41]
        #If len < num_points, random number n, min_lat <= n <= max_lat
        self.points_lat = inputs[42]
        #If len < num_points, random number n, min_long<= n <= max_long
        self.points_long = inputs[43]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                       Read-only Variables (non-editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
        self.num_stands = self.num_rows * self.num_columns #NOT USED

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Classes
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class Fire(object):
    '''Object responsible for containing all of the data on each fire'''
    def __init__(self, time_at_ignition, time_at_detection, time_at_report,  \
                 slope, time, latitude, longitude, fuel_type, detected,\
                 slope_azimult, cause, inputs, cell):
        self.time_at_ignition = time_at_ignition #Time Fire Starts
        self.time_at_detection = time_at_detection #Time Fire is Detected
        self.time_at_report = time_at_report #Time Fire is Reported
        self.slope = slope #if using forest data, used as undefined
        self.time = time #the current time used for size calculations
        self.latitude = latitude #latitude of ignition point
        self.real_lat = latitude #latitude of centre of fire (ellipse)
        self.longitude = longitude #longitude of ignition point
        self.real_long = longitude #longitude of centre of fire (ellipse)
        self.fuel_type = fuel_type #fueltype of cell ignition point is in
        self.detected = detected #True if fire is detected, else False
        self.size_at_detection = -1.0 #Area of the fire when it was detected
        self.perimeter_at_detection = -1.0 #Perimeter of the fire when detected
        self.size_at_report = -1.0 #Area of fire when reported
        self.perimeter_at_report = -1.0 #perimeter of fire when reported
        self.head_length_detect = -1.0 #length of the head when detected
        self.flank_length_detect = -1.0 #length of flank when detected
        self.back_length_detect = -1.0 #length of back when detetced
        self.head_length_report = -1.0 #length of head when reported
        self.flank_length_report = -1.0 #length of flank when reported
        self.back_length_report = -1.0 #length of tail when reported
        self.size = 0.0 #Assume fires start as points
        self.head_length = 0.0 #head length at self.time
        self.flank_length = 0.0 #flank length at self.time
        self.back_length = 0.0 #back length at self.time
        self.max_size = 0.0 #largest size of fire
        self.max_head_length = 0.0 #largest recorded head length
        self.max_flank_length = 0.0 #largest recorded flank length
        self.max_back_length = 0.0 #largest recorded back length
        self.elevation = '' #undefined - UPDATE TO USING MAP DATA FOR ELEVATION?
        self.slope_azimult = slope_azimult #undefined
        self.head_ros, self.flank_ros, self.back_ros, self.head_direction = \
                       self.get_ros(inputs)
        self.perimeter = 0.0 #perimeter at self.time
        self.max_perimeter = 0.0 #largest recorded perimeter
        self.cause = cause #if it is human or lightning caused
        self.value_at_risk = self.calc_value_risk() # Not yet implemented
        #THE NEXT FOUR HAVE NOT YET BEEN IMPLEMENTED IN ANY WAY
        self.airtankers_required = 1 # Always Assumed to be one
        self.airtankers_still_required = 1 #decrease by 1 when at arrives fire
        self.bird_dogs_required = 1#*
        priority = 1#*
        self.cell = cell #Cell in the forest fire is located in

        #airtanker values

        #list of fires sizes at each airtankers arrival
        self.size_at_airtanker_arrival = []
        #list of perimeters
        self.perimeter_at_airtanker_arrival = []
        #list of arrival times
        self.time_at_airtanker_arrival = []
        #time fire is consider controlled (airtankers are done fighting it)
        self.time_at_controlled = -1.0
        self.controlled = False


    def get_ros(self, inputs):
        '''Uses FBP to solve for the fires' rate of spread values'''
        input_list = [self.fuel_type, inputs.month, inputs.day,
                      inputs.min_fmc_month, inputs.min_fmc_day, self.latitude,
                      self.longitude, self.elevation, inputs.FFMC, inputs.BUI,
                      self.slope, self.slope_azimult, inputs.wind_speed,
                      inputs.wind_direction, inputs.PC, inputs.PDF, inputs.GFL,
                      inputs.PCUR, self.time, 1]
        output_list = fbpline2.FBP_Calculate(input_list)
        return (output_list[39] / 1000.0, output_list[45] / 1000.0,
                output_list[51] / 1000.0, output_list[19])

    def calc_value_risk(self):
        '''Calculates the value of the forest at risk by the fire'''
        #NOT YET IMPLEMENTED
        self.value_at_risk = 5
        return self.value_at_risk


    def growth(self): #assumed fires grow linearly
        if self.time < self.time_at_ignition:
            #Fire has not yet started so all values set to -1.0
            self.head_length = -1.0
            self.flank_length = -1.0
            self.back_length = -1.0
            self.perimeter = -1.0
            self.size = -1.0
        else:
            #Multiply time since ignition by ROS to get current lengths
            self.head_length = ((self.time - self.time_at_ignition) *
                                self.head_ros)
            self.flank_length = ((self.time - self.time_at_ignition) *
                               self.flank_ros)
            self.back_length = ((self.time - self.time_at_ignition) *
                                self.back_ros)
            #Use current lengths in ellipse area+perimeter formulas
            maj_axis = (self.head_length + self.back_length) / 2
            #the angle point on ellipse flank passes through makes with
            #major axis from centre of ellipse
            angle =  math.atan((2 * self.flank_length) / (self.head_length -
                                                          self.back_length))
            min_axis = minor_axis(maj_axis, angle, self.flank_length)
            self.size = area_ellipse(maj_axis, min_axis)
            self.perimeter = perimeter_ellipse(maj_axis, min_axis)

    def max_growth(self, inputs):
        '''Set time to end of run then grow fires to this time.
        This is true for all non-detected fires and non-controlled fires
        Controlled fires will have this value changed when controlled'''
        #Initally set to grow until times darkness on that day
        self.time = ((self.time_at_ignition // (LENGTH_DAY * 60.0)) *
                     (LENGTH_DAY * 60.0) + inputs.time_until_dark)
        self.growth() #call to growth method
        #save all size parameters to max size ones
        self.max_perimeter = self.perimeter
        self.max_size = self.size
        self.max_head_length = self.head_length
        self.max_flank_length = self.flank_length
        self.max_back_length = self.back_length


    def detect(self): #Updates detected and report size + radius
        '''For detected fires save their size when detected and reported'''
        #save old time to temporary variable
        temp = self.time
        #set time to current detected time , call growth() then update variables
        self.time = self.time_at_detection
        self.growth()
        self.size_at_detection = self.size
        self.perimeter_at_detection = self.perimeter
        self.head_length_detect = self.head_length
        self.flank_length_detect = self.flank_length
        self.back_length_detect = self.back_length
        #set time to current reported time , call growth() then update variables
        self.time = self.time_at_report
        self.growth()
        self.size_at_report = self.size
        self.perimeter_at_report = self.perimeter
        self.head_length_report = self.head_length
        self.flank_length_report = self.flank_length
        self.back_length_report = self.back_length
        #return time to previous value of time before this method call
        self.time = temp


    def real_centres_max(self): #Gives real elliptical centre
        '''Source: http://www.movable-type.co.uk/scripts/latlong.html
        Assumed 0 bearing is true north, increasing bearing clockwise
        Sets self.real_lat and self.real_long to coordinates of centre of
        the ellipse (other lat and long are the ignition point)'''
        #Find distance from ignition point to real centre
        dist = (self.max_head_length - self.max_back_length) / 2
##        dist = ((self.max_head_length - self.max_back_length) / 2 -
##                self.max_back_length)
        #major axis direction is the same as the head direction
        direct = to_rad(self.head_direction)
        if CCW_IS_POS: #Change to coordinates of North 0,CW pos, not from source
            direct *= -1.0
            direct += (EAST_DIRECTION + (math.pi / 2))
            while direct > 2 * math.pi:
                direct -= 2 * math.pi
            while direct < 0:
                direct += 2 * math.pi
        else:
            direct -= (math.pi / 2 - EAST_DIRECTION)
            while direct > 2 * math.pi:
                direct -= 2 * math.pi
            while direct < 0:
                direct += 2 * math.pi
        d_r = dist / EARTHS_RADIUS
        new_lat = translate_coordinate_lat(self.longitude, self.latitude,
                                           direct, d_r)
        new_long = translate_coordinate_lon(self.longitude, self.latitude,
                                           direct, d_r, new_lat)
        self.real_long = to_degrees(new_long)
        #get -360 < real_long <= 0 degrees
        while self.real_long > 0:
            self.real_long -= 360.0 #Western Hemisphere
        self.real_long = self.real_long % -360.0
        #get 0 <= real_lat < 360 degrees
        self.real_lat = to_degrees(new_lat)
        while self.real_lat < 0:
            self.real_lat += 360.0
        self.real_lat = self.real_lat % 360.0
        return

    
    def print_attributes(self): #Print all of the fire's attributes
        '''Print all of the saved details of the fire'''
        print "Time Ignited: %.2f" %self.time_at_ignition
        if self.detected:
            print "Time Detected: %.2f" %self.time_at_detection
            print "Time Reported: %.2f" %self.time_at_report
        #print "Slope: %.2f"  %self.slope
        print "Time: %.2f"  %self.time
        print "Latitude: %.2f" %self.latitude
        print "Longitude: %.2f" %self.longitude
        print "Caused by: ", self.cause
        print "Fuel Type:", self.fuel_type
        print "Fire Was Detected:", self.detected
        if self.detected:
            print "Size When Detected: %.2f"  %self.size_at_detection
            print "Perimeter When Detected: %.2f" %self.perimeter_at_detection
            print "Size When Reported: %.2f" %self.size_at_report
            print "Perimeter When Reported: %.2f" %self.perimeter_at_report
        print "Current Perimeter: %.2f" %self.perimeter
        print "Current Size: %.2f"  %self.size
        print "Largest Size: %.2f" %self.max_size
        print "Largest Perimeter: %.2f" %self.max_perimeter
        print "Head Rate of Growth %.4f" %self.head_ros
        print "Flank Rate of Growth %.4f" %self.flank_ros
        print "Back Rate of Growth %.4f" %self.back_ros
        print "Current Head Length %.4f" %self.head_length
        print "Current Flank Length %.4f" %self.flank_length
        print "Current Back Length %.4f" %self.back_length
        print "Max Head Length %.4f" %self.max_head_length
        print "Max Flank Length %.4f" %self.max_flank_length
        print "Max Back Length %.4f" %self.max_back_length
        print "Fire Was Controlled:", self.controlled
        #If multiple airtanker arrivals were set up, would show this
        for x in xrange(len(self.size_at_airtanker_arrival)):
            try:
                print "Size at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.size_at_airtanker_arrival[x])
                print "Perimeter at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.perimeter_at_airtanker_arrival[x])
                print "Time at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.time_at_airtanker_arrival[x])
            except IndexError:
                pass
        if self.controlled:
            print "Controlled at Time: %.2f" %self.time_at_controlled

class Statistics(object): #Has many useful statistics as attributes
    '''Class to store final statistics about the simulation
    If Small memory mode each list is [average_all_runs, max, min]
    Else each list holds every runs' values'''
    def __init__(self):
        self.average_max_size = []
        self.average_detection_size = []
        self.average_report_size = []
        self.average_ignition_time = [] 
        self.average_detection_time = [] #After ignition
        self.average_report_time = [] #After detection
        self.num_fires = []
        self.detection_rate = []
        self.controlled_rate = []
        self.average_cost = [] #*
        
        #Airtanker Stats
        self.average_travel_time = []
        self.average_travel_distance = []
        self.average_wait_time = []
        self.average_fight_fire_time = []
        self.average_control_time = []
    
class Airtanker(object):
    #Class storing all of the attributes about each airtanker
    def __init__(self, cruising_airspeed, fight_airspeed, circling_speed,
                 lat, lon, fly_when_dark, drop_type, size, fuel_capacity,
                 fuel_consumption, after_fire_protocol, initial_attack_radius,
                 start_time, end_time, max_flight_time, max_serv_time,
                 drop_time):
        #Speed to fly between locations, assumed infinite acceleration
        self.cruising_airspeed = cruising_airspeed 
        #Speed used to calculate time flying between fire and lake
        self.fight_airspeed = fight_airspeed
        #NOT IMPLEMENTED
        self.circling_speed = circling_speed
        #Airtankers current latitude
        self.latitude = lat
        #airtankers current longitude
        self.longitude = lon
        #Airtankers home base latitude
        self.base_lat = lat
        #Airtankers home base longitude
        self.base_long = lon
        #Amount of time it has travelled, resets on refuel?(NOT IMPLEMENTED)
        self.travel_time = 0.0
        #amount of time it has travelled in total
        self.total_travel_time = 0.0
        #distance airtanker has travelled, resets on refuel? (NOT IMPLEMENTED)
        self.travel_distance = 0.0
        #Total distance airtanker has travelled this run
        self.total_travel_distance = 0.0
        #Amount of time an airtanker is in queue for other fires
        self.total_wait_time = 0.0
        #time airtanker spends fighting fires
        self.fight_fire_time = 0.0
        #Total time airtanker spends fighting fires
        self.total_fight_fire_time = 0.0
        #Airtanker can fly after dark OLD, NOT IMPLEMENTED
        self.fly_when_dark = fly_when_dark
        #Airtanker droptype, CURRENTLY DOESNT AFFECT ANYTHING (ie. fight fire)
        self.drop_type = drop_type #3 types salvo, trail and misc
        #Airtankers size, CURRENTLY DOESNT AFFECT ANYTHING
        self.size = size #small/large
        #number representing what the airtanker does after controlling a fire
        self.after_fire_protocol = after_fire_protocol #Goes where after fire
        #NOT IMPLEMENTED
        self.fuel_capacity = fuel_capacity #cannot reach 0
        #NOT IMPLEMENTED
        self.max_fuel_cap = fuel_capacity #when refilled goes to this level
        #NOT IMPLEMENTED
        self.fuel_consumption = fuel_consumption #Some units
        #Airtanker can only fight fires within this radius of the airtanker
        self.initial_attack_radius = initial_attack_radius
        #Time in day airtanker starts service, cannot be sent to fire earlier
        self.start_time = start_time
        #Time airtanker ends service if already dispatched it finishes fire 1st
        self.end_time = end_time
        #maximum amount of time an airtanker can fly for before it cant be used
        self.max_flight_time = max_flight_time # if airtanker cannot longer
        #maximum amount of time an airtanker can service fires for 
        self.max_serv_time = max_serv_time # in a day cant serv fires longer
        #Time to drop one load of water, minutes, constant added to drop cycle
        self.drop_time = drop_time

    def calc_iar(self): #not used
        '''Return an iar for the airtanker based on its other statistics'''
        self.initial_attack_radius = 1000

    def suitable(self, fire, time, inputs):
        '''Return True if airtanker could fight fire, else return False'''
        #Determine if fire is in airtankers initial attack range from cur pos
        fire_dist = obj_distance(self, fire)
        #estimates how long it will take to fight the fire
        fight_time = 2 * get_time_per_drop (LAKE_DIST, self)
        #Extra time is estimate of total time to serve fire to check if avail
        extra_time = 1 * fire_dist / self.cruising_airspeed + fight_time
        in_range = (fire_dist - EPS) <= self.initial_attack_radius
        #Determine if past the airtankers start service time
        past_start = (time + EPS) >= self.start_time
        #Determine if now + extra time before the airtankers end of service time
        before_end = (time + extra_time + AT_AVAIL_CONST- EPS) <= self.end_time
        #check if below the max flight time excluding next fires flight time
        below_flight = (self.travel_time - EPS) <= self.max_flight_time
        #check if below max service time, exluding next fires service time
        below_serv = (self.fight_fire_time - EPS) <= self.max_serv_time
        #if need to leave time for airtanker to return to home base at end day
        if self.after_fire_protocol == 3:
            #get base distance and time to fly there
            flight_distance = distance(self.longitude, self.latitude,
                                       self.base_long, self.base_lat)
            flight_time = flight_distance / self.cruising_airspeed
            #if this makes it fly too long, it instead returns home
            if (time + flight_time + EPS) >= self.end_time:
                self.latitude = self.base_lat
                self.longitude = self.base_long
                self.travel_time += flight_time
                self.total_travel_time += flight_time
                self.travel_distance += flight_distance
                self.total_travel_distance += flight_distance
                return False
        #return if the airtanker is able to fight the fire
        is_suitable = in_range and past_start and before_end and below_flight \
                   and below_serv
        return is_suitable

    def print_attributes(self):
        '''Prints all of the airtanker information'''
        print "Cruising Airspeed: %4.2f" %self.cruising_airspeed
        print "Fight Fire Airspeed: %4.2f" %self.fight_airspeed
        print "Circling Airspeed: %4.2f" %self.circling_speed
        print "Latitude: %4.2f" %self.latitude
        print "Longitude: %4.2f" %self.longitude
        print "Home Base Longitude: %3.2f" %self.base_lat
        print "Home Base Latitude: %3.2f" %self.base_long
        print "Total Travel Time: %4.1f" %self.total_travel_time
        print "Total Travel Distance: %4.1f" %self.total_travel_distance
        print "Total Wait Time: %3.1f" %self.total_wait_time
        print "Total Fight Fire Time: %3.1f" %self.total_fight_fire_time
##        self.fly_when_dark #Not implemented
        print "Drop Type: %s" %self.drop_type
        print "Size: %s" %self.size
        prot = self.after_fire_protocol
        if prot == 0:
            prot = 'Return to Home Base'
        elif prot == 1 or prot == 3:
            prot = 'Return to Closest Base'
        elif prot == 2:
            prot = 'Next Fire if Available'
        print "After Fire Protocol: %s" %prot
        print "Fuel Capacity: %3.1f" %self.fuel_capacity
        print "Fuel Consumption Rate: %2.2f" %self.fuel_consumption
        print "Initial Attack Radius %4.2f" %self.initial_attack_radius
        print "Start Service Time: %3.1f" %self.start_time
        print "End Service Time: %3.1f" %self.end_time
        print "Max Flight Time: %3.1f" %self.max_flight_time
        print "Max Fight Fire Time: %3.1f" %self.max_serv_time

class Base(object):
    '''Class to store each bases information: location and initial aircraft'''
    def __init__(self, latitude, longitude, airtankers, airtankers_resource,\
                 bird_dogs, bird_dogs_resource):
        self.latitude = latitude #location
        self.longitude = longitude
        self.airtankers = airtankers #list of airtankers starting at base
        self.bird_dogs = bird_dogs #list of bird dogs starting at base
        self.airtankers_resource = airtankers_resource #airtankers for simpy 
        self.bird_dogs_resource = bird_dogs_resource #bird dogs for simpy

class Lake(object): #Assumed circle
    def __init__(self, latitude, longitude, suitable, radius): #NOT IMPLEMENTED
        self.latitude = latitude
        self.longitude = longitude
        self.suitable = suitable #If True, can be used by Airtankers
        self.radius = radius


class Forest_stand(object): #Records fuel type and slope of that part of forest
    '''One cell of the forest, only used if real forest data is not'''
    def __init__(self, fuel_type, slope, slope_azimult):
        self.fuel_type = fuel_type
        self.slope = slope
        self.slope_azimult = slope_azimult

class Point(object): #Points to keep track of during simulation
    '''Stores point location and a list keeping track of the days burned'''
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.burned = []

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def mean_time_between_fires(env, fires_per_day): #Use to calculate fire ign time
    '''Return mean time in minutes between fires'''
    #find the number of fires per hour by dividing by the length of a day
    fires_per_hour = fires_per_day / LENGTH_DAY
    #return the mean time between fires in minutes
    return  60.0 / fires_per_hour

def obj_distance(obj1, obj2):
    '''Uses Haversice Formula to find the distance between 2 points
    Source: http://en.wikipedia.org/wiki/Haversine_formula'''
    dist = distance(obj1.longitude, obj1.latitude, obj2.longitude,obj2.latitude)
##    if isinstance(obj1, Fire):
##        pass
##    if isinstance(obj2, Fire):
##        pass
    return dist

def generate_fueltype(): #Assumed uniform distribution of fueltypes in forest
    '''Use some probability distribution to return fueltypes
        Only used if no forest data is given'''
    fuel_types = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "D1", "M1",\
                  "M2", "M3", "M4", "O1a", "O1b", "S1", "S2", "S3"]
    return fuel_types[random.randint(0, len(fuel_types) - 1)]#some fuel type

def generate_slope(): #DOESNT CURRENTLY AFFECT ANYTHING ELSE
    '''Uses some probability distribution to generate a slope'''
    return random.uniform(0, 5)

def create_forest(inputs): #Generate forest with random stands
    '''Return a list of lists of stands that represent each row in the forest'''
##    forest = []
    if type(inputs.num_rows) != int:
        print "Please enter num_rows as an integer"
        raise SystemExit
    if type(inputs.num_columns) != int:
        print "Please enter num_columns as an integer"
        raise SystemExit
    #save matrix of forest stands to a list variable to represent the forest
    forest = [[Forest_stand(generate_fueltype(), generate_slope(),
                    random.uniform(0, 360)) for y in xrange(inputs.num_columns)]
              for x in xrange(inputs.num_rows)]
##    for x in xrange (inputs.num_rows):
##        forest.append([])
##        for y in xrange(inputs.num_columns):
##            forest[x].append(Forest_stand(generate_fueltype(),generate_slope(),
##                                          random.uniform(0, 360)))
    return forest

def get_stand_info_random(lat, lon, forest, inputs):
    '''Returns slope and fuel type and given location'''
    #find the stand in the forest containing the parameter coordinates
    lat_stand = len(forest) - int(((lat - inputs.min_lat) / \
                                   (inputs.max_lat-inputs.min_lat))*len(forest))
    if lat_stand == 0: #case where coordinates on edge of forest
        lat_stand = 1
    long_stand = len(forest[0]) - int(((lon - inputs.min_long) /\
                                       (inputs.max_long - inputs.min_long))\
                                      * len(forest[0]))
    if long_stand == 0: #case where coordinates on edge of forest
        long_stand = 1
    return forest[lat_stand - 1][long_stand - 1].fuel_type, \
        forest[lat_stand - 1][long_stand - 1].slope, \
        forest[lat_stand - 1][long_stand - 1].slope_azimult

def get_stand_info_old(lat, lon, inputs):
    '''Return fuel type and fuel percent at a coordinate location
    Using the forest_data_input_file'''
    forest_data_file = open(FOREST_DATA_LOCATION, 'r')
    #ignore header line
    temp = forest_data_file.readline()
    #Read one cells values and separate into a list
    temp = forest_data_file.readline()
    temp2 = temp.split(',')
    #cell is in list[0]
    cell = temp2[0]
    #longitude is list[2] and latitude is list[1], find distance to point
    dist = distance(lon, lat, float(temp2[2]), float(temp2[1]))
    #fuel type is list[3]
    fueltype = temp2[3]
    #Fuel percent used is list[4] NEED TO CHANGE - NOT CORRECT
    fuel_perc = float(temp2[4])
    #continue for all cells in the forest
    next_temp = forest_data_file.readline()
    while next_temp != '' and next_temp != '\n':
        temp = next_temp
        temp2 = temp.split(',')
        new_dist = distance(lon, lat, float(temp2[2]), float(temp2[1]))
        #finds cell with that is closest to the fires ignition point
        if new_dist < dist:
            dist = new_dist
            fueltype = temp2[3]
            fuel_perc = float(temp2[4])
            cell = temp2[0]
        next_temp = forest_data_file.readline()
    forest_data_file.close()
    return fueltype, fuel_perc, cell

def get_stand_info(lat, lon, inputs, cell):
    ''' Return fuel type and fuel percent at a coordinate location
        Using the forest_data_input_file formatted as:
        CELLID,LATITUDE,LONGITUDE,FBP FUELTYPE,FBP FUEL PERCENT'''
    forest_data_file = open(FOREST_DATA_LOCATION, 'r')
    #ignore header
    temp = forest_data_file.readline()
    temp = forest_data_file.readline()
    while temp != '':
        temp2 = temp.split(',')
        if temp2[0] == cell:
            forest_data_file.close()
            return temp2[3], temp2[4]
        temp = forest_data_file.readline()

def lightning_is_detected(env, inputs):
    '''Determines if lightning caused fire is detected'''
    if random.random() < PROB_DETECTED_LIGHTNING: #Chance fire is detected
        detected = True
    else:
        detected = False
    return detected

def human_is_detected(env, inputs):
    '''Determines if human caused fire is detected'''
    if random.random() < PROB_DETECTED_HUMAN: #Chance fire is detected
        detected = True
    else:
        detected = False
    return detected

def is_detected(env, inputs, cause):
    '''determines if the fire is detected or not'''
    if cause == "Lightning":
        detected = lightning_is_detected(env, inputs)
    elif cause == "Human":
        detected = human_is_detected(env, inputs)
    return detected

def lightning_detect_time(env, inputs):
    '''Return lightning caused fire detection time'''
    detect_time = random.expovariate(1.0 / DETECT_TIME_LIGHTNING)
    return detect_time

def human_detect_time(env, inputs):
    '''Return human caused fire detection_time'''
    detect_time = random.expovariate(1.0 / DETECT_TIME_HUMAN)
    return detect_time

def determine_detect_time(env, inputs, cause):
    '''determines time after ignition until fire is detected'''
    if cause == "Lightning":
        detect_time = lightning_detect_time(env, inputs)
    elif cause == "Human":
        detect_time = human_detect_time(env, inputs)
    return detect_time

def lightning_report_time(env, inputs):
    '''Return lightning caused fire report time'''
    report_time = random.expovariate(1.0 / REPORT_TIME_LIGHTNING)# 10 minute
    return report_time

def human_report_time(env, inputs):
    '''Return human caused fire report time'''
    detect_time = random.expovariate(1.0 / REPORT_TIME_HUMAN)# 10 minute detect
    return detect_time

def determine_report_time(env, inputs, cause):
    '''determines time after ignition until fire is reported'''
    if cause == "Lightning":
        report_time = lightning_report_time(env, inputs)
    elif cause == "Human":
        report_time = human_report_time(env, inputs)
    return report_time

def lightning_determine_latitude(env, inputs, fires):
    '''determines latitude for a lightning caused fire'''
    #Fires uniformly spread in forest, doesn't depend on anything else
    latitude = random.uniform(inputs.min_lat, inputs.max_lat)
    return latitude

def human_determine_latitude(env, inputs, fires):
    '''determines latitude for a human caused fire'''
    #Fires uniformly spread in forest, doesn't depend on anything else
    latitude = random.uniform(inputs.min_lat, inputs.max_lat)
    return latitude

def determine_fire_latitude(env, inputs, cause, fires):
    '''Determines latitude of new fire'''
    if cause == "Lightning":
        latitude = lightning_determine_latitude(env, inputs, fires)
    elif cause == "Human":
        latitude = human_determine_latitude(env, inputs, fires)
    return latitude

def lightning_determine_longitude(env, inputs, fires):
    '''determines longitude for a lightning caused fire'''
    #Fires uniformly spread in forest, doesn't depend on anything else
    longitude = random.uniform(inputs.min_long, inputs.max_long)
    return longitude

def human_determine_longitude(env, inputs, fires):
    '''determines longitude for a human caused fire'''
    #Fires uniformly spread in forest, doesn't depend on anything else
    longitude = random.uniform(inputs.min_long, inputs.max_long)
    return longitude

def determine_fire_longitude(env, inputs, cause, fires):
    '''Determines longitude of new fire'''
    if cause == "Lightning":
        latitude = lightning_determine_longitude(env, inputs, fires)
    elif cause == "Human":
        latitude = human_determine_longitude(env, inputs, fires)
    return latitude

def determine_fire_location_old(env, inputs, cause, fires):
    if cause == "Lightning":
        lat = determine_fire_latitude(env, inputs, cause, fires)
        lon = determine_fire_longitude(env, inputs, cause, fires)
    elif cause == "Human":
        lat = determine_fire_latitude(env, inputs, cause, fires)
        lon = determine_fire_longitude(env, inputs, cause, fires)
    return lat, lon

def get_lat_lon(lon, lat, area):
    ''' Takes cell information and returns random point from within it
        Based on Uniform distribution'''
    dist = math.sqrt(area) / 2 #get kilometre distance to edge of cell
    d_r = dist / EARTHS_RADIUS
    #Get latitude dist south of centre of cell
    min_lat = translate_coordinate_lat(lon, lat, 180.0, d_r)
    #Get latitude dist north of centre of cell
    max_lat = translate_coordinate_lat(lon, lat, 0.0, d_r)
    #Get longitude dist west of centre of cell
    min_lon = translate_coordinate_lon(lon, lat, 270.0, d_r, lat)
    #Get longitude dist east of centre of cell
    max_lon = translate_coordinate_lon(lon, lat, 90.0, d_r, lat)
    #Convert coordinates back to degrees
    min_lon = to_degrees(min_lon)
    while min_lon > 0:
        min_lon -= 360.0 #Western Hemisphere
    min_lon = min_lon % -360.0
    min_lat = to_degrees(min_lat)
    while min_lat < 0:
        min_lat += 360.0
    min_lat = min_lat % 360.0
    max_lon = to_degrees(max_lon)
    while max_lon > 0:
        max_lon -= 360.0 #Western Hemisphere
    max_lon = min_lon % -360.0
    max_lat = to_degrees(max_lat)
    while max_lat < 0:
        max_lat += 360.0
    max_lat = max_lat % 360.0
    #return uniformly distributed coordinates from this cell
    return random.uniform(min_lat, max_lat), random.uniform(min_lon, max_lon)


def determine_fire_location(env, inputs, cause, fires):
    #Open file of month's data
    in_file = open(inputs.fire_location_file, 'r')
    temp = in_file.readline()
    temp2 = temp.split(',')
    #Read lines until we reach the header of file
    while len(temp2) < 5:
        temp = in_file.readline()
        temp2 = temp.split(',')
    num_c = 0 #location of cell ID
    num_x = 1 #location of longitude
    num_y = 2 #location of latitude
    num_a = 3 #area of cell
    if cause == "Lightning":
        num_f = 4#expected cell number of fires location
    elif cause == "Human":
        num_f = 5#expected cell number of fires location
    #Checks header for location of each value
    for x in xrange(len(temp2)):
        if temp2[x] == "INDEXVAL" or temp2[x] == "CELLID":
            num_c = x
            continue
        if temp2[x] == "X_COORD" or temp2[x] == "LONGITUDE":
            num_x = x
            continue
        if temp2[x] == "Y_COORD" or temp2[x] == "LATITUDE":
            num_y = x
            continue
        if "AREA" in temp2[x]:
            num_a = x
            continue
        if temp2[x] == "FPP" and cause == "Human":
            num_f = x
            continue
        if temp2[x] == "HoLtg" and cause == "Lightning":
            num_f = x
    fire_sum = 0.0
    temp = in_file.readline()
    temp2 = temp.split(',')
    #Find the maximum value in the holdover/human fire column
    while temp != '':
        try:
            fire_sum += float(temp2[num_f])
        except (IndexError, ValueError):
            pass
        temp = in_file.readline()
        temp2 = temp.split(',')
    #Return start of file so we can loop through it again
    in_file.seek(0)
    #value will represent current "depth" into file
    value = 0.0
    #exp_val is 0-100% the fire_sum value when value > exp_val we have location
    exp_val = random.random() * fire_sum
    temp = in_file.readline()
    while temp != '':
        temp2 = temp.split(',')
        try:
            value += float(temp2[num_f])
        except (IndexError, ValueError):
            pass
        #found the cell location
        if value >= exp_val:
            area = float(temp2[num_a])
            #From grids location of center & size, get random uniformly dist loc
            lat, lon = get_lat_lon(float(temp2[num_x]),
                                   float(temp2[num_y]), area)
            in_file.close()
            return lat, lon, temp2[num_c]
        temp = in_file.readline()

def create_fire(env, fires, forest, inputs, cause):
    '''Randomly generates a fire and appends it to parameter fires'''
    #Function called at simulation time fire is ignited at
    ig_time = env.now
    #If fire is detected assign it a detect time and report time
    if is_detected(env, inputs, cause):
        detected = True
        #detect time = time it took to detect the fire + fire's ignition time
        detect_time = determine_detect_time(env, inputs, cause) + ig_time
        #report time = time it took to report the fire + fire's detection time
        report_time = determine_report_time(env, inputs, cause) + detect_time
    else:
        detect_time = -1.0
        detected = False
        report_time = -1.0
    #get fires location
    lat, lon, cell= determine_fire_location(env, inputs, cause, fires)
    #If no input forest data file is given generate random forest
    if not USE_FOREST_DATA:
        fuel_type, slope, slope_azimult = get_stand_info_random(lat, lon,
                                                                forest, inputs)
        fuel_perc = ''
        cell = None
    #use forest data
    else:
        fuel_type, fuel_perc = get_stand_info(lat, lon, inputs, cell)
        slope = ''
        slope_azimult = ''
    #add Fire instance of this fire to the list of fires
    fires.append(Fire(ig_time, detect_time, report_time, slope, env.now, \
                      lat, lon, fuel_type, detected, slope_azimult, cause,
                      inputs, cell))
    #If fire is detected, save its sizes at detection and report times
    if fires[-1].detected:
        fires[-1].detect()
    #assume fire will grow until end of
    fires[-1].max_growth(inputs)

def determine_points_latitude(inputs, points, point_num):
    '''Return latitude for the point'''
    #If no point latitude given one randomly generated from uniform prob dist
    try:
        lat = inputs.points_lat[point_num]
    except IndexError:
        lat = random.uniform(inputs.min_lat, inputs.max_lat)
    return lat

def determine_points_longitude(inputs, points, point_num):
    '''Return longitude for the point'''
    #if no point longitude given one randomly generated from uniform prob dist
    try:
        lon = inputs.points_long[point_num]
    except IndexError:
        lon = random.uniform(inputs.min_long, inputs.max_long)
    return lon

def create_points(inputs):
    '''Return a list of points in the forest to track'''
    points = []
    for x in xrange(inputs.num_points):
        lat = determine_points_latitude(inputs, points, x)
        lon = determine_points_longitude(inputs, points, x)
        points.append(Point(lat, lon))
    #Return list of instances of the point class each representing a point
    return points

#~~~~~~~~Functions Getting Airtanker Statistics~~~~~~~~

def determine_at_cruising(base_num, env, inputs, at_num):
    '''Return the airtankers cruising speed'''
    #speed used for all travelling assumed to accelerate to this speed instantly
    cruising = float(inputs.base_airtankers_cruising[base_num][at_num])
    return cruising

def determine_at_fight(base_num, env, inputs, at_num):
    '''Return the airtankers fight fire speed'''
    #speed used to fly to and from lake when fighting a fire
    fight = float(inputs.base_airtankers_fight[base_num][at_num])
    return fight

def determine_at_circling(base_num, env, inputs, at_num):
    '''Return the airtankers circling speed'''
    #Airtanker circling speed, not currently implemented
    circling = float(inputs.base_airtankers_circling[base_num][at_num])
    return circling

def determine_at_latitude(base_num, env, inputs, at_num):
    '''Return the airtankers latitude'''
    #originally is set to home base's latitude
    latitude = float(inputs.bases_lat[base_num])
    return latitude

def determine_at_longitude(base_num, env, inputs, at_num):
    '''Return the airtankers longitude'''
    #originally set to home base's longitude
    fight = float(inputs.bases_long[base_num])
    return fight

def determine_at_fly_dark(base_num, env, inputs, at_num):
    '''Return if airtankter can fly after dark'''
    #Not implemented - probably redundent since airtankers have end times now
    return False

def determine_at_drop_type(base_num, env, inputs, at_num):
    '''Return droptype of airtanker: salvo, trail or other'''
    #Not currently used for anything
    #Could be used to affect number of drops needed to fight a fire
    return "salvo"

def determine_at_size(base_num, env, inputs, at_num):
    '''Return size of the airtanker: small or large'''
    #Doesnt currently affect anything
    return "small"

def determine_at_after_fire_prot(base_num, env, inputs, at_num):
    ''' Return 0 for return to home base
        Return 1 return closest base
        Return 2 go to next fire if available else go to home base
        Return 3 return to closest base, but fly to home base at end of day'''
    #After fighting a fire, controls what the airtanker will do
    return random.randint(0, 3)

def determine_at_fuel_cap(base_num, env, inputs, at_num):
    '''Return the airtankers fuel capacity'''
    #Not currently used for anthing
    fuel_cap = float(inputs.base_airtankers_fuel_cap[base_num][at_num])
    return fuel_cap

def determine_at_fuel_con(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    #not currently used for anything
    fuel_con = float(inputs.base_airtankers_fuel_con[base_num][at_num])
    return fuel_con

def determine_iar(base_num, env, inputs, at_num):
    '''Return the airtankers initial attack radius'''
    #airtanker can only fight fires within this distance of its current location
    return 2000

def determine_at_start_time(base_num, env, inputs, at_num):
    '''Return Airtanker Start Time'''
    #Before this time of day airtankers can not be dispatched
##    start_time = float(inputs.base_airtankers_start_time[base_num][at_num])
    start_time = 0
    return start_time

def determine_at_end_time(base_num, env, inputs, at_num):
    '''Return Airtanker End Time'''
    #After this time airtankers cannot START service (can still finish services)
##    end_time = float(inputs.base_airtankers_end_time[base_num][at_num])
    end_time = 1550
    return end_time

def determine_at_max_flight(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    #airtankers cannot start service if their flight time exceeds this
##    max_flight_time = float(inputs.base_airtankers_max_flight[base_num][at_num])
    max_flight_time = 200 #temp
    return max_flight_time

def determine_at_max_serv(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    #airtankers cannot start service if their service time exceeds this
##    max_serv_time = float(inputs.base_airtankers_max_serv[base_num][at_num])
    max_serv_time = 200
    return max_serv_time

def determine_at_drop_time(base_num, env, inputs, at_num):
    '''Constant time added to each drop'''
    #constant time added to each drop cycle
    return 1

def get_airtanker_stats(base_num, env, inputs, at_num):
    '''Return stats for the given airtanker'''
    #Call all of the functions to get airtanker stats
    try:
        lat = determine_at_latitude(base_num, env, inputs, at_num)
        lon = determine_at_longitude(base_num, env, inputs, at_num)
        #if there is a file with the airtanker stats for models use that instead
        if inputs.airtanker_models != '':
            stats = airtanker_values(inputs.airtanker_models[base_num][at_num])
            return stats[1:4] + [lat, lon] + stats[4:]
        #else call functions for all stats
        cruising = determine_at_cruising(base_num, env, inputs, at_num)
        fight = determine_at_fight(base_num, env, inputs, at_num)
        circling = determine_at_circling(base_num, env, inputs, at_num)
        ###CHANGE THESE###
        fly_after_dark = determine_at_fly_dark(base_num, env, inputs, at_num)
        drop_type = determine_at_drop_type(base_num, env, inputs, at_num)
        size = determine_at_size(base_num, env, inputs, at_num)
        ###CHANGE THESE###
        after_fire_prot = determine_at_after_fire_prot(base_num, env, inputs,
                                                       at_num)
        fuel_cap = determine_at_fuel_cap(base_num, env, inputs, at_num)
        fuel_con = determine_at_fuel_con(base_num, env, inputs, at_num)
        initial_attack_radius = determine_iar(base_num, env, inputs, at_num)
        start_time = determine_at_start_time(base_num, env, inputs, at_num)
        end_time = determine_at_end_time(base_num, env, inputs, at_num)
        max_flight_time = determine_at_max_flight(base_num, env, inputs, at_num)
        max_serv_time = determine_at_max_serv(base_num, env, inputs, at_num)
        drop_time = determine_at_drop_time(base_num, env, inputs, at_num)
        return (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot,
                initial_attack_radius, start_time, end_time, max_flight_time,
                max_serv_time, drop_time)
    except IndexError:
        print "Not enough airtanker data entered"
        raise SystemExit
    except ValueError:
        print "Invalid airtanker values entered"
        raise SystemExit

def create_airtankers(base_num, env, inputs):
    '''Return a list of Airtanker objects'''
    #Create a list of stats for the base's airtankers, and simpy resources
    airtankers = []
    airtankers_resource =[]
    try:
        num = int(inputs.base_num_airtankers[base_num])
    except (IndexError, ValueError):
        print "Invalid number of airtankers entered"
        raise SystemExit
    for x in xrange (num):
        #set all of the stats to variables
        (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot,
         initial_attack_radius, start_time, end_time, max_flight_time,
         max_serv_time, drop_time) = get_airtanker_stats(base_num,env,inputs,x)
        #Create instance of airtanker class and save it to list
        airtankers.append(Airtanker(cruising, fight, circling, lat, lon,
                                    fly_after_dark, drop_type, size, fuel_cap,
                                    fuel_con, after_fire_prot,
                                    initial_attack_radius, start_time, end_time,
                                    max_flight_time, max_serv_time, drop_time))
        #create airtanker resource representing this same airtanker for simpy
        airtankers_resource.append(simpy.Resource(env, capacity=1))
    #return the bases airtanker and airtanker resource lists
    return airtankers, airtankers_resource

#~~~~~~~~Functions getting all of the Bird Dog Stats
#Bird dogs use the same class as airtankers
#Bird dogs are not yet implemented in any way

def determine_bd_cruising(base_num, env, inputs, bd_num):
    '''Return the bird dogs cruising speed'''
    #main flight sleep
    cruising = float(inputs.base_bird_dogs_cruising[base_num][bd_num])
    return cruising

def determine_bd_fight(base_num, env, inputs, bd_num):
    '''Return the bird dogs fight fire speed'''
    #Speed of bird dogs when at fire
    fight = float(inputs.base_bird_dogs_fight[base_num][bd_num])
    return fight

def determine_bd_circling(base_num, env, inputs, bd_num):
    '''Return the bird dogs circling speed'''
    #Not important
    circling = float(inputs.base_bird_dogs_circling[base_num][bd_num])
    return circling

def determine_bd_latitude(base_num, env, inputs, bd_num):
    '''Return the bird dogs latitude'''
    #Set to home base's latitude
    latitude = float(inputs.bases_lat[base_num])
    return latitude

def determine_bd_longitude(base_num, env, inputs, bd_num):
    '''Return the bird dogs longitude'''
    #set to home base's longitude
    fight = float(inputs.bases_long[base_num])
    return fight

def determine_bd_fly_dark(base_num, env, inputs, bd_num):
    '''Return if bird dogs can fly after dark'''
    #unnecessary 
    return False

def determine_bd_drop_type(base_num, env, inputs, bd_num):
    '''Return droptype of bird dog: salvo, trail or other'''
    #unnecessary
    return None

def determine_bd_size(base_num, env, inputs, bd_num):
    '''Return size of the bird dog: small or large'''
    #probably unnecessary
    return "small"

def determine_bd_after_fire_prot(base_num, env, inputs, bd_num):
    '''Return 0 for return to home base, 1 return closest base, 2 stay fire'''
    return 2

def determine_bd_fuel_cap(base_num, env, inputs, bd_num):
    '''Return the bird dogs fuel capacity'''
    fuel_cap = float(inputs.base_bird_dogs_fuel_cap[base_num][bd_num])
    return fuel_cap

def determine_bd_fuel_con(base_num, env, inputs, bd_num):
    '''Return the bird dogs fuel consumption'''
    fuel_con = float(inputs.base_bird_dogs_fuel_con[base_num][bd_num])
    return fuel_con

def determine_bd_iar(base_num, env, inputs, bd_num):
    '''Bird Dog's initial attack radius (km)'''
    return 1500

def determine_bd_start_time(base_num, env, inputs, bd_num):
    '''Return bird dog start service time'''
    #Cannot start service before this time
    start_time = float(inputs.base_bird_dogs_start_time[base_num][bd_num])
    return start_time


def determine_bd_end_time(base_num, env, inputs, bd_num):
    '''Return bird dog end of service time'''
    #cannot start service after this time
    end_time = float(inputs.base_bird_dogs_end_time[base_num][bd_num])
    return end_time

def determine_bd_max_flight(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    #cannot start service if flight time exceeds this value
##    max_flight_time = float(inputs.base_bird_dogs_max_flight[base_num][at_num])
    max_flight_time = 200 #temp
    return max_flight_time

def determine_bd_max_serv(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    #Cannot start service if servicing time exceeds this
##    max_serv_time = float(inputs.base_bird_dogs_max_serv[base_num][at_num])
    max_serv_time = 200
    return max_serv_time

def get_bird_dogs_stats(base_num, env, inputs, bd_num):
    '''Return stats for the given bird dog'''
    try:
        lat = determine_bd_latitude(base_num, env, inputs, bd_num)
        lon = determine_bd_longitude(base_num, env, inputs, bd_num)
        #If bird dog data is in input file get it from there
        if inputs.bird_dogs_models != '':
            stats = airtanker_values(inputs.bird_dogs_models[base_num][bd_num])
            return stats[:3] + [lat, lon], + stats[3:]
        #otherwise call the functions
        cruising = determine_bd_cruising(base_num, env, inputs, bd_num)
        fight = determine_bd_fight(base_num, env, inputs, bd_num)
        circling = determine_bd_circling(base_num, env, inputs, bd_num)
        ###CHANGE THESE###
        fly_after_dark = determine_bd_fly_dark(base_num, env, inputs, bd_num)
        drop_type = determine_bd_drop_type(base_num, env, inputs, bd_num)
        size = determine_bd_size(base_num, env, inputs, bd_num)
        after_fire_prot = determine_bd_after_fire_prot(base_num, env, inputs,
                                                       bd_num)
        ###CHANGE THESE###
        fuel_cap = determine_bd_fuel_cap(base_num, env, inputs, bd_num)
        fuel_con = determine_bd_fuel_con(base_num, env, inputs, bd_num)
        iar = determine_bd_iar(base_num, env, inputs, bd_num)
        start_time = determine_bd_start_time(base_num, env, inputs, bd_num)
        end_time = determine_bd_end_time(base_num, env, inputs, bd_num)
        max_flight_time = determine_bd_max_flight(base_num, env, inputs, at_num)
        max_serv_time = determine_bd_max_serv(base_num, env, inputs, at_num)
        return (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot, iar,
                start_time, end_time, max_flight_time, max_serv_time, None)
    except IndexError:
        print "Not enough bird dog data entered"
        raise SystemExit
    except ValueError:
        print "Invalid bird dog values entered"
        raise SystemExit

def create_bird_dogs(base_num, env, inputs):
    '''Return a list of bird dogs as Airtanker objects'''
    #Create a list of bird dog stats and one for resources for use by simpy
    bird_dogs = []
    bird_dogs_resource = []
    try:
        num = int(inputs.base_num_bird_dogs[base_num])
    except (IndexError, ValueError):
        print "Invalid number of bird dogs entered"
        raise SystemExit
    for x in xrange(num):
        #get stats for bird dog from get_bird_dogs_stats function call
        (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot, iar, 
         start_time, end_time, max_flight_time, max_serv_time, drop_time) = \
         get_bird_dogs_stats(base_num, env, inputs, x)
        #create bird dog instance of airtanker class and add to list
        bird_dogs.append(Airtanker(cruising, fight, circling, lat, lon,
                            fly_after_dark, drop_type, size, fuel_cap, fuel_con,
                            after_fire_prot, iar, start_time, end_time,
                            max_flight_time, max_serv_time, drop_time))
        #add a bird dog resource to the list
        bird_dogs_resource.append(simpy.Resource(env, capacity=1))
    return bird_dogs, bird_dogs_resource

def get_base_stats(env, inputs, base_num):
    '''Return the stats for each base'''
    #Currently just gets the bases location based on user-input
    try:
        lat = inputs.bases_lat[base_num]
    except IndexError:
        print "\nNot enough base latitudes entered\n"
        raise SystemExit
    try:
        lon = inputs.bases_long[base_num]
    except IndexError:
        print "\nNot enough base longitudes entered\n"
        raise SystemExit
    return lat, lon
    
        
def create_bases(env, inputs):
    '''Return a list of bases in the forest'''
    #Create list to hold the instances of Base class
    bases = []
    if type(inputs.num_bases) != int:
        try:
            inputs.num_bases = int(inputs.num_bases)
        except ValueError:
            print "Invalid number of bases value entered"
            raise SystemExit
    for x in xrange(inputs.num_bases):
        #Get base location
        lat, lon = get_base_stats(env, inputs, x)
        #Add lists of airtankers and their resources
        airtankers, airtankers_resource = create_airtankers(x, env, inputs)
        #Add lists of birg_dogs and their resources
        bird_dogs, bird_dogs_resource = create_bird_dogs(x, env, inputs)
        #Add instance of Base class to the list
        bases.append(Base(lat, lon, airtankers, airtankers_resource, \
                     bird_dogs, bird_dogs_resource))
    return bases

def update_statistics(stats, fires, bases, points, inputs): #add base stats
    '''Add fires statistics to stats variable'''
    #For current statistics use of this function is not worthwhile
    
    #if no fires on the day, there are no statistics to update
    if len(fires) == 0:
        stats.num_fires.append(0)
        return
    max_size = 0.0 #set all values to start at 0
    detection_size = 0.0
    report_size = 0.0
    ignition_time = 0.0
    detection_time = 0.0 #After ignition
    report_time = 0.0 #After detection
    detection_rate = 0.0
    travel_time = 0.0
    travel_distance = 0.0
    wait_time = 0.0
    control_time = 0.0
    fight_fire_time = 0.0
    controlled_rate = 0.0
    for x in xrange(len(fires)): #Increase each value by the amount for a fire
        max_size += fires[x].max_size
        if fires[x].detected: #Don't add the -1.0 placeholder
            detection_size += fires[x].size_at_detection
            report_size += fires[x].size_at_report
        days_passed = fires[x].time_at_ignition // (LENGTH_DAY * 60.0)
        cur_fire_ig_time = (fires[x].time_at_ignition -
                            (days_passed * LENGTH_DAY * 60.0))
        #Compare first fire to time fires can start occuring at
        if x == 0:
            ignition_time += cur_fire_ig_time - inputs.time_until_start
        else:
            #If previous fire occured on same time ig time is difference
            if days_passed == fires[x-1].time_at_ignition //(LENGTH_DAY * 60.0):
                ignition_time += (fires[x].time_at_ignition - \
                             fires[x-1].time_at_ignition) #time since prev fire
            #else ignition time is the time since fires could start occuring
            else:
                ignition_time += cur_fire_ig_time - inputs.time_until_start
        if fires[x].detected:
            detection_time += (fires[x].time_at_detection - \
                          fires[x].time_at_ignition)
            report_time += (fires[x].time_at_report - \
                            fires[x].time_at_detection)
            detection_rate += 1.0
        if fires[x].controlled:
            controlled_rate += 1.0
            #Time since airtanker was requested until it was controlled
            control_time += (fires[x].time_at_controlled - \
                             fires[x].time_at_report)
    #To get averages divide these values by the number of fires
    num_fires = len(fires)
    max_size = max_size / num_fires #Find average by dividing by num of fires
    ignition_time = ignition_time / num_fires
    try:
        #detection rate currently set to number of fires detected (not rate yet)
        detection_time = detection_time / detection_rate
        report_time = report_time / detection_rate
        detection_size = detection_size / detection_rate
        report_size = report_size / detection_rate
    except ZeroDivisionError: #No detected fires this day...set to 0?
        detection_time = 0.0
        report_time = 0.0
        detection_size = 0.0
        report_size = 0.0
    #change rates to probability a fire is detected/controlled here
    detection_rate = detection_rate / num_fires
    controlled_rate = controlled_rate / num_fires
    if controlled_rate != 0:
        control_time = control_time / (controlled_rate * num_fires)
    else:
        #If no fires were controlled, control time set to 0
        control_time = 0
    #Calculate airtanker stats

    #Count keeps track of the total number of airtankers
    count = 0
    #Sum some values from all of the airtankers from every base
    for x in xrange(len(bases)):
        for y in xrange(len(bases[x].airtankers)):
            travel_distance += bases[x].airtankers[y].total_travel_distance
            travel_time += bases[x].airtankers[y].total_travel_time
            wait_time += bases[x].airtankers[y].total_wait_time
            fight_fire_time += bases[x].airtankers[y].total_fight_fire_time
            count += 1
    try:
        #Find airtanker average by dividing each sum by number of airtankers
        travel_distance = travel_distance / count
        travel_time = travel_time / count
        wait_time = wait_time / count
        fight_fire_time = fight_fire_time / count
    except ZeroDivisionError: #No airtankers in this simulation
        travel_distance = 0.0
        travel_time = 0.0
        wait_time = 0.0
        fight_fire_time = 0.0
    #Update stats variable by appending to stats variable
    try:
        #Get average wait_time for each detected fire
        wait_time = wait_time / (detection_rate * num_fires)
    except ZeroDivisionError:
        wait_time = 0
    #Append all of the runs statistics to the stats variable
    stats.average_max_size.append(max_size)
    stats.average_detection_size.append(detection_size)
    stats.average_report_size.append(report_size)
    stats.average_ignition_time.append(ignition_time)
    stats.average_detection_time.append(detection_time)
    stats.average_report_time.append(report_time)
    stats.num_fires.append(num_fires)
    stats.detection_rate.append(detection_rate)
    stats.controlled_rate.append(controlled_rate)
    stats.average_travel_time.append(travel_time)
    stats.average_travel_distance.append(travel_distance)
    stats.average_wait_time.append(wait_time)
    stats.average_control_time.append(control_time)
    stats.average_fight_fire_time.append(fight_fire_time)
    #Update the points in the forest to check if they were burned on this run
    update_points(fires, points)

def update_statistics_small(stats, fires, bases, points, inputs):
    #Less memory intesive version of previous function
    #Currently gives same results, but since this removes data
    #This option could potentially do less statistical analysis
    #However presently this option should always be used
    '''Add fires statistics to stats variable'''
    num_fires = len(fires)
    #No fires so nothing to update stats with
    if num_fires == 0:
        try:
            stats.num_fires[2] = 0
        except IndexError:
            stats.num_fires += [-1, 0]
        return
    max_size = 0.0 #set all values to start at 0
    detection_size = 0.0
    report_size = 0.0
    ignition_time = 0.0
    detection_time = 0.0 #After ignition
    report_time = 0.0 #After detection
    detection_rate = 0.0
    travel_time = 0.0
    travel_distance = 0.0
    wait_time = 0.0
    control_time = 0.0
    fight_fire_time = 0.0
    controlled_rate = 0.0
    for x in xrange(num_fires): #Increase each value by the amount for a fire
        max_size += fires[x].max_size
        if fires[x].detected: #Don't add the -1.0 placeholder
            detection_size += fires[x].size_at_detection
            report_size += fires[x].size_at_report
        days_passed = fires[x].time_at_ignition // (LENGTH_DAY * 60.0)
        cur_fire_ig_time = (fires[x].time_at_ignition -
                            days_passed * (LENGTH_DAY * 60.0))
        #Compare first fire to time fires can start occuring at
        if x == 0:
            ignition_time += cur_fire_ig_time - inputs.time_until_start
        else:
            #If previous fire occured on same time ig time is difference
            if days_passed == fires[x-1].time_at_ignition //(LENGTH_DAY * 60.0):
                ignition_time += (fires[x].time_at_ignition - \
                             fires[x-1].time_at_ignition) #time since prev fire
            #else ignition time is the time since fires could start occuring
            else:
                ignition_time += cur_fire_ig_time - inputs.time_until_start
        if fires[x].detected:
            detection_time += (fires[x].time_at_detection - \
                          fires[x].time_at_ignition)
            report_time += (fires[x].time_at_report - \
                            fires[x].time_at_detection)
            detection_rate += 1.0
        if fires[x].controlled:
            controlled_rate += 1.0
            control_time += (fires[x].time_at_controlled - \
                             fires[x].time_at_report)
    max_size = max_size / num_fires #Find average by dividing by num of fires
    ignition_time = ignition_time / num_fires
    try:
        detection_time = detection_time / detection_rate
        report_time = report_time / detection_rate
        detection_size = detection_size / detection_rate
        report_size = report_size / detection_rate
    #No fires detected, so set to 0.0
    except ZeroDivisionError:
        detection_time = 0.0
        report_time = 0.0
        detection_size = 0.0
        report_size = 0.0
    #Make rate variables equal the probability for the day
    detection_rate = detection_rate / num_fires
    controlled_rate = controlled_rate / num_fires
    if controlled_rate != 0:
        control_time = control_time / (controlled_rate * num_fires)
    #No fires were controlled so set control_time to 0.0
    else:
        control_time = 0.0
    #Calculate airtanker stats

    #Count is total number of airtankers
    count = 0
    for x in xrange(len(bases)):
        for y in xrange(len(bases[x].airtankers)):
            travel_distance += bases[x].airtankers[y].total_travel_distance
            travel_time += bases[x].airtankers[y].total_travel_time
            wait_time += bases[x].airtankers[y].total_wait_time
            fight_fire_time += bases[x].airtankers[y].total_fight_fire_time
            count += 1
    try:
        travel_distance = travel_distance / count #Find average 
        travel_time = travel_time / count
        wait_time = wait_time / count
        fight_fire_time = fight_fire_time / count
    except ZeroDivisionError:
        pass
    #First Pass Through Set to Zeros
    if stats.average_max_size == []: 
        stats.average_max_size.append(0.0)
        stats.average_detection_size.append(0.0)
        stats.average_report_size.append(0.0)
        stats.average_ignition_time.append(0.0)
        stats.average_detection_time.append(0.0)
        stats.average_report_time.append(0.0)
        stats.num_fires.append(0.0)
        stats.detection_rate.append(0.0)
        stats.controlled_rate.append(0.0)
        stats.average_travel_time.append(0.0)
        stats.average_travel_distance.append(0.0)
        stats.average_wait_time.append(0.0)
        stats.average_control_time.append(0.0)
        stats.average_fight_fire_time.append(0.0)
        #Set Max Then Min
        for x in xrange (2):
            stats.average_max_size.append(-1.0)
            stats.average_detection_size.append(-1.0)
            stats.average_report_size.append(-1.0)
            stats.average_ignition_time.append(-1.0)
            stats.average_detection_time.append(-1.0)
            stats.average_report_time.append(-1.0)
            stats.num_fires.append(-1.0)
            stats.detection_rate.append(-1.0)
            stats.controlled_rate.append(-1.0)
            stats.average_travel_time.append(-1.0)
            stats.average_travel_distance.append(-1.0)
            stats.average_wait_time.append(-1.0)
            stats.average_control_time.append(-1.0)
            stats.average_fight_fire_time.append(-1.0)
    
    #Update stats variable by appending to stats variable

    #list[0] is average over all runs
    #list[1] is the maximum value from a run
    #list[2] is the minimum value from a run
    if max_size < 0:
        max_size = 0
    stats.average_max_size[0] += max_size
    if max_size > stats.average_max_size[1] or stats.average_max_size[1] == -1:
        stats.average_max_size[1] = max_size
    if max_size < stats.average_max_size[2] or stats.average_max_size[2] == -1:
        stats.average_max_size[2] = max_size
    if detection_size < 0:
        detection_size = 0
    stats.average_detection_size[0] += detection_size
    if detection_size > stats.average_detection_size[1] or \
       stats.average_detection_size[1] == -1:
        stats.average_detection_size[1] = detection_size
    if detection_size < stats.average_detection_size[2] or \
       stats.average_detection_size[2] == -1:
        stats.average_detection_size[2] = detection_size
    if report_size < 0:
        report_size = 0
    stats.average_report_size[0] += report_size
    if report_size > stats.average_report_size[1] or \
       stats.average_report_size[1] == -1:
        stats.average_report_size[1] = report_size
    if report_size < stats.average_report_size[2] or \
       stats.average_report_size[2] == -1:
        stats.average_report_size[2] = report_size
    stats.average_ignition_time[0] += ignition_time
    if ignition_time > stats.average_ignition_time[1] or \
       stats.average_ignition_time[1] == -1:
        stats.average_ignition_time[1] = ignition_time
    if ignition_time < stats.average_ignition_time[2] or \
       stats.average_ignition_time[2] == -1:
        stats.average_ignition_time[2] = ignition_time
    stats.average_detection_time[0] += detection_time
    if detection_time > stats.average_detection_time[1] or \
       stats.average_detection_time[1] == -1:
        stats.average_detection_time[1] = detection_time
    if detection_time < stats.average_detection_time[2] or \
       stats.average_detection_time[2] == -1:
        stats.average_detection_time[2] = detection_time
    stats.average_report_time[0] += report_time
    if report_time > stats.average_report_time[1] or \
       stats.average_report_time[1] == -1:
        stats.average_report_time[1] = report_time
    if report_time < stats.average_report_time[2] or \
       stats.average_report_time[2] == -1:
        stats.average_report_time[2] = report_time
    stats.num_fires[0] += num_fires
    if num_fires > stats.num_fires[1] or stats.num_fires[1] == -1:
        stats.num_fires[1] = num_fires
    if num_fires < stats.num_fires[2] or stats.num_fires[2] == -1:
        stats.num_fires[2] = num_fires
    stats.detection_rate[0] += detection_rate
    if detection_rate > stats.detection_rate[1] or stats.detection_rate[1]== -1:
        stats.detection_rate[1] = detection_rate
    if detection_rate < stats.detection_rate[2] or stats.detection_rate[2]== -1:
        stats.detection_rate[2] = detection_rate
    stats.controlled_rate[0] += controlled_rate
    if controlled_rate>stats.controlled_rate[1] or stats.controlled_rate[1]==-1:
        stats.controlled_rate[1] = controlled_rate
    if controlled_rate<stats.controlled_rate[2] or stats.controlled_rate[2]==-1:
        stats.controlled_rate[2] = controlled_rate

    #Airtanker Stats
        
    stats.average_travel_time[0] += travel_time
    if travel_time > stats.average_travel_time[1] or \
       stats.average_travel_time[1] == -1:
        stats.average_travel_time[1] = travel_time
    if travel_time < stats.average_travel_time[2] or \
       stats.average_travel_time[2] == -1:
        stats.average_travel_time[2] = travel_time
    stats.average_travel_distance[0] += travel_distance
    if travel_distance > stats.average_travel_distance[1] or \
       stats.average_travel_distance[1] == -1:
        stats.average_travel_distance[1] = travel_distance
    if travel_distance < stats.average_travel_distance[2] or \
       stats.average_travel_distance[2] == -1:
        stats.average_travel_distance[2] = travel_distance
    #Save average detected fires wait time in queue to temp1
    try:
        temp1 = (wait_time / (detection_rate * num_fires))
    except ZeroDivisionError:
        temp1 = 0
    stats.average_wait_time[0] += (temp1)
    if temp1 > stats.average_wait_time[1] or stats.average_wait_time[1] == -1:
        stats.average_wait_time[1] = temp1
    if temp1 < stats.average_wait_time[2] or stats.average_wait_time[2] == -1:
        stats.average_wait_time[2] = temp1
    stats.average_control_time[0] += control_time
    if control_time > stats.average_control_time[1] or \
       stats.average_control_time[1] == -1:
        stats.average_control_time[1] = control_time
    if control_time < stats.average_control_time[2] or \
       stats.average_control_time[2] == -1:
        stats.average_control_time[2] = control_time
    stats.average_fight_fire_time[0] += fight_fire_time
    if fight_fire_time > stats.average_fight_fire_time[1] or \
       stats.average_fight_fire_time[1] == -1:
        stats.average_fight_fire_time[1] = fight_fire_time
    if fight_fire_time < stats.average_fight_fire_time[2] or \
       stats.average_fight_fire_time[2] == -1:
        stats.average_fight_fire_time[2] = fight_fire_time
    update_points(fires, points)

def update_points(fires, points):
    '''Updates points' burned attribute by checking if within max fire sizes'''
    #Check if a point is burned by any fire at any point during the run
    #Checks fire areas burned more accurately - should always be used
    if IMPROVE_POINTS_BURN:
        for x in xrange(len(fires)):
            fires[x].real_centres_max() #updates ellipse centre
    for x in xrange(len(points)):
        points[x].burned.append(0.0)
        for y in xrange(len(fires)):
            #Bearing formula: http://www.movable-type.co.uk/scripts/latlong.html
            bearing = get_bearing(fires[y].real_long, fires[y].real_lat,
                                  points[x].longitude, points[x].latitude)
            point_distance = distance(points[x].longitude, points[x].latitude,
                                       fires[y].real_long, fires[y].real_lat)
            #theta is angle with head direction that the point direction makes
            if CCW_IS_POS:
                theta = bearing - (to_rad(fires[y].head_direction) -
                                   EAST_DIRECTION)
            else:
                theta = bearing + ((to_rad(fires[y].head_direction) +
                                            EAST_DIRECTION))
            #fire dist is the distance to fire perimeter in point direction
            fire_dist = ellipse_radius(fires[y].max_head_length,
                                       fires[y].max_flank_length, theta)
            #If point is within fires area it is considered burned
            if fire_dist >= point_distance:
                #Change last days burned value to 1.0 (True)
                points[x].burned[-1] = 1.0
                #Point already burned so dont need to check other fires
                break

            
##def human_fire_wait_time(env, inputs): # OLD AND WRONG
##    '''Determines wait time for next fire'''
##    num_fires = inputs.human_fires_day
####    mean_time = mean_time_between_fires(env, num_fires)
##    #delta is time period over which fires can occur
##    delta = inputs.time_until_dark - inputs.time_until_start
##    fires_m = num_fires / (delta) #mean fires/hour
##    time = (env.now % (LENGTH_DAY * 60.0)) - inputs.time_until_start
##    #Fires per hour at current time
##    fires_t = fires_m - AMP_H * math.cos(2 * math.pi * (time - LAG_H) / delta)
##    #Get mean_time between fires in minutes
##    mean_time = 60.0 / fires_t
##    wait_time = random.expovariate(1.0/(mean_time))
##    if wait_time < 0: #NEED TO FIX FORMULA SUCH THAT wait_time always > 0
##        wait_time = 100
##    return wait_time
##
##def lightning_fire_wait_time(env, inputs): #OLD AND WRONG
##    '''Determines wait time for next fire'''
##    num_fires = inputs.lightning_fires_day
####    mean_time = mean_time_between_fires(env, num_fires)
##    #delta is time period over which fires can occur
##    delta = inputs.time_until_dark - inputs.time_until_start
##    fires_m = num_fires / (delta) #mean fires/hour
##    time = (env.now % (LENGTH_DAY * 60.0)) - inputs.time_until_start
##    #Fires per hour at current time
##    fires_t = fires_m - AMP_L * math.cos(2 * math.pi * (time - LAG_L) / delta)
##    #Get mean_time between fires in minutes
##    mean_time = 60.0 / fires_t
##    wait_time = random.expovariate(1.0/(mean_time))
##    if wait_time < 0: #NEED TO FIX FORMULA SUCH THAT wait_time always > 0
##        wait_time = 100
##    return wait_time

def max_arrival_rate_human(env, inputs):
    ''' Return the mean wait time at max poisson interarrival rate
        Based on the following equation:
        fires_t = fires_m - AMP*math.cos(2*math.pi*(time - LAG)/delta)'''
    num_fires = inputs.human_fires_day
    #delta is the time period over which fires can occur
    delta = inputs.time_until_dark - inputs.time_until_start
    fires_m = num_fires / (delta / 60.0) #mean fires per hour
    # Find the time within delta that the highest arrival rate occurs at
    time = delta / 4 + LAG_H
    time = min(max(time, inputs.time_until_start), inputs.time_until_dark)
    fires_t = fires_m - AMP_H*math.cos(2*math.pi*(time - LAG_H)/delta)
    #Return mean wait_time in minutes for fires at max interarrival time
    return 60.0 / fires_t, fires_m

def human_arrived_fire_check(env, inputs, fires_m):
    '''Return True if the arrived fire is accepted else return False'''
    #Range of time fires can grow over
    delta = inputs.time_until_dark - inputs.time_until_start
    #Current time of day
    time = env.now % (LENGTH_DAY * 60.0)
    #Fire arrival rate at current time
    fires_t = fires_m - AMP_H*math.cos(2*math.pi*(time - LAG_H)/delta)
    #current arrival rate over max arrival rate
    p = fires_t / fires_m
    check = random.random()
    return check <= p

def max_arrival_rate_lightning(env, inputs):
    ''' Return the mean wait time at max poisson interarrival rate
        Based on the following equation:
        fires_t = fires_m - AMP*math.cos(2*math.pi*(time - LAG)/delta)'''
    num_fires = inputs.lightning_fires_day
    #delta is the time period over which fires can occur
    delta = inputs.time_until_dark - inputs.time_until_start
    fires_m = num_fires / (delta  / 60.0)#mean fires per hour
    # Find the fastest arrival rate at a time within delta
    time = delta / 4 + LAG_L
    time = min(max(time, inputs.time_until_start), inputs.time_until_dark)
    fires_t = fires_m - AMP_L*math.cos(2*math.pi*(time - LAG_L)/delta)
    #Return mean wait_time in minutes for fires at max interarrival time
    return 60.0 / fires_t, fires_m

def lightning_arrived_fire_check(env, inputs, fires_m):
    '''Return True if the arrived fire is accepted else return False'''
    #Range of time fires can grow over
    delta = inputs.time_until_dark - inputs.time_until_start
    #Current time of day
    time = env.now % (LENGTH_DAY * 60.0)
    #Fire arrival rate at current time
    fires_t = fires_m - AMP_L*math.cos(2*math.pi*(time - LAG_L)/delta)
    #current arrival rate over max arrival rate
    p = fires_t / fires_m
    check = random.random()
    return check <= p
    
        

def human_fire_generator(env, fires, forest, inputs): #fire gen process
    '''Generates a fire every ___ time'''
    #Generate fires for the whole run length
    mean_wait, fires_m = max_arrival_rate_human(env, inputs)
    while 1:
        #wait until time fires can start occuring
        yield env.timeout(inputs.time_until_start)
        while 1:
            #get the time until the next fire ignites
            wait_time = random.expovariate(1.0 / mean_wait)
            #if this time is past the end of the day, skip to the next day
            if (env.now % (LENGTH_DAY * 60.0) + wait_time) >= \
                                           inputs.time_until_dark:
                break
            #else make environment wait this amount of time then create a fire
            yield env.timeout(wait_time)
            if not human_arrived_fire_check(env, inputs, fires_m):
                continue
            create_fire(env, fires, forest, inputs, "Human")
        yield env.timeout((LENGTH_DAY * 60.0) - env.now)

def lightning_fire_generator(env, fires, forest, inputs): 
    '''Generates a fire every ___ time'''
    #Generate fires for the whole run length
    mean_wait, fires_m = max_arrival_rate_lightning(env, inputs)
    while 1:
        #wait until time fires can start occuring
        yield env.timeout(inputs.time_until_start)
        while 1:
            #get the time until the next fire ignites
            wait_time = random.expovariate(1.0 / mean_wait)
            #if this time is past the end of the day, skip to the next day
            if (env.now + wait_time) >= inputs.time_until_dark:
                break
            #else make environment wait this amount of time then create a fire
            yield env.timeout(wait_time)
            if not lightning_arrived_fire_check(env, inputs, fires_m):
                continue
            create_fire(env, fires, forest, inputs, "Lightning")
        yield env.timeout((LENGTH_DAY * 60.0) - env.now)

def get_min_drops(env, fire, airtanker, inputs):
    '''Based on fire size, return a value for the minimum number of drops'''
    #CHANGE TO SOMETHING MEANINGFUL BASED OF FIRE SIZE + AIRTANKER TYPE
    return 6

def get_max_drops(env, fire, airtanker, inputs):
    '''Based on fire size, return a value for the maximum number of drops'''
    #CHANGE TO SOMETHING MEANINGFUL BASED ON FIRE SIZE + AIRTANKER TYPE
    return 10

def get_number_drops(env, fire, airtanker, inputs):
    '''Determines the number of airtanker drops required to fight a fire'''
    min_drops = get_min_drops(env, fire, airtanker, inputs)
    max_drops = get_max_drops(env, fire, airtanker, inputs)
    num_drops = random.randint(min_drops, max_drops) #Discrete Uniform Dist
    return num_drops

def get_min_lake_distance(env, fire, airtanker, inputs):
    '''Return minimum possible lake distance from fire (km)'''
    #CHANGE TO MEANINGFUL VALUE
    return 15

def get_max_lake_distance(env, fire, airtanker, inputs):
    '''Return Maximum possible lake distance from fire (km)'''
    #CHANGE TO MEANINGFUL VALUE
    return 35


def get_lake_distance(env, fire, airtanker, inputs):
    '''Return lake distance randomly based on uniform distribution'''
    min_distance = get_min_lake_distance(env, fire, airtanker, inputs)
    max_distance = get_max_lake_distance(env, fire, airtanker, inputs)
    return random.uniform(min_distance, max_distance) #Uniform Distribution

def get_time_per_drop(lake_distance, airtanker):
    '''Return the time per drop'''
    #CHANGE FROM STRAIGHT DISTANCE TO SOME ELLIPTICAL ONE?
    return 2.0 * lake_distance / airtanker.fight_airspeed + airtanker.drop_time


def at_control_fire_time_calc(env, fire, airtanker, inputs):
    '''Determines actual amount of time process waits'''
    num_drops = get_number_drops(env, fire, airtanker, inputs)
    lake_distance = get_lake_distance(env, fire, airtanker, inputs)
    time_per_drop = get_time_per_drop(lake_distance, airtanker)
    time_yield = time_per_drop * num_drops
    #returns the time to control the fire, and the distance the airtanker flew
    return time_yield, lake_distance * num_drops * 2

def at_control_fire_time(env, fire, airtanker, inputs):
    '''Determines amount of time airtanker spends controlling the fire'''
    time_yield, dist = at_control_fire_time_calc(env, fire, airtanker, inputs)
    #Simulation ends at length run. If true fire will only be partially control
    if time_yield + env.now > inputs.length_run:
        percent = (inputs.length_run - env.now) / time_yield
    else:
        percent = 1.0
    #ALL of fire's sizes reduced by BHE value - INCORRECT
    fire.size = (1.0 - percent * BHE) * fire.size
    fire.perimeter = (1.0 - percent * BHE) * fire.perimeter
    fire.head_length = (1.0 - percent * BHE) * fire.head_length
    fire.flank_length = (1.0 - percent * BHE) * fire.flank_length
    fire.back_length = (1.0 - percent * BHE) * fire.back_length
    #Wait for the airtanker to finish serving the airtanker
    yield env.timeout(time_yield)
    #Update airtanker statistics about this fire
    airtanker.travel_distance += dist
    airtanker.total_travel_distance += dist
    airtanker.fight_fire_time +=  time_yield
    airtanker.total_fight_fire_time += time_yield


def fight_fire(env, fire, airtanker, inputs):
    '''Simpy process that is called when an airtanker arrives at a fire'''
    #For controlled fires, max size is at time when the airtanker just arrives
    fire.time = env.now
    fire.growth()
    fire.max_perimeter = fire.perimeter
    fire.max_size = fire.size
    fire.max_head_length = fire.head_length
    fire.max_flank_length = fire.flank_length
    fire.max_back_length = fire.back_length
    yield env.process(at_control_fire_time(env, fire, airtanker, inputs))
    #Fire is controlled at current time
    fire.controlled = True
    fire.time_at_controlled = env.now

def select_airtanker(env, fire, bases, inputs):
    '''Returns which base and airtanker will be used to fight fire
    Picks closest available airtanker currently'''
    #Set to default values
    base_num = -2.0
    airtanker_num = -2.0
    num_bases = len(bases)
    if len (bases) < 1: #Check if any bases
        return -1.0, -1.0
    for x in range(num_bases): #Check if there is at least one airtanker
        if len(bases[x].airtankers) > 0:
            break
        if x == (num_bases - 1): #if there is no airtankers in sim returns
            return -1.0, -1.0
    flag = True
    #time is time of day
    time = env.now %(LENGTH_DAY * 60.0)
    for x in xrange (num_bases): #Finds closest airtanker
        for y in xrange(len(bases[x].airtankers)):
            cur_at = bases[x].airtankers[y]
            new_dist = obj_distance(cur_at, fire)
            #check if current airtanker is withing iar of fire
            if new_dist - EPS <= cur_at.initial_attack_radius:
                flag = False
##            if bases[x].airtankers_resource[y].count == 1 and base_num == -2.0\
##                                                    and airtanker_num == -2.0:
            #if current airtanker is already busy, ignore it
            if bases[x].airtankers_resource[y].count == 1:
                continue
            #if no airtanker found yet set current one as closest if suitable
            elif base_num == -2.0 and airtanker_num == -2.0:
                try:
                    new_dist = obj_distance(cur_at, fire)
                except IndexError:
                    continue
                if cur_at.suitable(fire, time, inputs):
                    base_num = x
                    airtanker_num = y
                continue
            try:
                #check if next airtanker is suitable and closer to fire
                if (new_dist - EPS < obj_distance(
                    bases[base_num].airtankers[airtanker_num],fire) and \
                    cur_at.suitable(fire, time, inputs) and
                   bases[x].airtankers_resource[y].count != 1) :
                    base_num = x
                    airtanker_num = y
            except IndexError:
                continue
##    if flag:
##        return -3.0, -3.0 #No airtankers in range of this fire
    #Return selected airtanker or -2.0, -2.0 if no suitable ones available
    return base_num, airtanker_num

def airtanker_arrival(env, fire, airtanker):
    '''Sets statistics when airtanker arrives at fire'''
    travel_dist = obj_distance(airtanker, fire)
    travel_time = travel_dist / airtanker.cruising_airspeed
    #Airtankers new location is the fire
    airtanker.longitude = fire.longitude
    airtanker.latitude = fire.latitude
    #Update airtankers travel time and distance
    airtanker.travel_distance += travel_dist
    airtanker.total_travel_distance += travel_dist
    airtanker.travel_time += travel_time
    airtanker.total_travel_time += travel_time
    #Update that airtanker arrived at the fire at this time, fires current size
    fire.time_at_airtanker_arrival.append(env.now)
    fire.time = env.now
    fire.growth()
    fire.perimeter_at_airtanker_arrival.append(fire.perimeter)
    fire.size_at_airtanker_arrival.append(fire.size)

def find_closest_base(bases, airtanker):
    '''Return base_num of closest base to the airtanker'''
    base_num = 0
    base_dist = obj_distance(bases[base_num], airtanker)
    for x in xrange(1, len(bases)):
        #If next base is closer it is set as the current closest base
        if obj_distance(bases[x], airtanker) < base_dist:
            base_num = x
            base_dist = obj_distance(bases[x], airtanker)
    return base_num

def return_airtanker_process(env, bases, travel_time, airtanker,
                             airtanker_resource, fires):
    '''Control the airtanker after it fights a fire
    If 0 returns to home base
    If 1 returns to closest base
    If 2 returns to closest base unless in queue for another fire
    If 3 returns to closest base, but return to home base at end of day'''
    travel_distance = travel_time * airtanker.cruising_airspeed
    prot = airtanker.after_fire_protocol
    if airtanker_resource.queue is None: #Not in queue for another fire
        #check fuel then do something
        if prot == 0:
            yield env.timeout(travel_time) #returns home base
            #Set location to home base's location
            airtanker.latitude = airtanker.base_lat
            airtanker.longitude = airtanker.base_long
            #Add travel time and distance to statistics
            airtanker.travel_time += travel_time
            airtanker.total_travel_time += travel_time
            airtanker.travel_distance += travel_distance
            airtanker.total_travel_distance += travel_distance
        elif prot == 1 or prot == 3 or prot == 2: #returns nearest base
            #Find the closest base
            base_num = find_closest_base(bases, airtanker)
            #Find travel time and distance
            travel_dist = obj_distance(bases[base_num], airtanker)
            travel_time = travel_dist / airtanker.cruising_airspeed
            #Wait for this travel time
            yield env.timeout(travel_time)
            #Set airtanker's location to the base's location
            airtanker.latitude = bases[base_num].latitude
            airtanker.longitude = bases[base_num].longitude
            #Update airtankers travel time and distance statistics
            airtanker.travel_time += travel_time
            airtanker.total_travel_time += travel_time
            airtanker.travel_distance += travel_distance
            airtanker.total_travel_distance += travel_distance
##        elif prot == 2:
##            pass #airtanker stays at fire
    else:
        #check fuel then do something
        if prot == 0:
            yield env.timeout(travel_time) #returns home base
            #Set location to home base's location
            airtanker.latitude = airtanker.base_lat
            airtanker.longitude = airtanker.base_long
            #Add travel time and distance to statistics
            airtanker.travel_time += travel_time
            airtanker.total_travel_time += travel_time
            airtanker.travel_distance += travel_distance
            airtanker.total_travel_distance += travel_distance
        elif prot == 1 or prot == 3: #returns nearest base
            #Find the closest base
            base_num = find_closest_base(bases, airtanker)
            #Find travel time and distance
            travel_dist = obj_distance(bases[base_num], airtanker)
            travel_time = travel_dist / airtanker.cruising_airspeed
            #Wait for this travel time
            yield env.timeout(travel_time)
            #Set airtanker's location to the base's location
            airtanker.latitude = bases[base_num].latitude
            airtanker.longitude = bases[base_num].longitude
            #Update airtankers travel time and distance statistics
            airtanker.travel_time += travel_time
            airtanker.total_travel_time += travel_time
            airtanker.travel_distance += travel_distance
            airtanker.total_travel_distance += travel_distance
        elif prot == 2:
            pass #airtanker stays at fire

    

def check_fuel(env, bases, airtanker):
    '''Checks current distance/time travelled and if airtanker needs refuel'''
    pass

def calc_needed_fuel(env, bases, airtanker):
    'Return the necessary fuel to go to the fire'''
    pass

def dispatch_airtanker(env, fire, bases, fires, inputs):
    '''Requests an airtanker, then calls fight_fire process'''
    #Get the most suitable airtanker
    base_num, airtanker_num = select_airtanker(env, fire, bases, inputs)
    time_at_req = env.now
    if base_num == -1.0 or airtanker_num == -1.0: #Simulation has no airtankers
        return
    elif base_num == -2.0 and airtanker_num == -2.0: #All Airtankers are busy
        reqs = [] #stores requests for airtankers in a list
        reqs_sorted = [] #stores requests but keeps base+airtanker position
        timeout_list = [] #stores list of airtankers not yet available
        timeout_requests = [] #stores list of requests for those airtankers
        time = env.now % (LENGTH_DAY * 60.0) #current time in day
        for x in range(len(bases)):
            reqs_sorted.append([])
            for y in range(len(bases[x].airtankers)):
                flag = 1
                cur_at = bases[x].airtankers[y] 
                new_dist = obj_distance(cur_at, fire)
                #Request every suitable airtanker
                if cur_at.suitable(fire, time, inputs):
                    temp = bases[x].airtankers_resource[y].request()
                #Request to wait for new airtankers to start their shift
                elif (time - EPS <= cur_at.start_time and (new_dist - EPS) <=
                      cur_at.initial_attack_radius):
                    #Amount of time until airtanker is available
                    temp = env.timeout(cur_at.start_time - time)
                    timeout_list.append(cur_at)
                    at_request = bases[x].airtankers_resource[y].request()
                    timeout_requests.append(at_request)
                    reqs_sorted[-1].append(at_request)
                    flag = 0
                else:
                    temp = env.timeout((LENGTH_DAY * 60.0) - time)
                #only append requests to list not env.timeouts
                if flag:
                    reqs_sorted[-1].append(temp)
                reqs.append(temp)
        #Create variable to store the first available suitable airtanker
        the_airtanker = None
        #Run forever until we get get an airtanker (or simulation run runs out)
        while the_airtanker == None:
            #Wait for any of the requests to be True
            successful_airtanker_dict = yield simpy.events.AnyOf(env, reqs)
            #Time after requests
            new_time = env.now % (LENGTH_DAY * 60.0)
##            if False:
##                pass
            #If the airtanker was one that just started service find it here
            for x in xrange(len(timeout_list)):
                if (abs(timeout_list[x].start_time - new_time) <= EPS ):
                    the_airtanker = timeout_requests[x]
                    break
            #Otherwise one of the previous busy airtankers was available first
            else:
                #1st avail airtanker
                the_airtanker = successful_airtanker_dict.keys()[0]
                #find which airtanker became available
                for x in xrange(len(bases)):
                    for y in xrange(len(bases[x].airtankers)):
                        if the_airtanker == reqs_sorted[x][y]:
                            #if past the airtankers working time cancel
                            if new_time + EPS >=bases[x].airtankers[y].end_time:
                                the_airtanker = None
                        if (reqs_sorted[x][y] == None and
                            bases[x].airtankers[y].start_time - EPS<= new_time):
                            reqs_sorted[x][y] = \
                                    bases[x].airtankers_resource[y].request()
                        if bases[x].airtankers[y].end_time < new_time:
                            reqs_sorted[x][y] = None
                #If the found airtanker is actually not suitable
                if the_airtanker == None:
                    z = 0
                    #Remove all timeout requests from req list
                    while z < len(reqs):
                        try:
                            if type(reqs[z]) == simpy.events.Timeout:
                                reqs = reqs[:z] + reqs[z+1:]
                            else:
                                z += 1
                        except IndexError:
                            break
                    #rerequest all of the not yet started shift airtankers
                    for z in xrange(len(bases)):
                        for y in xrange(len(bases[z].airtankers)):
                            if bases[z].airtankers[y].start_time + EPS >=\
                               new_time:
                                temp = env.timeout(
                                bases[z].airtankers[y].start_time - new_time)
                                reqs.append(temp)
                                reqs_sorted[z][y] = temp
                            else:
                                reqs.append(env.timeout((LENGTH_DAY * 60.0)
                                                        - new_time))
                    #repeat loop since an airtanker was not found
        #Finally got an available airtanker
        for x in xrange(len(bases)):
            for y in xrange(len(bases[x].airtankers)):
                #Cancel all of the other requests for other airtankers
                if the_airtanker != reqs_sorted[x][y]:
                    bases[x].airtankers_resource[y].release(reqs_sorted[x][y])
                    try:
                        reqs_sorted[x][y].cancel(None, None, None)
                    except AttributeError:
                        pass #env.timeout has no cancel method
                #Find which airtanker at which base is the available one
                else:
                    base_num = x #Find which airtanker was chosen
                    airtanker_num = y
##        for x in xrange(len(timeout_requests)):
##            try:
##                if the_airtanker != timeout_requests[x]:
##                    timeout_requests[x].cancel(None, None, None)
##            except IndexError:
##                break
        if base_num < 0 or airtanker_num < 0:
            return
        #Calculate how long the wait_time was
        airtanker = bases[base_num].airtankers[airtanker_num]
        wait_time = env.now - time_at_req
        airtanker.total_wait_time += wait_time
        
        travel_dist = obj_distance(airtanker, fire)
        travel_time = travel_dist / airtanker.cruising_airspeed
        #Cause airtanker to wait for the travel time to the fire
        yield env.timeout(travel_time)
        #Handle updating once airtanker arrives at fire
        airtanker_arrival(env, fire, airtanker)
        #Wait for airtanker to finish controlling the fire
        yield env.process(fight_fire(env, fire, \
                                     bases[base_num].airtankers[airtanker_num],
                                     inputs))
        #Wait for airtanker to finish its return process
        yield env.process(return_airtanker_process(env, bases, travel_time,
            airtanker,bases[base_num].airtankers_resource[airtanker_num],fires))
        bases[x].airtankers_resource[y].release(the_airtanker)
##    elif base_num == -3.0 and airtanker_num == -3.0:
##        return
####        while 1:
####            for x in xrange(len(bases)):
####                for y in xrange(len(bases)):
####                    pass
    #There was an airtanker available from the select_airtanker function                
    else:                
        airtanker = bases[base_num].airtankers[airtanker_num]
        the_resource = bases[base_num].airtankers_resource[airtanker_num]
        #Take control of the resource so it is busy
        with the_resource.request() as req:
            yield req
            wait_time = env.now - time_at_req
            airtanker.total_wait_time += wait_time
            travel_dist = obj_distance(airtanker, fire)
            travel_time = travel_dist / airtanker.cruising_airspeed
            #Wait for travel time
            yield env.timeout(travel_time)
            #Handle airtanker arrival updating
            airtanker_arrival(env, fire, airtanker)
            #Wait for airtanker to fight the fire
            yield env.process(fight_fire(env, fire, airtanker, inputs))
            #Wait for the after fighting the fire airtanker process
            yield env.process(return_airtanker_process(env, bases, travel_time,
                                                airtanker,the_resource,fires))

def circling_process(env, bases):
    '''If an airtanker must stop fighting the fire, this func handles it'''
    pass

def bird_dogs_process(env, fires, bases):
    '''Controls bird dogs in simulation'''
    pass

def main_airtanker_process(env, fires, bases, inputs):
    '''When a fire is reported, calls the dispatch_airtanker process'''
    #Cycles through the list of fires and requests one airtanker for each
    #Order based on report times.
    while 1:
        min_report = -1.0
        lowest_fire = -1.0
        for x in xrange(len(fires)):
            #If next fires report time is earlier than previous, or no prev fire
            if (fires[x].time_at_report < min_report  or min_report == -1.0):
                #If fire wasn't already handled earlier by this function
                if fires[x].time_at_report > env.now:
                    #Set fire as current earliest yet to be handled fire
                    min_report = fires[x].time_at_report
                    lowest_fire = x
                else:
                    continue
        #If all fires have been handled, skip to end of simulation
        if min_report == -1.0:
            yield env.timeout(inputs.length_run - env.now + 1.0)
        #Wait til the next fires report time
        yield env.timeout(min_report - env.now)
        #Request an airtanker to handle the fire
        env.process(dispatch_airtanker(env, fires[lowest_fire],
                                       bases, fires, inputs))



def print_simulation_results(stats, points):
    '''Print out all of the results obtained from the simulation
        This print version used with the more memory intensive stat mode'''
    if len(stats.average_max_size) == 0:
        print "No Statistics Generated...Error or input error...\n\n"
        return
    print "\n\nSimulation Results:\n\n"
    print "Largest Day's Average Max Size: %4.2f" %max(stats.average_max_size)
    print "Smallest Day's Average Max Size: %4.2f" %min(stats.average_max_size)
    print "Average Day's Average Max Size: %4.2f" \
          %(sum(stats.average_max_size)/len(stats.average_max_size))
    print "Largest Day's Average Detection Size: %4.2f" \
          %max(stats.average_detection_size)
    print "Smallest Day's Average Detection Size: %4.2f" \
          %min(stats.average_detection_size)
    print "Average Day's Average Detection Size: %4.2f" \
          %(sum(stats.average_detection_size)/len(stats.average_detection_size))
    print "Largest Day's Average Report Size: %4.2f" \
          %max(stats.average_report_size)
    print "Smallest Day's Average Report Size: %4.2f" \
          %min(stats.average_report_size)
    print "Average Day's Average Report Size: %4.2f" \
          %(sum(stats.average_report_size) / len(stats.average_report_size))
    print "Largest Day's Average Time Between Fires: %4.2f"\
          %max(stats.average_ignition_time)
    print "Smallest Day's Average Time Between Fires: %4.2f"\
          %min(stats.average_ignition_time)
    print "Average Day's Average Time Between Fires: %4.2f"\
          %(sum(stats.average_ignition_time) / len(stats.average_ignition_time))
    print "Largest Day's Average Detection Time: %4.2f"\
          %max(stats.average_detection_time) #After ignition
    print "Smallest Day's Average Detection Time: %4.2f"\
          %min(stats.average_detection_time) #After ignition
    print "Average Day's Average Detection Time: %4.2f"\
          %(sum(stats.average_detection_time)/len(stats.average_detection_time))
    print "Largest Day's Average Report Time: %4.2f"\
          %max(stats.average_report_time) #After detection
    print "Smallest Day's Average Report Time: %4.2f"\
          %min(stats.average_report_time) #After detection
    print "Average Day's Average Report Time: %4.2f"\
          %(sum(stats.average_report_time) / len(stats.average_report_time))
    print "Largest Day's Number of Fires: %4d" %max(stats.num_fires)
    print "Smallest Day's Number of Fires: %4d" %min(stats.num_fires)
    print "Average Day's Number of Fires: %4.2f" \
          %(float(sum(stats.num_fires)) / len(stats.num_fires))
    print "Largest Day's Detection Rate: %4.2f" %max(stats.detection_rate)
    print "Smallest Day's Detection Rate: %4.2f" %min(stats.detection_rate)
    print "Average Day's Detection Rate: %4.2f"\
          %(sum(stats.detection_rate) / len(stats.detection_rate))
    print "Largest Day's Fire Control Rate: %4.2f" %max(stats.controlled_rate)
    print "Smallest Day's Fire Control Rate: %4.2f" %min(stats.controlled_rate)
    print "Average Day's Fire Control Rate: %4.2f" \
          %(sum(stats.controlled_rate) / len(stats.controlled_rate))
        
        #Airtanker Stats
    print "\n\nAirtanker Statistics:\n\n"
    print "Largest Day's Average Travel Time: %4.2f" \
          %max(stats.average_travel_time)
    print "Smallest Day's Average Travel Time: %4.2f" \
          %min(stats.average_travel_time)
    print "Average Day's Average Travel Time: %4.2f" \
          %(sum(stats.average_travel_time) / len(stats.average_travel_time))
    print "Largest Day's Average Travel Distance: %4.2f" \
          %max(stats.average_travel_distance)
    print "Smallest Day's Average Travel Distance: %4.2f" \
          %min(stats.average_travel_distance)
    print "Average Day's Average Travel Distance: %4.2f" \
          %(sum(stats.average_travel_distance) / \
            len(stats.average_travel_distance))
    print "Largest Day's Average Wait Time: %4.2f" %max(stats.average_wait_time)
    print "Smallest Day's Average Wait Time: %4.2f"%min(stats.average_wait_time)
    print "Average Day's Average Wait Time: %4.2f" \
          %(sum(stats.average_wait_time) / len(stats.average_wait_time))
    print "Largest Day's Average Fight Fire Time: %4.2f" \
          %max(stats.average_fight_fire_time)
    print "Smallest Day's Average Fight Fire Time: %4.2f" \
          %min(stats.average_fight_fire_time)
    print "Average Day's Average Fight Fire Time: %4.2f" \
          %(sum(stats.average_fight_fire_time) / \
            len(stats.average_fight_fire_time))
    print "Largest Day's Average Control Time: %4.2f" \
          %max(stats.average_control_time)
    print "Smallest Day's Average Control Time: %4.2f" \
          %min(stats.average_control_time)
    print "Average Day's Average Control Time: %4.2f" \
          %(sum(stats.average_control_time) / len(stats.average_control_time))

    #Points Statistics
    print "\n\nPoint Statistics\n"
    for x in xrange(len(points)):
        print"\nPoint %d\n\n" %(x + 1)
        print"Longitude: %2.2f" %points[x].longitude
        print "Latitude: %2.2f" %points[x].latitude
        print "Percent of days burned: %2.2f%%" \
              %(sum(points[x].burned) * 100.0 / len(points[x].burned))

def print_simulation_results_small(stats, points, days):
    '''Prints out all of the results obtained from the simulation
        This version used with the small stat saving mode'''
    if len(stats.average_max_size) < 3:
        print "No Statistics Generated...Error or input error...\n\n"
        return
    print "\n\nSimulation Results:\n\n"
    print "Largest Day's Average Max Size: %4.2f" %(stats.average_max_size[1])
    print "Smallest Day's Average Max Size: %4.2f" %(stats.average_max_size[2])
    print "Average Day's Average Max Size: %4.2f" \
          %(stats.average_max_size[0]/days)
    print "Largest Day's Average Detection Size: %4.2f" \
          %(stats.average_detection_size[1])
    print "Smallest Day's Average Detection Size: %4.2f" \
          %(stats.average_detection_size[2])
    print "Average Day's Average Detection Size: %4.2f" \
          %((stats.average_detection_size[0])/days)
    print "Largest Day's Average Report Size: %4.2f" \
          %(stats.average_report_size[1])
    print "Smallest Day's Average Report Size: %4.2f" \
          %(stats.average_report_size[2])
    print "Average Day's Average Report Size: %4.2f" \
          %((stats.average_report_size[0]) / days)
    print "Largest Day's Average Time Between Fires: %4.2f"\
          %(stats.average_ignition_time[1])
    print "Smallest Day's Average Time Between Fires: %4.2f"\
          %(stats.average_ignition_time[2])
    print "Average Day's Average Time Between Fires: %4.2f"\
          %((stats.average_ignition_time[0]) / days)
    print "Largest Day's Average Detection Time: %4.2f"\
          %(stats.average_detection_time[1]) #After ignition
    print "Smallest Day's Average Detection Time: %4.2f"\
          %(stats.average_detection_time[2]) #After ignition
    print "Average Day's Average Detection Time: %4.2f"\
          %((stats.average_detection_time[0])/days)
    print "Largest Day's Average Report Time: %4.2f"\
          %(stats.average_report_time[1]) #After detection
    print "Smallest Day's Average Report Time: %4.2f"\
          %(stats.average_report_time[2]) #After detection
    print "Average Day's Average Report Time: %4.2f"\
          %((stats.average_report_time[0]) / days)
    print "Largest Day's Number of Fires: %4d" %(stats.num_fires[1])
    print "Smallest Day's Number of Fires: %4d" %(stats.num_fires[2])
    print "Average Day's Number of Fires: %4.2f" \
          %(float((stats.num_fires[0])) / days)
    print "Largest Day's Detection Rate: %4.2f" %(stats.detection_rate[1])
    print "Smallest Day's Detection Rate: %4.2f" %(stats.detection_rate[2])
    print "Average Day's Detection Rate: %4.2f"\
          %((stats.detection_rate[0]) / days)
    print "Largest Day's Fire Control Rate: %4.2f" %(stats.controlled_rate[1])
    print "Smallest Day's Fire Control Rate: %4.2f" %(stats.controlled_rate[2])
    print "Average Day's Fire Control Rate: %4.2f" \
          %((stats.controlled_rate[0]) / days)
        
        #Airtanker Stats
    print "\n\nAirtanker Statistics:\n\n"
    print "Largest Day's Average Travel Time: %4.2f" \
          %(stats.average_travel_time[1])
    print "Smallest Day's Average Travel Time: %4.2f" \
          %(stats.average_travel_time[2])
    print "Average Day's Average Travel Time: %4.2f" \
          %((stats.average_travel_time[0]) / days)
    print "Largest Day's Average Travel Distance: %4.2f" \
          %(stats.average_travel_distance[1])
    print "Smallest Day's Average Travel Distance: %4.2f" \
          %(stats.average_travel_distance[2])
    print "Average Day's Average Travel Distance: %4.2f" \
          %((stats.average_travel_distance[0]) / days)
    print "Largest Day's Average Wait Time: %4.2f" %(stats.average_wait_time[1])
    print "Smallest Day's Average Wait Time: %4.2f"%(stats.average_wait_time[2])
    print "Average Day's Average Wait Time: %4.2f" \
          %((stats.average_wait_time[0]) / days)
    print "Largest Day's Average Fight Fire Time: %4.2f" \
          %(stats.average_fight_fire_time[1])
    print "Smallest Day's Average Fight Fire Time: %4.2f" \
          %(stats.average_fight_fire_time[2])
    print "Average Day's Average Fight Fire Time: %4.2f" \
          %((stats.average_fight_fire_time[0]) / days)
    print "Largest Day's Average Control Time: %4.2f" \
          %(stats.average_control_time[1])
    print "Smallest Day's Average Control Time: %4.2f" \
          %(stats.average_control_time[2])
    print "Average Day's Average Control Time: %4.2f" \
          %((stats.average_control_time[0]) / days)

    #Points Statistics
    print "\n\nPoint Statistics\n"
    for x in xrange(len(points)):
        print"\nPoint %d\n\n" %(x + 1)
        print"Longitude: %2.2f" %points[x].longitude
        print "Latitude: %2.2f" %points[x].latitude
        print "Percent of days burned: %2.3f%%" \
              %(sum(points[x].burned) * 100.0 / len(points[x].burned))

        
def print_fire_info(fires, bases):
    ''' Show all of the details about the simulation.
        Call every fire instance's print_attributes method
        Also calls every airtankers print_attributes method'''
    for x in xrange(len(fires)):
        print "\nFire ", x + 1, "\n"
        fires[x].print_attributes()
    for x in xrange(len(bases)):
        print "\nBase %d\n" %(x+1)
        for y in xrange(len(bases[x].airtankers)):
            print "\nAirtanker %d\n" %(y+1)
            bases[x].airtankers[y].print_attributes()

def simulation_day(env, env2, fires, bases, forest, points, stats, inputs):
    '''Main simulation function, runs whole simulation for one day'''
    #This function runs the simulation for one run length = inputs.length_run
    #Set up the human and lightning fire generator processes
    env.process(human_fire_generator(env, fires, forest, inputs))
    env.process(lightning_fire_generator(env, fires, forest, inputs))
    #Run the fire generation processes for the whole simulation length
    env.run(until=(inputs.length_run))
    #Now that we have all the fire stats, run the airtanker fighting process
    env2.process(main_airtanker_process(env2, fires, bases, inputs))
    env2.run(until=(inputs.length_run))
    #Update statistics based on what happened on this day
    if inputs.save_daily_averages:
        update_statistics(stats, fires, bases, points, inputs)
    else:
        update_statistics_small(stats, fires, bases, points, inputs)

def define_undefined(inputs):
    '''Gives values for inputs not entered'''
    #This function is designed to add default values to any User inputs
    #That were not entered, but currently is a mess
    if inputs.number_runs is None:
        print "Value of 1 assigned to number of runs\n"
        inputs.number_runs = 1
    if inputs.length_run is None:
        print "Value of 1440 minutes assigned to length of run\n"
        inputs.length_run = 1440.0
    if inputs.show_fire_attributes is None:
        print "Value of True assigned to Show Fire Attributes\n"
        inputs.show_fire_attributes = True
    if inputs.save_daily_averages is None:
        print "Value of True assigned to save daily averages\n"
        inputs.save_daily_averages = True
    if inputs.FFMC is None:
        print "Value of 80.0 assigned to FFMC\n"
        inputs.FFMC = 80.0
##    if inputs.ISI is None:
##        print "Value of 15.0 assigned to ISI\n"
##        inputs.ISI == 15.0
    if inputs.min_lat is None:
        print "Value of 0 assigned to minimum latitude\n"
        inputs.min_lat = 0
    if inputs.max_lat is None:
        print "Value of 200 assigned to maximum latitude\n"
        inputs.max_lat = 200
    if inputs.min_long is None:
        print "Value of 0 assigned to minimum longitude\n"
        inputs.min_long = 0
    if inputs.max_long is None:
        print "Value of 200 assigned to maximum longitude\n"
        inputs.max_long = 200
    if inputs.points_lat is None:
        print "Random Point Latitudes Set"
        inputs.points_lat = []
    if inputs.points_long is None:
        print "Random Point Longitudes Set"
        inputs.points_long = []


def check_inputs(inputs):
    '''Check the inputted values, fill in missing ones with default values'''
    #Provide type and value checking on all inputs
    #NOT UPDATED TO REFLECT MOST RECENT INPUTS YET - IS A MESS
    define_undefined(inputs)
    if type(inputs.number_runs) == float or type(inputs.number_runs) == int:
        inputs.number_runs = int(inputs.number_runs)
        if inputs.number_runs < 0:
            print "\nEnter Positive Number of Runs Value\n\n"
            return -1
    else:
        print "\nInvalid Number of Runs Value Entered\n\n"
        return -2
    if type(inputs.length_run) == float or type(inputs.length_run) == int:
        inputs.length_run = float(inputs.length_run)
        if inputs.length_run < 0:
            print "\nEnter Postive Simulation Run Length\n\n"
            return -1
    else:
        print "\nInvalid Simulation Run Length Entered\n\n"
        return -2
    if type(inputs.show_fire_attributes) != bool:
        if inputs.show_fire_attributes in ("Yes", "yes", "Y", "y", "Ya", "ya"):
            inputs.show_fire_attributes = True
        elif inputs.show_fire_attributes in ("No", "no", "N", "n", "na", "Na"):
            inputs.show_fire_attributes = False
        else:
            print "\nInvalid Show Fire Attributes Value\n\n"
            return -2
    if type(inputs.save_daily_averages) != bool:
        if inputs.save_daily_averages in ("Yes", "yes", "Y", "y", "Ya", "ya"):
            inputs.save_daily_averages = True
        elif inputs.save_daily_averages in ("No", "no", "N", "n", "na", "Na"):
            inputs.save_daily_averages = False
        else:
            print "\nInvalid Save Daily Averages Value\n\n"
            return -2
    if type(inputs.FFMC) == float or type(inputs.FFMC) == int:
        inputs.FFMC = float(inputs.FFMC)
        if inputs.FFMC < 0 or inputs.FFMC > 150:
            print "\nFFMC Value Out of range\n\n"
            return -1
    else:
        print "Invalid FFMC Value Entered"
        return -2
##    if type(inputs.ISI) == float or type(inputs.ISI) == int:
##        inputs.ISI = float(inputs.ISI)
##        if inputs.ISI < 0 or inputs.ISI > 50:
##            print "\nISI Value Out of Range\n\n"
##            return -1
##    else:
##        print "Invalid ISI Value Entered\n\n"
##        return -2
    if type(inputs.min_lat) == float or type(inputs.min_lat) == int:
        inputs.min_lat = float(inputs.min_lat)
        if inputs.min_lat < -90.0 or inputs.min_lat > 90.0:
            print "\nMin Latitude Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Min Latitude Value Entered\n\n"
        return -2
    if type(inputs.max_lat) == float or type(inputs.max_lat) == int:
        inputs.max_lat = float(inputs.max_lat)
        if inputs.max_lat < -90.0 or inputs.max_lat > 90.0:
            print "\nMax Latitude Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Max Latitude Value Entered\n\n"
        return -2
    if inputs.max_lat < inputs.min_lat:
        print "\nMax Lat Smaller than Min Lat; Values Swapped\n\n"
        inputs.max_lat, inputs.min_lat = inputs.min_lat, inputs.max_lat
    if type(inputs.min_long) == float or type(inputs.min_long) == int:
        inputs.min_long = float(inputs.min_long)
        if inputs.min_long < -180.0 or inputs.min_long > 180.0:
            print "\nMin Longitude Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Min Longitude Value Entered\n\n"
        return -2
    if type(inputs.max_long) == float or type(inputs.max_long) == int:
        inputs.max_long = float(inputs.max_long)
        if inputs.max_long < -180.0 or inputs.max_long > 180.0:
            print "\nMax Latitude Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Max Latitude Value Entered\n\n"
        return -2
    if inputs.max_long < inputs.min_long:
        print "\nMax Long Smaller than Min Long; Values Swapped\n\n"
        inputs.max_long, inputs.min_long = inputs.min_long, inputs.max_long
    if type(inputs.num_rows) == float or type(inputs.num_rows) == int:
        inputs.num_rows = int(inputs.num_rows)
        if inputs.num_rows < 0:
            print "\nNumber of Rows Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Number of Rows Value Entered\n\n"
        return -2
    if type(inputs.num_columns) == float or type(inputs.num_columns) == int:
        inputs.num_columns = int(inputs.num_columns)
        if inputs.num_columns < 0:
            print "\nNumber of Columns Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Number of Columns Value Entered\n\n"
        return -2
    if type(inputs.PC) == float or type(inputs.PC) == int:
        inputs.PC = float(inputs.PC)
        if inputs.PC < 0.0 or inputs.PC > 100.0:
            print "\nPercent Cured Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Percent Cured Value Entered\n\n"
        return -2
    if type(inputs.PDF) == float or type(inputs.PDF) == int:
        inputs.PDF = float(inputs.PDF)
        if inputs.PDF < 0.0 or inputs.PDF > 100.0:
            print "\nPercent Dead Fir Value Out of Range\n\n"
            return -1
    else:
        print "Invalid Percent Dead Fir Value Entered\n\n"
        return -2
    if type(inputs.num_bases) == float or type(inputs.num_bases) == int:
        inputs.num_bases = int(inputs.num_bases)
        if inputs.num_bases < 0:
            print "\nNumber of Bases Value Out of Range\n\n"
            return -1
    else:
        print inputs.num_bases
        print "Invalid Number of Bases Value Entered\n\n"
        return -2
    if inputs.num_bases != len(inputs.bases_lat):
        print "\nNumber of Bases and their Latitudes Don't Match\n\n"
        return -1
    if inputs.num_bases != len(inputs.bases_long):
        print "\nNumber of Bases and their Longitudes Don't Match\n\n"
        return -1
    if inputs.num_bases != len(inputs.base_num_airtankers):
        print "\nNumber of Bases and Number of Airtankers Don't Match\n\n"
        return -1
    if inputs.num_bases != len(inputs.base_num_bird_dogs):
        print "\nNumber of Bases and Number of Bird Dogs Don't Match\n\n"
        return -1
    for x in xrange(inputs.num_bases):
        if type(inputs.bases_lat[x]) == float or type(inputs.bases_lat[x])==int:
            inputs.bases_lat[x] = float(inputs.bases_lat[x])
            if inputs.bases_lat[x] < -90.0 or inputs.bases_lat[x] > 90.0:
                print "\nBase %d Latitude Out of range\n\n" %(x + 1)
                return -1
        else:
            print "\nInvalid Base %d Latitude\n\n" %(x + 1)
        if type(inputs.bases_long[x]) == float or \
           type(inputs.bases_long[x])==int:
            inputs.bases_long[x] = float(inputs.bases_long[x])
            if inputs.bases_long[x] < -180.0 or inputs.bases_long[x] > 180.0:
                print "\nBase %d Longitude Out of Range\n\n" %(x + 1)
                return -1
        else:
            print "\nInvalid Base %d Longitude\n\n" %(x + 1)
        if type(inputs.base_num_airtankers[x]) == float or \
                type(inputs.base_num_airtankers[x]) == int:
            inputs.base_num_airtankers[x] = \
                                          int(inputs.base_num_airtankers[x])
            if inputs.base_num_airtankers < 0:
                print "\nNumber of Airtankers Out of Range\n\n"
                return -1
        else:
            print "\nInvalid Number of Airtankers Entered\n\n"
            return -2
        if inputs.base_num_airtankers[x] != \
           len(inputs.base_airtankers_cruising[x]):
            print "\nNumber of Airtankers and Cruising Speeds Don't Match\n\n"
            return -1
        if inputs.base_num_airtankers[x] !=len(inputs.base_airtankers_fight[x]):
            print "\nNumber of Airtankers and Fight Speeds Don't Match\n\n"
            return -1
        if inputs.base_num_airtankers[x] != \
           len(inputs.base_airtankers_circling[x]):
            print "\nNumber of Airtankers and Circling Speeds Don't Match\n\n"
            return -1
##        if inputs.base_num_airtankers[x] != \
##           len(inputs.base_airtankers_max_time[x]):
##            print "\nNumber of Airtankers and Max Time Don't Match\n\n"
##            return -1
##        if inputs.base_num_airtankers[x] != \
##           len(inputs.base_airtankers_max_distance[x]):
##            print "\nNumber of Airtankers and Max Distance Don't Match\n\n"
##            return -1
        for y in xrange(inputs.base_num_airtankers[x]):
            temp = inputs.base_airtankers_cruising[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nAirtanker Cruising Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Airtanker Cruising Speed\n\n"
                return -2
            temp = inputs.base_airtankers_fight[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nAirtanker Fight Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Airtanker Fight Speed\n\n"
                return -2
            temp = inputs.base_airtankers_circling[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nAirtanker Circling Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Airtanker Circling Speed\n\n"
                return -2
##            temp = inputs.base_airtankers_max_time[x][y]
##            if type(temp) == float or type(temp) == int:
##                temp = float(temp)
##                if temp < 0.0:
##                    print "\nAirtanker Max Time Out of Range\n\n"
##                    return -1
##            else:
##                print "\nInvalid Airtanker Max Time\n\n"
##                return -2
##            temp = inputs.base_airtankers_max_distance[x][y]
##            if type(temp) == float or type(temp) == int:
##                temp = float(temp)
##                if temp < 0.0:
##                    print "\nAirtanker Max Time Out of Range\n\n"
##                    return -1
##            else:
##                print "\nInvalid Airtanker Max Distance\n\n"
##                return -2
        if type(inputs.base_num_bird_dogs[x]) == float or \
                type(inputs.base_num_bird_dogs[x]) == int:
            inputs.base_num_bird_dogs[x] = \
                                          int(inputs.base_num_bird_dogs[x])
            if inputs.base_num_bird_dogs < 0:
                print "\nNumber of Bird Dogs Out of Range\n\n"
                return -1
        else:
            print "\nInvalid Number of Bird Dogs Entered\n\n"
            return -2
        if inputs.base_num_bird_dogs[x] != \
           len(inputs.base_bird_dogs_cruising[x]):
            print "\nNumber of Bird Dogs and Cruising Speeds Don't Match\n\n"
            return -1
        if inputs.base_num_bird_dogs[x] != len(inputs.base_bird_dogs_fight[x]):
            print "\nNumber of Bird Dogs and Fight Speeds Don't Match\n\n"
            return -1
        if inputs.base_num_bird_dogs[x]!=len(inputs.base_bird_dogs_circling[x]):
            print "\nNumber of Bird Dogs and Circling Speeds Don't Match\n\n"
            return -1
##        if inputs.base_num_bird_dogs[x]!=len(inputs.base_bird_dogs_max_time[x]):
##            print "\nNumber of Bird Dogs and Max Times Don't Match\n\n"
##            return -1
##        if inputs.base_num_bird_dogs[x] != \
##           len(inputs.base_bird_dogs_max_distance[x]):
##            print "\nNumber of Bird Dogs and Max Distances Don't Match\n\n"
##            return -1
        for y in xrange(inputs.base_num_bird_dogs[x]):
            temp = inputs.base_bird_dogs_cruising[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nBird Dog Cruising Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Bird Dog Cruising Speed\n\n"
                return -2
            temp = inputs.base_bird_dogs_fight[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nBird Dog Fight Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Bird Dog Fight Speed\n\n"
                return -2
            temp = inputs.base_bird_dogs_circling[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nBird Dog Circling Speed Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Bird Dog Circling Speed\n\n"
                return -2
##            temp = inputs.base_bird_dogs_max_time[x][y]
##            if type(temp) == float or type(temp) == int:
##                temp = float(temp)
##                if temp < 0.0:
##                    print "\nBird Dog Max Time Out of Range\n\n"
##                    return -1
##            else:
##                print "\nInvalid Bird Dog Max Time\n\n"
##                return -2
##            temp = inputs.base_bird_dogs_max_distance[x][y]
##            if type(temp) == float or type(temp) == int:
##                temp = float(temp)
##                if temp < 0.0:
##                    print "\nBird Dog Max Distance Out of Range\n\n"
##                    return -1
##            else:
##                print "\nInvalid Bird Dog Max Distance\n\n"
##                return -2
    #Points Check
    if type(inputs.num_points) == float or type(inputs.num_points) == int:
        inputs.num_points = int(inputs.num_points)
        if inputs.num_points < 0:
            print "Number of Points Out of Range\n\n"
            return -1
    else:
        print "Invalid Number of Points"
        return -2
    if inputs.points_lat == '' or inputs.points_long == '':
        return 0
    if inputs.num_points != len(inputs.points_lat):
        print "\nNumber of Points and Point Latitudes Don't Match\n\n"
        return -1
    if inputs.num_points != len(inputs.points_long):
        print "\nNumber of Points and Point Longitudes Don't Match\n\n"
        return -1
    for x in xrange(inputs.num_points):
        if type(inputs.points_lat[x])==float or type(inputs.points_lat[x])==int:
            inputs.points_lat[x] = float(inputs.points_lat[x])
            if inputs.points_lat[x] < -90.0 or inputs.points_lat > 90.0:
                print "\nPoint Latitudes Out of Range\n\n"
                return -1
        else:
            print "\nInvalid Point Latitudes\n\n"
        if type(inputs.points_long[x])== float or \
           type(inputs.points_long[x])== int:
            inputs.points_long = float(inputs.points_long)
            if inputs.points_long[x] < -180.0 or inputs.points_long > 180.0:
                print "\nPoint Longitudes Out of Range\n\n"
                return -1
        else:
            print "\nInvalid Point Longitudes\n\n"

def main_func(read_only_values):
    '''Main Simulation Program, call to run the program'''
    #This is the function called to run the whole program
    #Time allows us to see how long the simulation takes to run
    time1 = time.clock()
    #Save user inputs to class
    inputs = User_input(read_only_values)
    check = check_inputs(inputs)
    #Check Inputs - OUTDATED
    if check == -1 or check == -2:
        print "\nImproper Inputs, System Quitting...\n\n"
        return -1
    #Create statistics class to store stats during the simulation
    stats = Statistics()
    #If no forest data file, create a random forest to use instead
    if not USE_FOREST_DATA:
        forest = create_forest(inputs)
    else:
        forest = []
        #Create points to track
    points = create_points(inputs)
    #Run simulation for user specified number of days
    for days in xrange(int(inputs.number_runs)):
        fires = []
        env = simpy.Environment()
        env2 = simpy.Environment()
        bases = create_bases(env2, inputs)
        simulation_day(env, env2, fires, bases, forest, points, stats, inputs)
        #Optionally show all fire and airtankers stats after every run
        if inputs.show_fire_attributes:
            print_fire_info(fires, bases)
    #big or small statistics saving mode
    if inputs.save_daily_averages:
        print_simulation_results(stats, points)
    else:
        print_simulation_results_small(stats, points, inputs.number_runs)
    #Calculate and print time to run simulation
    time2 = time.clock()
    print"\n\nIt took %f seconds to do %d runs!\n\n" %(time2-time1,
                                                       inputs.number_runs)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                Run Simulation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
if __name__ == '__main__':
    list1 = [0 for x in xrange (44)]
    list1[0] = 100
    list1[1] = 1440.0
    list1[3], list1[4] = 5, 5
    list1[6], list1[7] = False, False
    list1[8], list1[9], list1[10], list1[11] = 7, 11, '', ''
    list1[21], list1[23] = 85, 85
    list1[24], list1[25] = 10, 10
    list1[26] = 0
    for y in xrange(27, 44):
        list1[y] = []
    list1[41] = 0
    list1 = [100, 1440, 1000, 5, 5, '', False, False, 5, 26, '', '', 85.0,
             110.0, 10, 130.0, 60, 60, 60, 60, 47, 56, -96, -84, 10, 10, 2,
             [65.3, 62.1], [-85.6, -79.4], [2.0, 1.0], [0.0, 0.0],
             [5.0, 5.0, 4.0], [5.0, 5.0, 4.0], [5.0, 5.0, 4.0], '', '', '',
             [5.0, 5.0, 3.0], [5.0, 5.0, 3.0], '', '', 10, '', '']
    main_func(list1)
        
    










    
