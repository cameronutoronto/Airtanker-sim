from __future__ import division
import math
import random
import simpy
import time
import fbpline2
from haversine import *
#Airtanker Simulation Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

#Please note that values of -1.0 are unchanged or erroneous values

#POINTS BROKEN *fixed

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                           Read-only Variables (editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
EARTHS_RADIUS = 6371.0 #KM
FOREST_DATA_LOCATION = "canadian_forest_data.txt"
USE_FOREST_DATA = True
IMPROVE_POINTS_BURN = True #Better check, costs time
EAST_DIRECTION = 0.0 #Set Default Direction in RADIANS
CCW_IS_POS = True #Set counter-clock-wise is positive direction
BHE = 0.4 #When airtanker covers 40% of perimeter, fire is controlled
DROP_TIME = 1.0 #Time for one airtanker water drop (excluding travel time)

class user_input(object):
    def __init__(self, inputs):
        #Simulation

        #Number of "days" simulation repeats 
        self.number_runs = inputs[0] 
        self.length_run = inputs[1] #minutes
        #If True, shows all of the data for every fire
        self.time_until_dark = inputs[2]
        self.lightning_fires_day = inputs[3]
        self.human_fires_day = inputs[4]
        self.check_distance = inputs[5]
        self.show_fire_attributes = inputs[6]
        #If True, save more statistics at the cost of memory
        self.save_daily_averages = inputs[7]

        #FBP Info

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
        self.num_stands = self.num_rows * self.num_columns

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Classes
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class Fire(object):
    def __init__(self, time_at_ignition, time_at_detection, time_at_report,  \
                 slope, time, latitude, longitude, fuel_type, detected,\
                 slope_azimult, cause, inputs):
        self.time_at_ignition = time_at_ignition #Time Fire Starts
        self.time_at_detection = time_at_detection #Time Fire is Detected
        self.time_at_report = time_at_report #Time Fire is Reported
        self.slope = slope
        self.time = time
        self.latitude = latitude
        self.real_lat = latitude
        self.longitude = longitude
        self.real_long = longitude
        self.fuel_type = fuel_type
        self.detected = detected #True if fire is detected, else False
        self.size_at_detection = -1.0
        self.perimeter_at_detection = -1.0
        self.size_at_report = -1.0
        self.perimeter_at_report = -1.0
        self.size_at_detection = -1.0
        self.perimeter_at_detection = -1.0
        self.head_length_detect = -1.0
        self.flank_length_detect = -1.0
        self.back_length_detect = -1.0
        self.head_length_report = -1.0
        self.flank_length_report = -1.0
        self.back_length_report = -1.0
        self.size = 0.0 #Assume fires start as points
        self.head_length = 0.0
        self.flank_length = 0.0
        self.back_length = 0.0
        self.max_size = 0.0 #largest size of fire
        self.max_head_length = 0.0
        self.max_flank_length = 0.0
        self.max_back_length = 0.0
        self.elevation = 0.0 #CHANGE
        self.slope_azimult = slope_azimult
        self.head_ros, self.flank_ros, self.back_ros, self.head_direction = \
                       self.get_ros(inputs)
        self.perimeter = 0.0
        self.max_perimeter = 0.0
        self.cause = cause
        self.value_at_risk = self.calc_value_risk() #*
        self.airtankers_required = 1 #*
        self.airtankers_still_required = 1 #change to 0 when a airtanker arrives
        self.bird_dogs_required = 1#*
        priority = 1#*

        #airtanker values
        self.size_at_airtanker_arrival = []
        self.perimeter_at_airtanker_arrival = []
        self.time_at_airtanker_arrival = []
        self.time_at_controlled = -1.0
        self.controlled = False
        self.airtanker_return_time = []


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
        self.value_at_risk = 5
        return 5


    def growth(self): #assumed fires grow linearly
        if self.time < self.time_at_ignition:
            self.head_length = -1.0
            self.flank_length = -1.0
            self.back_length = -1.0
            self.perimeter = -1.0
            self.size = -1.0
        else:
            self.head_length = ((self.time - self.time_at_ignition) *
                                self.head_ros)
            self.flank_length = ((self.time - self.time_at_ignition) *
                               self.flank_ros)
            self.back_length = ((self.time - self.time_at_ignition) *
                                self.back_ros)
            self.size = area_ellipse((self.head_length + self.back_length) / 2,\
                                     self.flank_length)
            self.perimeter = perimeter_ellipse((self.head_length +
                                                self.back_length) / 2,
                                               self.flank_length)

    def max_growth(self, inputs):
        self.time = inputs.length_run #Initally set to grow til end of day
        self.growth()
        self.max_perimeter = self.perimeter
        self.max_size = self.size
        self.max_head_length = self.head_length
        self.max_flank_length = self.flank_length
        self.max_back_length = self.back_length


    def detect(self): #Updates detected and report size + radius
        temp = self.time
        self.time = self.time_at_detection
        self.growth()
        self.size_at_detection = self.size
        self.perimeter_at_detection = self.perimeter
        self.head_length_detect = self.head_length
        self.flank_length_detect = self.flank_length
        self.back_length_detect = self.back_length
        self.time = self.time_at_report
        self.growth()
        self.size_at_report = self.size
        self.perimeter_at_report = self.perimeter
        self.head_length_report = self.head_length
        self.flank_length_report = self.flank_length
        self.back_length_report = self.back_length
        self.time = temp


    def real_centres_max(self): #Gives real elliptical centre
        '''Source: http://www.movable-type.co.uk/scripts/latlong.html
        Assumed 0 bearing is true north, increasing bearing clockwise'''
        dist = ((self.max_head_length - self.max_back_length) / 2 -
                self.max_back_length)
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
        while self.real_long > 0:
            self.real_long -= 360.0 #Western Hemisphere
        self.real_long = self.real_long % -360.0
        self.real_lat = to_degrees(new_lat)
        while self.real_lat < 0:
            self.real_lat += 360.0
        self.real_lat = self.real_lat % 360.0
        return

    
    def print_attributes(self): #Print all of the fire's attributes
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
        for x in xrange(len(self.size_at_airtanker_arrival)):
            try:
                print "Size at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.size_at_airtanker_arrival[x])
                print "Perimeter at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.perimeter_at_airtanker_arrival[x])
                print "Time at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.time_at_airtanker_arrival[x])
                print "Time of Airtanker %d Return: %4.2f" \
                      %(x + 1, self.airtanker_return_time[x])
            except IndexError:
                pass
        if self.controlled:
            print "Controlled at Time: %.2f" %self.time_at_controlled

class Statistics(object): #Has many useful statistics as attributes
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
    def __init__(self, cruising_airspeed, fight_airspeed, circling_speed,
                 lat, lon, fly_when_dark, drop_type, size, fuel_capacity,
                 fuel_consumption, after_fire_protocol):
        self.cruising_airspeed = cruising_airspeed #main flight speed
        self.fight_airspeed = fight_airspeed #flight speed when fighting fire
        self.circling_speed = circling_speed #fight speed when circling
        self.latitude = lat
        self.longitude = lon
        self.base_lat = lat
        self.base_long = lon
        self.travel_time = 0.0
        self.total_travel_time = 0.0
        self.travel_distance = 0.0
        self.total_travel_distance = 0.0
        self.total_wait_time = 0.0
        self.total_fight_fire_time = 0.0
        self.fly_when_dark = fly_when_dark
        self.drop_type = drop_type #3 types salvo, trail and misc
        self.size = size #small/large
        self.after_fire_protocol = after_fire_protocol #Goes where after fire
        self.fuel_capacity = fuel_capacity #cannot reach 0
        self.fuel_consumption = fuel_consumption #Some units
        self.initial_attack_radius = self.calc_iar()

    def calc_iar(self):
        '''Return an iar for the airtanker based on its other statistics'''
        return 5

class Base(object):
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
    def __init__(self, fuel_type, slope, slope_azimult):
        self.fuel_type = fuel_type
        self.slope = slope
        self.slope_azimult = slope_azimult

class Point(object): #Points to keep track of during simulation
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.burned = []

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def mean_time_between_fires(env, fires_per_day): #Use to calculate fire ign times
    '''Return mean time in minutes between fires'''
    fires_per_hour = fires_per_day / 24.0 #OR 8.0?
    return  60.0 / fires_per_hour

def obj_distance(obj1, obj2):
    '''Uses Haversice Formula to find the distance between 2 points
    Source: http://en.wikipedia.org/wiki/Haversine_formula'''
    dist = distance(obj1.longitude, obj1.latitude, obj2.longitude,obj2.latitude)
    if isinstance(obj1, Fire):
        pass
    if isinstance(obj2, Fire):
        pass
    return dist

def generate_fueltype(): #Assumed uniform distribution of fueltypes in forest
    '''Use some probability distribution to return fueltypes'''
    fuel_types = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "D1", "M1",\
                  "M2", "M3", "M4", "O1a", "O1b", "S1", "S2", "S3"]
    return fuel_types[random.randint(0, len(fuel_types) - 1)]#some fuel type

def generate_slope(): #DOESNT CURRENTLY AFFECT ANYTHING ELSE
    '''Uses some probability distribution to generate a slope'''
    return random.uniform(0, 5)

def create_forest(inputs): #Generate forest with random stands
    '''Return a list of lists of stands that represent each row in the forest'''
    forest = []
    if type(inputs.num_rows) != int:
        print "Please enter num_rows as an integer"
        raise SystemExit
    if type(inputs.num_columns) != int:
        print "Please enter num_columns as an integer"
        raise SystemExit
    for x in xrange (inputs.num_rows):
        forest.append([])
        for y in xrange(inputs.num_columns):
            forest[x].append(Forest_stand(generate_fueltype(),generate_slope(),
                                          random.uniform(0, 360)))
    return forest

def get_stand_info_random(lat, lon, forest, inputs):
    '''Returns slope and fuel type and given location'''
    lat_stand = len(forest) - int(((lat - inputs.min_lat) / \
                                   (inputs.max_lat-inputs.min_lat))*len(forest))
    if lat_stand == 0:
        lat_stand = 1
    long_stand = len(forest[0]) - int(((lon - inputs.min_long) /\
                                       (inputs.max_long - inputs.min_long))\
                                      * len(forest[0]))
    if long_stand == 0:
        long_stand = 1
    return forest[lat_stand - 1][long_stand - 1].fuel_type, \
        forest[lat_stand - 1][long_stand - 1].slope, \
        forest[lat_stand - 1][long_stand - 1].slope_azimult

def get_stand_info(lat, lon, inputs):
    '''Return fuel type and fuel percent at a coordinate location
    Using the forest_data_input_file'''
    forest_data_file = open(FOREST_DATA_LOCATION, 'r')
    temp = forest_data_file.readline()
    temp = forest_data_file.readline()
    temp2 = temp.split(',')
    dist = distance(lon, lat, float(temp2[2]), float(temp2[1]))
    fueltype = temp2[3]
    fuel_perc = float(temp2[4])
    next_temp = forest_data_file.readline()
    while next_temp != '' and next_temp != '\n':
        temp = next_temp
        temp2 = temp.split(',')
        new_dist = distance(lon, lat, float(temp2[2]), float(temp2[1]))
        if new_dist < dist:
            dist = new_dist
            fueltype = temp2[3]
            fuel_perc = float(temp2[4])
        next_temp = forest_data_file.readline()
    forest_data_file.close()
    return fueltype, fuel_perc

def lightning_is_detected(env, inputs):
    '''Determines if lightning caused fire is detected'''
    if random.random() < 0.8: #80% Chance fire is detected
        detected = True
    else:
        detected = False
    return detected

def human_is_detected(env, inputs):
    '''Determines if human caused fire is detected'''
    if random.random() < 0.8: #80% Chance fire is detected
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
    detect_time = random.expovariate(1.0 / 120.0)# 2 hours detect
    return detect_time

def human_detect_time(env, inputs):
    '''Return human caused fire detection_time'''
    detect_time = random.expovariate(1.0 / 120.0)# 2 hours detect
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
    report_time = random.expovariate(1.0 / 10.0)# 10 minute detect
    return report_time

def human_report_time(env, inputs):
    '''Return human caused fire report time'''
    detect_time = random.expovariate(1.0 / 10.0)# 10 minute detect
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
    latitude = random.uniform(inputs.min_lat, inputs.max_lat)
    return latitude

def human_determine_latitude(env, inputs, fires):
    '''determines latitude for a human caused fire'''
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
    longitude = random.uniform(inputs.min_long, inputs.max_long)
    return longitude

def human_determine_longitude(env, inputs, fires):
    '''determines longitude for a human caused fire'''
    longitude = random.uniform(inputs.min_long, inputs.max_long)
    return longitude

def determine_fire_longitude(env, inputs, cause, fires):
    '''Determines longitude of new fire'''
    if cause == "Lightning":
        latitude = lightning_determine_longitude(env, inputs, fires)
    elif cause == "Human":
        latitude = human_determine_longitude(env, inputs, fires)
    return latitude

def create_fire(env, fires, forest, inputs, cause):
    '''Randomly generates a fire and appends it to parameter fires'''
    ig_time = env.now
    detected = True
    if is_detected(env, inputs, cause): 
        detect_time = determine_detect_time(env, inputs, cause) + ig_time
        report_time = determine_report_time(env, inputs, cause) + detect_time
    else:
        detect_time = -1.0
        detected = False
        report_time = -1.0
    lat = determine_fire_latitude(env, inputs, cause, fires)
    lon = determine_fire_longitude(env, inputs, cause, fires)
    if not USE_FOREST_DATA:
        fuel_type, slope, slope_azimult = get_stand_info_random(lat, lon,
                                                                forest, inputs)
        fuel_perc = ''
    else:
        fuel_type, fuel_perc = get_stand_info(lat, lon, inputs)
        slope = ''
        slope_azimult = ''
    fires.append(Fire(ig_time, detect_time, report_time, slope, env.now, \
                      lat, lon, fuel_type, detected, slope_azimult, cause,
                      inputs))

    if detected:
        fires[-1].detect()
    fires[-1].max_growth(inputs)

def determine_points_latitude(inputs, points, point_num):
    '''Return latitude for the point'''
    try:
        lat = inputs.points_lat[point_num]
    except IndexError:
        lat = random.uniform(inputs.min_lat, inputs.max_lat)
    return lat

def determine_points_longitude(inputs, points, point_num):
    '''Return longitude for the point'''
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
    return points


def determine_at_cruising(base_num, env, inputs, at_num):
    '''Return the airtankers cruising speed'''
    cruising = float(inputs.base_airtankers_cruising[base_num][at_num])
    return cruising

def determine_at_fight(base_num, env, inputs, at_num):
    '''Return the airtankers fight fire speed'''
    fight = float(inputs.base_airtankers_fight[base_num][at_num])
    return fight

def determine_at_circling(base_num, env, inputs, at_num):
    '''Return the airtankers circling speed'''
    circling = float(inputs.base_airtankers_circling[base_num][at_num])
    return circling

def determine_at_latitude(base_num, env, inputs, at_num):
    '''Return the airtankers latitude'''
    latitude = float(inputs.bases_lat[base_num])
    return latitude

def determine_at_longitude(base_num, env, inputs, at_num):
    '''Return the airtankers longitude'''
    fight = float(inputs.bases_long[base_num])
    return fight

def determine_at_fly_dark(base_num, env, inputs, at_num):
    '''Return if airtankter can fly after dark'''
    return False

def determine_at_drop_type(base_num, env, inputs, at_num):
    '''Return droptype of airtanker: salvo, trail or other'''
    return "salvo"

def determine_at_size(base_num, env, inputs, at_num):
    '''Return size of the airtanker: small or large'''
    return "small"

def determine_at_after_fire_prot(base_num, env, inputs, at_num):
    '''Return 0 for return to home base, 1 return closest base, 2 stay fire'''
    return 2

def determine_at_fuel_cap(base_num, env, inputs, at_num):
    '''Return the airtankers fuel capacity'''
    fuel_cap = float(inputs.base_airtankers_fuel_cap[base_num][at_num])
    return fuel_cap

def determine_at_fuel_con(base_num, env, inputs, at_num):
    '''Return the airtankers fuel consumption'''
    fuel_con = float(inputs.base_airtankers_fuel_con[base_num][at_num])
    return fuel_con

def get_airtanker_stats(base_num, env, inputs, at_num):
    '''Return stats for the given airtanker'''
    try:
        cruising = determine_at_cruising(base_num, env, inputs, at_num)
        fight = determine_at_fight(base_num, env, inputs, at_num)
        circling = determine_at_circling(base_num, env, inputs, at_num)
        lat = determine_at_latitude(base_num, env, inputs, at_num)
        lon = determine_at_longitude(base_num, env, inputs, at_num)
        ###CHANGE THESE###
        fly_after_dark = determine_at_fly_dark(base_num, env, inputs, at_num)
        drop_type = determine_at_drop_type(base_num, env, inputs, at_num)
        size = determine_at_size(base_num, env, inputs, at_num)
        after_fire_prot = determine_at_after_fire_prot(base_num, env, inputs, at_num)
        ###CHANGE THESE###
        fuel_cap = determine_at_fuel_cap(base_num, env, inputs, at_num)
        fuel_con = determine_at_fuel_con(base_num, env, inputs, at_num)
        return (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot)
    except IndexError:
        print "Not enough airtanker data entered"
        raise SystemExit
    except ValueError:
        print "Invalid airtanker values entered"
        raise SystemExit

def create_airtankers(base_num, env, inputs):
    '''Return a list of Airtanker objects'''
    airtankers = []
    airtankers_resource =[]
    try:
        num = int(inputs.base_num_airtankers[base_num])
    except (IndexError, ValueError):
        print "Invalid number of airtankers entered"
        raise SystemExit
    for x in xrange (num):
        (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot) = get_airtanker_stats(
                    base_num,env,inputs,x)
        airtankers.append(Airtanker(cruising, fight, circling, lat, lon,
                                    fly_after_dark, drop_type, size, fuel_cap,
                                    fuel_con, after_fire_prot))
        airtankers_resource.append(simpy.Resource(env, capacity=1))
    return airtankers, airtankers_resource

def determine_bd_cruising(base_num, env, inputs, bd_num):
    '''Return the bird dogs cruising speed'''
    cruising = float(inputs.base_bird_dogs_cruising[base_num][bd_num])
    return cruising

def determine_bd_fight(base_num, env, inputs, bd_num):
    '''Return the bird dogs fight fire speed'''
    fight = float(inputs.base_bird_dogs_fight[base_num][bd_num])
    return fight

def determine_bd_circling(base_num, env, inputs, bd_num):
    '''Return the bird dogs circling speed'''
    circling = float(inputs.base_bird_dogs_circling[base_num][bd_num])
    return circling

def determine_bd_latitude(base_num, env, inputs, bd_num):
    '''Return the bird dogs latitude'''
    latitude = float(inputs.bases_lat[base_num])
    return latitude

def determine_bd_longitude(base_num, env, inputs, bd_num):
    '''Return the bird dogs longitude'''
    fight = float(inputs.bases_long[base_num])
    return fight

def determine_bd_fly_dark(base_num, env, inputs, bd_num):
    '''Return if bird dogs can fly after dark'''
    return False

def determine_bd_drop_type(base_num, env, inputs, bd_num):
    '''Return droptype of bird dog: salvo, trail or other'''
    return "salvo"

def determine_bd_size(base_num, env, inputs, bd_num):
    '''Return size of the bird dog: small or large'''
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

def get_bird_dogs_stats(base_num, env, inputs, bd_num):
    '''Return stats for the given bird dog'''
    try:
        cruising = determine_bd_cruising(base_num, env, inputs, bd_num)
        fight = determine_bd_fight(base_num, env, inputs, bd_num)
        circling = determine_bd_circling(base_num, env, inputs, bd_num)
        lat = determine_bd_latitude(base_num, env, inputs, bd_num)
        lon = determine_bd_longitude(base_num, env, inputs, bd_num)
        ###CHANGE THESE###
        fly_after_dark = determine_bd_fly_dark(base_num, env, inputs, bd_num)
        drop_type = determine_bd_drop_type(base_num, env, inputs, bd_num)
        size = determine_bd_size(base_num, env, inputs, bd_num)
        after_fire_prot = determine_bd_after_fire_prot(base_num, env, inputs, bd_num)
        ###CHANGE THESE###
        fuel_cap = determine_bd_fuel_cap(base_num, env, inputs, bd_num)
        fuel_con = determine_bd_fuel_con(base_num, env, inputs, bd_num)
        return (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot)
    except IndexError:
        print "Not enough bird dog data entered"
        raise SystemExit
    except ValueError:
        print "Invalid bird dog values entered"
        raise SystemExit

def create_bird_dogs(base_num, env, inputs):
    '''Return a list of bird dogs as Airtanker objects'''
    bird_dogs = []
    bird_dogs_resource = []
    try:
        num = int(inputs.base_num_bird_dogs[base_num])
    except (IndexError, ValueError):
        print "Invalid number of bird dogs entered"
        raise SystemExit
    for x in xrange(num):
        (cruising, fight, circling, lat, lon, fly_after_dark, drop_type,
                size, fuel_cap, fuel_con, after_fire_prot) =get_bird_dogs_stats(
                    base_num, env, inputs, x)
        bird_dogs.append(Airtanker(cruising, fight, circling, lat, lon,
                                       fly_after_dark, drop_type, size,
                                       fuel_cap, fuel_con, after_fire_prot))
        bird_dogs_resource.append(simpy.Resource(env, capacity=1))
    return bird_dogs, bird_dogs_resource

def get_base_stats(env, inputs, base_num):
    '''Return the stats for each base'''
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
    bases = []
    if type(inputs.num_bases) != int:
        try:
            inputs.num_bases = int(inputs.num_bases)
        except ValueError:
            print "Invalid number of bases value entered"
            raise SystemExit
    for x in xrange(inputs.num_bases):
        lat, lon = get_base_stats(env, inputs, x)
        airtankers, airtankers_resource = create_airtankers(x, env, inputs)
        bird_dogs, bird_dogs_resource = create_bird_dogs(x, env, inputs)
        bases.append(Base(lat, lon, airtankers, airtankers_resource, \
                     bird_dogs, bird_dogs_resource))
    return bases

def update_statistics(stats, fires, bases, points): #add bases statistics
    '''Add fires statistics to stats variable'''
    if len(fires) == 0:
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
        detection_size += fires[x].size_at_detection
        report_size += fires[x].size_at_report
        if x == 0:
            ignition_time += fires[x].time_at_ignition
        else:
            ignition_time += (fires[x].time_at_ignition - \
                             fires[x-1].time_at_ignition)
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
    max_size = max_size / len(fires) #Find average by dividing by num of fires
    detection_size = detection_size / len(fires)
    report_size = report_size / len(fires)
    ignition_time = ignition_time / len(fires)
    try:
        detection_time = detection_time / detection_rate
        report_time = report_time / detection_rate
    except ZeroDivisionError:
        detection_time = 0.0
        report_time = 0.0
    detection_rate = detection_rate / len(fires)
    controlled_rate = controlled_rate / len(fires)
    if controlled_rate != 0:
        control_time = control_time / (controlled_rate * len(fires))
    else:
        control_time = 0
    #Calculate airtanker stats
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
    #Update stats variable by appending to stats variable
    try:
        wait_time = wait_time / (detection_rate * len(fires))
    except ZeroDivisionError:
        wait_time = 0
    stats.average_max_size.append(max_size)
    stats.average_detection_size.append(detection_size)
    stats.average_report_size.append(report_size)
    stats.average_ignition_time.append(ignition_time)
    stats.average_detection_time.append(detection_time)
    stats.average_report_time.append(report_time)
    stats.num_fires.append(len(fires))
    stats.detection_rate.append(detection_rate)
    stats.controlled_rate.append(controlled_rate)
    stats.average_travel_time.append(travel_time)
    stats.average_travel_distance.append(travel_distance)
    stats.average_wait_time.append(wait_time)
    stats.average_control_time.append(control_time)
    stats.average_fight_fire_time.append(fight_fire_time)
    update_points(fires, points)

def update_statistics_small(stats, fires, bases, points): #Use less memory
    '''Add fires statistics to stats variable'''
    if len(fires) == 0:
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
        detection_size += fires[x].size_at_detection
        report_size += fires[x].size_at_report
        if x == 0:
            ignition_time += fires[x].time_at_ignition
        else:
            ignition_time += (fires[x].time_at_ignition - \
                             fires[x-1].time_at_ignition)
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
    max_size = max_size / len(fires) #Find average by dividing by num of fires
    detection_size = detection_size / len(fires)
    report_size = report_size / len(fires)
    ignition_time = ignition_time / len(fires)
    try:
        detection_time = detection_time / detection_rate
        report_time = report_time / detection_rate
    except ZeroDivisionError:
        detection_time = 0.0
        report_time = 0.0
    detection_rate = detection_rate / len(fires)
    controlled_rate = controlled_rate / len(fires)
    if controlled_rate != 0:
        control_time = control_time / (controlled_rate * len(fires))
    else:
        control_time = 0.0
    #Calculate airtanker stats
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
    stats.num_fires[0] += len(fires)
    if len(fires) > stats.num_fires[1] or stats.num_fires[1] == -1:
        stats.num_fires[1] = len(fires)
    if len(fires) < stats.num_fires[2] or stats.num_fires[2] == -1:
        stats.num_fires[2] = len(fires)
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
    try:
        temp1 = (wait_time / (detection_rate * len(fires)))
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
    '''Updates points' burned attribute'''
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
            if CCW_IS_POS:
                theta = bearing - (to_rad(fires[y].head_direction) -
                                   EAST_DIRECTION)
            else:
                theta = bearing + ((to_rad(fires[y].head_direction) +
                                            EAST_DIRECTION))
            fire_dist = ellipse_radius(fires[y].max_head_length,
                                       fires[y].max_flank_length, theta)
            if fire_dist >= point_distance: #burned
                points[x].burned[-1] = 1.0
                break

def human_wait_coef(env, inputs):
    '''Determines the coefficient for waittime based on time of day'''
    return 1.0

def lightning_wait_coef(env.now, inputs):
    '''Determines the coefficient for waittime based on time of day'''
    return 1.0
            
def human_fire_wait_time(env, inputs):
    '''Determines wait time for next fire'''
    num_fires = inputs.human_fires_day
    wait_coef = human_wait_coef(env, inputs)
    mean_time = mean_time_between_fires(env, num_fires)
    wait_time = random.expovariate(1.0/(wait_coef * mean_time))
    return wait_time

def lightning_fire_wait_time(env, inputs):
    '''Determines wait time for next fire'''
    num_fires = inputs.lightning_fires_day
    wait_coef = lightning_wait_coef(env, inputs)
    mean_time = mean_time_between_fires(env, num_fires)
    wait_time = random.expovariate(1.0/(wait_coef * mean_time))
    return wait_time

def human_fire_generator(env, fires, forest, inputs): #fire gen process
    '''Generates a fire every ___ time'''
    while 1:
        wait_time = human_fire_wait_time(env, inputs)
        yield env.timeout(wait_time)
        create_fire(env, fires, forest, inputs, "Human")

def lightning_fire_generator(env, fires, forest, inputs): 
    '''Generates a fire every ___ time'''
    while 1:
        wait_time = lightning_fire_wait_time(env, inputs)
        yield env.timeout(wait_time)
        create_fire(env, fires, forest, inputs, "Lightning")

def get_min_drops(env, fire, airtanker, inputs):
    '''Based on fire size, return a value for the minimum number of drops'''
    return 6

def get_max_drops(env, fire, airtanker, inputs):
    '''Based on fire size, return a value for the maximum number of drops'''
    return 10

def get_number_drops(env, fire, airtanker, inputs):
    '''Determines the number of airtanker drops required to fight a fire'''
    min_drops = get_min_drops(env, fire, airtanker, inputs)
    max_drops = get_max_drops(env, fire, airtanker, inputs)
    num_drops = random.randint(min_drops, max_drops) #Discrete Uniform Distribution
    return num_drops

def get_min_lake_distance(env, fire, airtanker, inputs):
    '''Return minimum possible lake distance from fire'''
    return 15

def get_max_lake_distance(env, fire, airtanker, inputs):
    '''Return Maximum possible lake distance from fire'''
    return 35


def get_lake_distance(env, fire, airtanker, inputs):
    '''Return lake distance'''
    min_distance = get_min_lake_distance(env, fire, airtanker, inputs)
    max_distance = get_max_lake_distance(env, fire, airtanker, inputs)
    return random.uniform(min_distance, max_distance) #Uniform Distribution

def get_time_per_drop(lake_distance, airtanker.fight_speed):
    '''Return the time per drop'''
    return 2.0 * lake_distance / airtanker.fight_airspeed + DROP_TIME


def at_control_fire_time_calc(env, fire, airtanker, inputs):
    '''Determines actual amount of time process waits'''
    num_drops = get_number_drops(env, fire, airtanker, inputs)
    lake_distance = get_lake_distance(env, fire, airtanker, inputs)
    time_per_drop = get_time_per_drop(lake_distance, airtanker.fight_speed)
    time_yield = time_per_drop * num_drops
    return time_yield

def at_control_fire_time(env, fire, airtanker, inputs):
    '''Determines amount of time airtanker spends controlling the fire'''
    time_yield = at_control_fire_time_calc(env, fire, airtanker, inputs)
    if time_yield + env.now > inputs.length_run:
        percent = (inputs.length_run - env.now) / time_yield
    else:
        percent = 1.0
    fire.size = (1.0 - percent * BHE) * fire.size
    fire.perimeter = (1.0 - percent * BHE) * fire.perimeter
    fire.head_length = (1.0 - percent * BHE) * fire.head_length
    fire.flank_length = (1.0 - percent * BHE) * fire.flank_length
    fire.back_length = (1.0 - percent * BHE) * fire.back_length
    yield env.timeout(time_yield)
    airtanker.total_fight_fire_time += time_yield


def fight_fire(env, fire, airtanker, inputs):
    '''Simpy process that is called when an airtanker arrives at a fire'''
    fire.time = env.now
    fire.growth()
    fire.max_perimeter = fire.perimeter
    fire.max_size = fire.size
    fire.max_head_length = fire.head_length
    fire.max_flank_length = fire.flank_length
    fire.max_back_length = fire.back_length
    yield env.process(at_control_fire_time(env, fire, airtanker, inputs))
    fire.controlled = True
    fire.time_at_controlled = env.now

def select_airtanker(fire, bases):
    '''Returns which base and airtanker will be used to fight fire
    Currently chooses closest airtanker'''
    base_num = -2.0
    airtanker_num = -2.0
    if len (bases) < 1: #Check if any bases
        return -1.0, -1.0
    for x in range(len(bases)):
        if len(bases[x].airtankers) > 0:
            break
        if x == (len(bases) - 1):
            return -1.0, -1.0
    for x in xrange (len(bases)): #Finds closest airtanker
        for y in xrange(len(bases[x].airtankers)):
            if bases[x].airtankers_resource[y].count == 1 and base_num == -2.0\
                                                    and airtanker_num == -2.0:
                continue
            elif base_num == -2.0 and airtanker_num == -2.0:
                base_num = x
                airtanker_num = y
                continue
            try:
                if obj_distance(bases[x].airtankers[y], fire) < \
                   obj_distance(bases[base_num].airtankers[airtanker_num],fire):
                    base_num = x
                    airtanker_num = y
            except IndexError:
                continue
    return base_num, airtanker_num

def airtanker_arrival(env, fire, airtanker):
    '''Sets statistics when airtanker arrives at fire'''
    travel_dist = obj_distance(airtanker, fire)
    travel_time = travel_dist / airtanker.cruising_airspeed
    airtanker.longitude = fire.longitude
    airtanker.latitude = fire.latitude
    airtanker.travel_distance += travel_dist
    airtanker.total_travel_distance += travel_dist
    airtanker.travel_time += travel_time
    airtanker.total_travel_time += travel_time
    fire.time_at_airtanker_arrival.append(env.now)
    fire.time = env.now
    fire.growth()
    fire.perimeter_at_airtanker_arrival.append(fire.perimeter)
    fire.size_at_airtanker_arrival.append(fire.size)

def return_airtanker_process(env, bases, travel_time, airtanker,
                             airtanker_resource, fires):
    '''Control the airtanker after it fights a fire'''
    if airtanker_resource.queue is None: #Not in queue for another fire
        #check fuel then do something
        pass
    else:
        #check fuel then do something
        pass
    yield env.timeout(travel_time) #returns airtanker to base
    airtanker.latitude = airtanker.base_lat
    airtanker.longitude = airtanker.base_long
    

def check_fuel(env, bases, airtanker):
    '''Checks current distance/time travelled and if airtanker needs refuel'''
    pass

def calc_needed_fuel(env, bases, airtanker):
    'Return the necessary fuel to go to the fire'''
    pass

def dispatch_airtanker(env, fire, bases, fires, inputs):
    '''Requests an airtanker, then calls fight_fire process'''
    base_num, airtanker_num = select_airtanker(fire, bases)
    time_at_req = env.now
    if base_num == -1.0 or airtanker_num == -1.0: #Simulation has no airtankers
        return
    elif base_num == -2.0 and airtanker_num == -2.0: #All Airtankers are busy
        reqs = []
        reqs_sorted = []
        for x in range(len(bases)):
            reqs_sorted.append([])
            for y in range(len(bases[x].airtankers)):
                temp = bases[x].airtankers_resource.request()
                reqs_sorted[-1].append(temp)
                reqs.append(temp)
        successful_airtanker_dict = yield simpy.events.AnyOf(env, reqs)
        the_airtanker = successful_airtanker_dict.keys()[0] #1st avail airtanker
        for x in range(len(bases)):
            for y in range(len(bases[x].airtankers)):
                if the_airtanker != reqs_sorted[x][y]:
                    bases[x].airtankers_resource[y].release(reqs_sorted[x][y])
                    reqs_sorted[x][y].cancel(None, None, None)
                else:
                    base_num = x #Find which airtanker was chosen
                    airtanker_num = y
        airtanker = bases[base_num].airtankers[airtanker_num]
        wait_time = env.now - time_at_req
        airtanker.total_wait_time += wait_time
        travel_dist = obj_distance(airtanker, fire)
        travel_time = travel_dist / airtanker.cruising_airspeed
        yield env.timeout(travel_time)
        airtanker_arrival(env, fire, airtanker)
        yield env.process(fight_fire(env, fire, \
                                     bases[base_num].airtankers[airtanker_num],
                                     inputs))
        yield env.process(return_airtanker_process(env, bases, travel_time,
            airtanker,bases[base_num].airtankers_resource[airtanker_num],fires))
        bases[x].airtankers_resource[y].release(the_airtanker)        
    else:                
        airtanker = bases[base_num].airtankers[airtanker_num]
        the_resource = bases[base_num].airtankers_resource[airtanker_num]
        with the_resource.request() as req:
            yield req
            wait_time = env.now - time_at_req
            airtanker.total_wait_time += wait_time
            travel_dist = obj_distance(airtanker, fire)
            travel_time = travel_dist / airtanker.cruising_airspeed
            yield env.timeout(travel_time)
            airtanker_arrival(env, fire, airtanker)
            yield env.process(fight_fire(env, fire, airtanker, inputs))
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
    while 1:
        min_report = -1.0
        lowest_fire = -1.0
        for x in xrange(len(fires)):
            if (fires[x].time_at_report < min_report  or min_report == -1.0):
                if fires[x].time_at_report > env.now: 
                    min_report = fires[x].time_at_report
                    lowest_fire = x
                else:
                    continue
        if min_report == -1.0:
            yield env.timeout(inputs.length_run - env.now)
        yield env.timeout(min_report - env.now)
        env.process(dispatch_airtanker(env, fires[lowest_fire],
                                       bases, fires, inputs))

def print_simulation_results(stats, points):
    '''Prints out all of the results obtained from the simulation'''
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
    '''Prints out all of the results obtained from the simulation'''
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

        
def print_fire_info(fires):
    '''Call every fire instance's print_attributes method'''
    for x in xrange(len(fires)):
        print "\nFire ", x + 1, "\n"
        fires[x].print_attributes()

def simulation_day(env, env2, fires, bases, forest, points, stats, inputs):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(human_fire_generator(env, fires, forest, inputs))
    env.process(lightning_fire_generator(env, fires, forest, inputs))
    env.run(until=inputs.length_run)
    env2.process(main_airtanker_process(env2, fires, bases, inputs))
    env2.run(until=inputs.length_run)
    if inputs.save_daily_averages:
        update_statistics(stats, fires, bases, points)
    else:
        update_statistics_small(stats, fires, bases, points)

def define_undefined(inputs):
    '''Gives values for inputs not entered'''
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
    time1 = time.clock()
    inputs = user_input(read_only_values)
    check = check_inputs(inputs)
    if check == -1 or check == -2:
        print "\nImproper Inputs, System Quitting...\n\n"
        return -1
    stats = Statistics()
    if not USE_FOREST_DATA:
        forest = create_forest(inputs)
    else:
        forest = []
    points = create_points(inputs)
    for days in xrange(int(inputs.number_runs)):
        fires = []
        env = simpy.Environment()
        env2 = simpy.Environment()
        bases = create_bases(env2, inputs)
        simulation_day(env, env2, fires, bases, forest, points, stats, inputs)
        if inputs.show_fire_attributes:
            print_fire_info(fires)
    if inputs.save_daily_averages:
        print_simulation_results(stats, points)
    else:
        print_simulation_results_small(stats, points, inputs.number_runs)
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
    main_func(list1)
        
    










    
