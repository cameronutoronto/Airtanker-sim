import math
import random
import simpy
import time
import fbpline2
#Airtanker Simulation Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

#Please note that values of -1.0 are unchanged or erroneous values

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                           Read-only Variables (editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
EARTHS_RADIUS = 6371 #KM
class user_input():
    def __init__(self, inputs):
        #Simulation

        #Number of "days" simulation repeats 
        self.number_runs = inputs[0] 
        self.length_run = inputs[1] #minutes
        #If True, shows all of the data for every fire
        self.show_fire_attributes = inputs[2]
        #If True, save more statistics at the cost of memory
        self.save_daily_averages = inputs[3]

        #Weather

        #Used to calculate number of fires per day
        self.FFMC = inputs[4]
        #Used to calculate Rate of Spread of Fires
        self.ISI = inputs[5]

        #Forest

        
        self.min_lat = inputs[6]
        self.max_lat = inputs[7]
        self.min_long = inputs[8]
        self.max_long = inputs[9]
        #Number of forest stands in each row
        self.num_rows = inputs[10]
        #Number of forest stands in each column
        self.num_columns = inputs[11]
        #For M1, M2 fuel types, needs 0.0 <= PC <= 100.0
        self.PC = inputs[12]
        #For M3, M4 fuel types, needs 0.0 <= PDF <= 100.0
        self.PDF = inputs[13]

        #Bases

        
        self.num_bases = inputs[14]
        #If len < num_bases, random number n, min_lat <= x <= max_lat
        self.bases_lat = inputs[15]
        #If len < num_bases, random number n, min_long <= x <= max_long
        self.bases_long = inputs[16]
        #list of the number of airtankers at each base
        self.base_num_airtankers = inputs[17]
        #list of the number of bird dogs at each base
        self.base_num_bird_dogs = inputs[18]
        #Cruising speed of each airtanker, km/min
        self.base_airtankers_cruising=[[inputs[19][x+int(sum(inputs[17][:y]))]\
                                           for x in range(int(inputs[17][y]))]\
                                           for y in range(len(inputs[17]))]
        #Fight fire flying speed of each airtanker km/min
        self.base_airtankers_fight = [[inputs[20][x +int(sum(inputs[17][:y]))]\
                                           for x in range(int(inputs[17][y]))]\
                                           for y in range(len(inputs[17]))]
        #circling speed of each airtanker km/min
        self.base_airtankers_circling =[[inputs[21][x+int(sum(inputs[17][:y]))]\
                                           for x in range(int(inputs[17][y]))]\
                                           for y in range(len(inputs[17]))]
        #Bird dogs cruising speed km/min
        self.base_bird_dogs_cruising = [[inputs[22][x+int(sum(inputs[18][:y]))]\
                                           for x in range(int(inputs[18][y]))]\
                                           for y in range(len(inputs[18]))]
        #Bird dog speed when at fire km/min
        self.base_bird_dogs_fight = [[inputs[23][x +int(sum(inputs[18][:y]))] \
                                           for x in range(int(inputs[18][y]))]\
                                           for y in range(len(inputs[18]))]
        #Bird dogs circling speed km/min
        self.base_bird_dogs_circling = [[inputs[24][x+int(sum(inputs[18][:y]))]\
                                           for x in range(int(inputs[18][y]))]\
                                           for y in range(len(inputs[18]))]
        #Max mins airtankers fly w/o return to a base
        self.base_airtankers_max_time =[[inputs[25][x+int(sum(inputs[17][:y]))]\
                                           for x in range(int(inputs[17][y]))]\
                                           for y in range(len(inputs[17]))]
        #max distance without return to a base km
        self.base_airtankers_max_distance = [[inputs[26]\
                                              [x+int(sum(inputs[17][:y]))]\
                                           for x in range(int(inputs[17][y]))]\
                                           for y in range(len(inputs[17]))]
        #bird dogs max time without return to a base mins
        self.base_bird_dogs_max_time = [[inputs[27][x+int(sum(inputs[18][:y]))]\
                                           for x in range(int(inputs[18][y]))]\
                                           for y in range(len(inputs[18]))]
        #bird dogs max distance w/o return to a base
        self.base_bird_dogs_max_distance = [[inputs[28]\
                                             [x +int(sum(inputs[18][:y]))]\
                                           for x in range(int(inputs[18][y]))]\
                                           for y in range(len(inputs[18]))]


        #Random Points


        #Number of points in forest to track
        self.num_points = inputs[29]
        #If len < num_points, random number n, min_lat <= n <= max_lat
        self.points_lat = inputs[30]
        #If len < num_points, random number n, min_long<= n <= max_long
        self.points_long = inputs[31]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                       Read-only Variables (non-editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
        self.num_stands = self.num_rows * self.num_columns

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Classes
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class Fire:
    def __init__(self, time_at_ignition, time_at_detection, time_at_report,  \
                 slope, time, latitude, longitude, fuel_type, detected, ISI, PDF):
        self.time_at_ignition = time_at_ignition #Time Fire Starts
        self.time_at_detection = time_at_detection #Time Fire is Detected
        self.time_at_report = time_at_report #Time Fire is Reported
        self.slope = slope
        self.time = time
        self.latitude = latitude
        self.longitude = longitude
        self.fuel_type = fuel_type
        self.detected = detected #True if fire is detected, else False
        self.size_at_detection = -1.0
        self.radius_at_detection = -1.0
        self.size_at_report = -1.0
        self.radius_at_report = -1.0
        self.size = 0.0 #Assume fires start as points
        self.radius = 0.0
        self.max_size = 0.0 #largest size of fire
        self.max_radius = 0.0
        self.rate_of_growth = calculate_rate_of_growth(fuel_type, slope, ISI, PDF)

        #airtanker values
        self.size_at_airtanker_arrival = []
        self.radius_at_airtanker_arrival = []
        self.time_at_airtanker_arrival = []
        self.time_at_controlled = -1.0
        self.controlled = False
        self.airtanker_return_time = []


    def growth(self): #assumed fires grow linearly
        if self.time < self.time_at_ignition:
            self.radius = -1.0
            self.size = -1.0
        else:
            self.radius = (self.time - self.time_at_ignition) \
                                  * self.rate_of_growth
            self.size = float(math.pi * (self.radius) ** 2)
        


    def detect(self): #Updates detected and report size + radius
        self.radius_at_detection = self.rate_of_growth * \
                                   (self.time_at_detection - \
                                    self.time_at_ignition)
        self.size_at_detection = math.pi * (self.radius_at_detection) ** 2
        self.radius_at_report = self.rate_of_growth * \
                                   (self.time_at_report - \
                                    self.time_at_ignition)
        self.size_at_report = math.pi * (self.radius_at_report) ** 2
    
    def print_attributes(self): #Print all of the fire's attributes
        print "Time Ignited: %.2f" %self.time_at_ignition
        if self.detected:
            print "Time Detected: %.2f" %self.time_at_detection
            print "Time Reported: %.2f" %self.time_at_report
        print "Slope: %.2f"  %self.slope
        print "Time: %.2f"  %self.time
        print "Latitude: %.2f" %self.latitude
        print "Longitude: %.2f" %self.longitude
        print "Fuel Type:", self.fuel_type
        print "Fire Was Detected:", self.detected
        if self.detected:
            print "Size When Detected: %.2f"  %self.size_at_detection
            print "Radius When Detected: %.2f" %self.radius_at_detection
            print "Size When Reported: %.2f" %self.size_at_report
            print "Radius When Reported: %.2f" %self.radius_at_report
        print "Current Radius: %.2f" %self.radius
        print "Current Size: %.2f"  %self.size
        print "Largest Size: %.2f" %self.max_size
        print "Largest Radius: %.2f" %self.max_radius
        print "Rate of Growth %.4f" %self.rate_of_growth
        print "Fire Was Controlled:", self.controlled
        for x in range(len(self.size_at_airtanker_arrival)):
            try:
                print "Size at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.size_at_airtanker_arrival[x])
                print "Radius at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.radius_at_airtanker_arrival[x])
                print "Time at Airtanker %d Arrival: %4.2f" \
                      %(x + 1, self.time_at_airtanker_arrival[x])
                print "Time of Airtanker %d Return: %4.2f" \
                      %(x + 1, self.airtanker_return_time[x])
            except IndexError:
                pass
        if self.controlled:
            print "Controlled at Time: %.2f" %self.time_at_controlled

class Statistics(): #Has many useful statistics as attributes
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
        
        #Airtanker Stats
        self.average_travel_time = []
        self.average_travel_distance = []
        self.average_wait_time = []
        self.average_fight_fire_time = []
        self.average_control_time = []
    
class Airtanker:
    def __init__(self, cruising_airspeed, fight_airspeed, circling_speed,\
                 max_flight_time, max_flight_distance, lat, lon):
        self.cruising_airspeed = cruising_airspeed #main flight speed
        self.fight_airspeed = fight_airspeed #flight speed when fighting fire
        self.circling_speed = circling_speed #fight speed when circling
        self.latitude = lat
        self.longitude = lon
        self.travel_time = 0.0
        self.total_travel_time = 0.0
        self.travel_distance = 0.0
        self.total_travel_distance = 0.0
        self.total_wait_time = 0.0
        self.total_fight_fire_time = 0.0
        self.max_flight_time = max_flight_time #max time fly w/o return a base
        self.max_flight_distance = max_flight_distance #max distance w/o return

class Base:
    def __init__(self, latitude, longitude, airtankers, airtankers_resource,\
                 bird_dogs, bird_dogs_resource):
        self.latitude = latitude #location
        self.longitude = longitude
        self.airtankers = airtankers #list of airtankers starting at base
        self.bird_dogs = bird_dogs #list of bird dogs starting at base
        self.airtankers_resource = airtankers_resource #airtankers for simpy 
        self.bird_dogs_resource = bird_dogs_resource #bird dogs for simpy

class Lake: #Assumed circle
    def __init__(self, latitude, longitude, suitable, radius): #NOT IMPLEMENTED
        self.latitude = latitude
        self.longitude = longitude
        self.suitable = suitable #If True, can be used by Airtankers
        self.radius = radius


class Forest_stand: #Records fuel type and slope of that part of forest
    def __init__(self, fuel_type, slope):
        self.fuel_type = fuel_type
        self.slope = slope

class Point: #Points to keep track of during simulation
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.burned = []

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def fires_per_day(ffmc): #number of fires in a day only based on FFMC
    '''Calculate the fires in a day based on ffmc'''
    if type(ffmc) != float and type(ffmc) != int:
        print "Invalid ffmc entered"
        raise SystemExit
    if (ffmc <= 70.0):
        return float(ffmc / 70)
    elif ffmc <= 80.0:
        return float((7 * ffmc / 10) - 48)
    elif ffmc > 80.0:
        return float((11 * ffmc / 10) - 80)

def mean_time_between_fires(fires_per_day): #used calculate fire ignition times
    '''Return mean time in minutes between fires'''
    fires_per_hour = fires_per_day / 8.0
    return  60.0 / fires_per_hour

def distance_euc(x1, y1, x2, y2): #NOT USED
    '''Find the Euclidean distance between 2 points'''
    return math.sqrt((x1-x2) ** 2 + (y1 - y2) ** 2)

def distance(x1, y1, x2, y2):
    '''Find the Euclidean distance between 2 points'''
    to_rad = math.pi / 180.0
    lat_diff = (y1 * to_rad) - (y2 * to_rad)
    long_diff = (x1 * to_rad) - (x2 * to_rad)
    lat_diff_2 = lat_diff / 2.0
    long_diff_2 = long_diff / 2.0
    const = 2.0 * EARTHS_RADIUS
    distance = const * math.asin(math.sqrt(math.sin(lat_diff_2) ** 2 + \
                                           (math.cos(y1 * to_rad) *
                                            math.cos(y2 * to_rad) *
                                                    (math.sin(long_diff_2) ** 2\
                                                     ))))

def obj_distance_euc(obj1, obj2): #Not used
    '''Return Euclidean distance between the objects'''
    distance = math.sqrt((obj1.longitude - obj2.longitude) ** 2 + \
                         (obj1.latitude - obj2.latitude) ** 2)
    if isinstance(obj1, Fire):
        pass
    if isinstance(obj2, Fire):
        pass
    return distance

def obj_distance(obj1, obj2):
    '''Return Non-Euclidean distance between the objects'''
    to_rad = math.pi / 180.0
    lat_diff = (obj1.latitude * to_rad) - (obj2.latitude * to_rad)
    long_diff = (obj1.longitude * to_rad) - (obj2.longitude * to_rad)
    lat_diff_2 = lat_diff / 2.0
    long_diff_2 = long_diff / 2.0
    const = 2.0 * EARTHS_RADIUS
    distance = const * math.asin(math.sqrt(math.sin(lat_diff_2) ** 2 + \
                                           (math.cos(obj1.latitude * to_rad) *
                                                    math.cos(obj2.latitude *\
                                                             to_rad) *
                                                    (math.sin(long_diff_2) ** 2\
                                                     ))))
                                                         
    if isinstance(obj1, Fire):
        pass
    if isinstance(obj2, Fire):
        pass
    return distance

def area_ellipse(major_axis, minor_axis):
    '''Return the area of an ellipse'''
    return math.pi * major_axis * minor_axis

def perimeter_ellipse(major_axis, minor_axis):
    '''Return the approximate perimeter of an ellipse'''
    if major_axis >= minor_axis:
	a, b = float(major_axis), float(minor_axis)
    else:
	a, b = float(minor_axis), float(major_axis)
    h = (((a - b) ** 2) / ((a + b) ** 2))
    return math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))

def calculate_rate_of_growth(fuel_type, slope, ISI, PDF):
    '''For given fuel type, slope and ISI values, return the rate of growth
    Most calculated from RSI = a[1 - e^((-b)(ISI))]^c for a,b,c depending on
    the fuel type of the stand. Result in km/min'''
    if type(ISI) != float and type(ISI) != int:
        print "Invalid ISI value entered"
        raise SystemExit
    if fuel_type == "C1": #C1 Spruce-Lichen Woodland
        return float((1.0 / 1000.0) * 90.0 * \
                     ((1.0 - math.exp(-0.0649 * ISI)) ** 4.5))
    elif fuel_type == "C2": #C2 Boreal Spruce
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C3": #C3 Mature Jackpine/Lodgepole Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0444 * ISI)) ** 3.0))
    elif fuel_type == "C4": #C4 Immature Jackpine/Lodgepole Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0293 * ISI)) ** 1.5))
    elif fuel_type == "C5": #C5 Red and White Pine
        return float((1.0 / 1000.0) * 3.0 * \
                     ((1.0 - math.exp(-0.0697 * ISI)) ** 4.0))
    elif fuel_type == "C6": #C6 Pine Plantation
        return float((1.0 / 1000.0) * 30.0 * \
                     ((1.0 - math.exp(-0.0800 * ISI)) ** 3.0))
    elif fuel_type == "C7": #C7 Ponderosa Pine/Douglas Fir
        return float((1.0 / 1000.0) * 45.0 * \
                     ((1.0 - math.exp(-0.0305 * ISI)) ** 2.0))
    elif fuel_type == "D1": #D1 Leafless Aspen
        return float((1.0 / 1000.0) * 30.0 * \
                     ((1.0 - math.exp(-0.0232 * ISI)) ** 1.6))
    elif fuel_type == "D2": #D2 Not Currently Implemented
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "M1": #M1 Boreal Mixedwood - Leafless
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))#INCORRECT
    elif fuel_type == "M2": #M2 Boreal Mixedwood - Green
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5)) #INCORRECT
    elif fuel_type == "M3": #M3 Dead B.Fir Mixedwood - Leafless
        return float((1.0 / 1000.0) * 170.0 * math.exp(-35.0/PDF) * \
                     ((1.0 - math.exp(-(0.082 * math.exp(-36.0/PDF)) * ISI)) **\
                      (1.698 - (0.00303 * PDF))))
    elif fuel_type == "M4": #M4 Dead B.Fir Mixedwood - Green
        return float((1.0 / 1000.0) * 140.0 * math.exp(-33.5 / PDF) *\
                     ((1.0 - math.exp(-0.0404 * ISI)) ** \
                      (3.02 * math.exp(-0.00714 * PDF))))
    elif fuel_type == "O1a": #O1a
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))#INCORRECT
    elif fuel_type == "O1b": #O1b
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5)) #INCORRECT
    elif fuel_type == "S1": #S1 Jack Pine/Lodgepole Pine Slash
        return float((1.0 / 1000.0) * 75.0 * \
                     ((1.0 - math.exp(-0.0297 * ISI)) ** 1.3))
    elif fuel_type == "S2": #S2 Spruce/Balsam Slash
        return float((1.0 / 1000.0) * 40.0 * \
                     ((1.0 - math.exp(-0.0438 * ISI)) ** 1.7))
    elif fuel_type == "S3": #S3 Coastal Cedar/Hemlock/Douglas Fir Slash
        return float((1.0 / 1000.0) * 55.0 * \
                     ((1.0 - math.exp(-0.0829 * ISI)) ** 3.2))
    print "Invalid fuel type entered"
    raise SystemExit
    return -1.0

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
    for x in range (inputs.num_rows):
        forest.append([])
        for y in range(inputs.num_columns):
            forest[x].append(Forest_stand(generate_fueltype(),generate_slope()))
    return forest

def get_stand_info(lat, lon, forest, inputs):
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
        forest[lat_stand - 1][long_stand - 1].slope

def create_fire(env, fires, forest, inputs):
    '''Randomly generates a fire and appends it to parameter fires'''
    ig_time = env.now
    detected = True
    if random.random() < 0.8: #80% Chance fire is detected
        detect_time = random.expovariate(1.0 / 120.0) + ig_time #2 hours detect
    else:
        detect_time = -1.0
        detected = False
    if detected:
        report_time = random.expovariate(1.0 / 10.0) + detect_time#10 min detect
    else:
        report_time = -1.0
    lat = random.uniform(inputs.min_lat, inputs.max_lat)
    lon = random.uniform(inputs.min_long, inputs.max_long)
    fuel_type, slope = get_stand_info(lat, lon, forest, inputs)
    fires.append(Fire(ig_time, detect_time, report_time, slope, env.now, \
                      lat, lon, fuel_type, detected, inputs.ISI, inputs.PDF))
    if detected:
        fires[-1].detect()
    fires[-1].time = inputs.length_run #Initally set to grow til end of day
    fires[-1].growth()
    fires[-1].max_radius = fires[-1].radius
    fires[-1].max_size = fires[-1].size

def create_points(inputs):
    '''Return a list of points in the forest to track'''
    points = []
    for x in range(inputs.num_points):
        try:
            lat = inputs.points_lat[x]
        except IndexError:
            lat = random.uniform(inputs.min_lat, inputs.max_lat)
        try:
            lon = inputs.points_long[x]
        except IndexError:
            lon = random.uniform(inputs.min_long, inputs.max_long)
        points.append(Point(lat, lon))
    return points

def create_airtankers(base_num, env, inputs):
    '''Return a list of Airtanker objects'''
    airtankers = []
    airtankers_resource =[]
    try:
        num = int(inputs.base_num_airtankers[base_num])
    except (IndexError, ValueError):
        print "Invalid number of airtankers entered"
        raise SystemExit
    for x in range (num):
        try:
            cruising = float(inputs.base_airtankers_cruising[base_num][x])
            fight = float(inputs.base_airtankers_fight[base_num][x])
            circling = float(inputs.base_airtankers_circling[base_num][x])
            lat = float(inputs.bases_lat[base_num])
            lon = float(inputs.bases_long[base_num])
            max_time = float(inputs.base_airtankers_max_time[base_num][x])
            max_distance=float(inputs.base_airtankers_max_distance[base_num][x])
            airtankers.append(Airtanker(cruising, fight, circling, max_time, \
                                        max_distance, lat, lon))
            airtankers_resource.append(simpy.Resource(env, capacity=1))
        except IndexError:
            print "Not enough airtanker data entered"
            raise SystemExit
        except ValueError:
            print "Invalid airtanker values entered"
            raise SystemExit
    return airtankers, airtankers_resource

def create_bird_dogs(base_num, env, inputs):
    '''Return a list of bird dogs as Airtanker objects'''
    bird_dogs = []
    bird_dogs_resource = []
    try:
        num = int(inputs.base_num_bird_dogs[base_num])
    except (IndexError, ValueError):
        print "Invalid number of bird dogs entered"
        raise SystemExit
    for x in range(num):
        try:
            cruising = float(inputs.base_bird_dogs_crusing[base_num][x])
            fight = float(inputs.base_bird_dogs_fight[base_num][x])
            circling = float(inputs.base_bird_dogs_circling[base_num][x])
            lat = float(inputs.bases_lat[base_num])
            lon = float(inputs.bases_lon[base_num])
            max_time = float(inputs.base_bird_dogs_max_time[base_num][x])
            max_distance =float(inputs.base_bird_dogs_max_distance[base_num][x])
            bird_dogs.append(Airtanker(cruising, fight, circling, max_time, \
                                        max_distance, lat, lon))
        except IndexError:
            print "Not enough bird dog data entered"
            raise SystemExit
        except ValueError:
            print "Invalid bird dog values entered"
            raise SystemExit
    return bird_dogs, bird_dogs_resource
        
def create_bases(env, inputs):
    '''Return a list of bases in the forest'''
    bases = []
    if type(inputs.num_bases) != int:
        try:
            inputs.num_bases = int(inputs.num_bases)
        except ValueError:
            print "Invalid number of bases value entered"
            raise SystemExit
    for x in range(inputs.num_bases):
        try:
            lat = inputs.bases_lat[x]
        except IndexError:
            lat = random.uniform(inputs.min_lat, inputs.max_lat)
            inputs.bases_lat.append(lat)
        try:
            lon = inputs.bases_long[x]
        except IndexError:
            lon = random.uniform(inputs.min_long, inputs.max_long)
            inputs.bases_long.append(lon)
        try:
            num_airtankers = inputs.base_num_airtankers[x]
        except IndexError:
            #num_airtankers = random.uniform(1, 3)
            num_airtankers = 0
            inputs.base_num_airtankers.append(0)
        try:
            num_birddogs = inputs.base_num_bird_dogs[x]
        except IndexError:
            #num_bird_dogs = 1
            num_bird_dogs = 0
            inputs.base_num_bird_dogs.append(0)
        airtankers, airtankers_resource = create_airtankers(x, env, inputs)
        bird_dogs, bird_dogs_resource = create_bird_dogs(x, env, inputs)
        bases.append(Base(lat, lon, airtankers, airtankers_resource, \
                     bird_dogs, bird_dogs_resource))
    return bases

def update_statistics(stats, fires, bases, points): #add bases statistics
    '''Add fires statistics to stats variable'''
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
    for x in range(len(fires)): #Increase each value by the amount for a fire
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
    detection_time = detection_time / detection_rate
    report_time = report_time / detection_rate
    detection_rate = detection_rate / len(fires)
    controlled_rate = controlled_rate / len(fires)
    control_time = control_time / (controlled_rate * len(fires))
    #Calculate airtanker stats
    count = 0
    for x in range(len(bases)):
        for y in range(len(bases[x].airtankers)):
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
    stats.average_wait_time.append(wait_time / (detection_rate * len(fires)))
    stats.average_control_time.append(control_time)
    stats.average_fight_fire_time.append(fight_fire_time)
    update_points(fires, points)

def update_statistics_small(stats, fires, bases, points): #Use less memory
    '''Add fires statistics to stats variable'''
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
    for x in range(len(fires)): #Increase each value by the amount for a fire
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
    detection_time = detection_time / detection_rate
    report_time = report_time / detection_rate
    detection_rate = detection_rate / len(fires)
    controlled_rate = controlled_rate / len(fires)
    control_time = control_time / (controlled_rate * len(fires))
    #Calculate airtanker stats
    count = 0
    for x in range(len(bases)):
        for y in range(len(bases[x].airtankers)):
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
    for x in range (2):
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
    stats.average_max_size[0] += max_size
    if max_size > stats.average_max_size[1] or stats.average_max_size[1] == -1:
        stats.average_max_size[1] = max_size
    if max_size < stats.average_max_size[2] or stats.average_max_size[2] == -1:
        stats.average_max_size[2] = max_size
    stats.average_detection_size[0] += detection_size
    if detection_size > stats.average_detection_size[1] or \
       stats.average_detection_size[1] == -1:
        stats.average_detection_size[1] = detection_size
    if detection_size < stats.average_detection_size[2] or \
       stats.average_detection_size[2] == -1:
        stats.average_detection_size[2] = detection_size
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
    temp1 = (wait_time / (detection_rate * len(fires)))
    stats.average_wait_time[0] += (wait_time / (detection_rate * len(fires)))
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
    for x in range(len(points)):
        points[x].burned.append(0.0)
        for y in range(len(fires)):
            if obj_distance(fires[y], points[x]) <= fires[y].max_radius:
                points[x].burned[-1] = 1.0
                break

                

def fire_generator(env, fires, forest, inputs): #fire generation process
    '''Generates a fire every ___ time'''
    while True:
        wait_time = random.expovariate(1.0/mean_time_between_fires(\
            fires_per_day(inputs.FFMC)))
        yield env.timeout(wait_time)
        create_fire(env, fires, forest, inputs)

def fight_fire_time(env, fire, airtanker):
    '''Determines amount of time airtanker spends fighting the fire for'''
    time_yield = 100
    yield env.timeout(time_yield)
    airtanker.total_fight_fire_time += time_yield

def fight_fire(env, fire, airtanker, inputs):
    '''Simpy process that is called when an airtanker arrives at a fire'''
    fire.time = env.now
    fire.growth()
    fire.max_radius = fire.radius
    fire.max_size = fire.size
    yield env.process(fight_fire_time(env, fire, airtanker))
    fire.controlled = True
    fire.time_at_controlled = env.now
    fire.time = inputs.length_run
    fire.size = 0.0
    fire.radius = 0.0

def select_airtanker(fire, bases):
    '''Returns which base and airtanker will be used to fight fire
    Currently chooses closest airtanker'''
    if len (bases) >= 1 and len(bases[0].airtankers) >= 1:
        base_num = 0
        airtanker_num = 0
    else:
        return -1.0, -1.0
    for x in range (len(bases)): #Finds closest airtanker
        for y in range(len(bases[x].airtankers)):
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
    fire.radius_at_airtanker_arrival.append(fire.radius)
    fire.size_at_airtanker_arrival.append(fire.size)

def return_airtanker_process(env, bases, airtanker, airtanker_resource, fires):
    '''Control the airtanker after it fights a fire'''
    if airtanker_resource.queue == None: #Not in queue for another fire
        #check fuel then do something
        pass
    else:
        #check fuel then do something
        pass

def check_fuel(env, bases, airtanker):
    '''Checks current distance/time travelled and if airtanker needs refuel'''
    pass

def dispatch_airtanker(env, fire, bases, fires, inputs):
    '''Requests an airtanker, then calls fight_fire process'''
    base_num, airtanker_num = select_airtanker(fire, bases)
    if base_num == -1.0 or airtanker_num == -1.0: #Simulation has no airtankers
        return
    airtanker = bases[base_num].airtankers[airtanker_num]
    time_at_req = env.now
    with bases[base_num].airtankers_resource[airtanker_num].request() as req:
        yield req
        wait_time = env.now - time_at_req
        airtanker.total_wait_time += wait_time
        travel_dist = obj_distance(airtanker, fire)
        travel_time = travel_dist / airtanker.cruising_airspeed
        yield env.timeout(travel_time)
        airtanker_arrival(env, fire, airtanker)
        yield env.process(fight_fire(env, fire, \
                                     bases[base_num].airtankers[airtanker_num],
                                     inputs))
        #Add function that handles airtanker after fighting a fire

def circling_process(env, bases):
    '''If an airtanker must stop fighting the fire, this func handles it'''
    pass

def bird_dogs_process(env, fires, bases):
    '''Controls bird dogs in simulation'''
    pass

def main_airtanker_process(env, fires, bases, inputs):
    '''When a fire is reported, calls the dispatch_airtanker process'''
    while True:
        min_report = -1.0
        lowest_fire = -1.0
        for x in range(len(fires)):
            if (fires[x].time_at_report < min_report  or min_report == -1.0):
                if fires[x].time_at_report > env.now: 
                    min_report = fires[x].time_at_report
                    lowest_fire = x
                else:
                    continue
        if min_report == -1.0:
            yield env.timeout(inputs.length_run - env.now)
        yield env.timeout(min_report - env.now)
        env.process(dispatch_airtanker(env, fires[lowest_fire], bases, fires, inputs))

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
    for x in range(len(points)):
        print"\nPoint %d\n\n" %(x + 1)
        print"Longitude: %2.2f" %points[x].longitude
        print "Latitude: %2.2f" %points[x].latitude
        print "Percent of days burned: %2.1f%%" \
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
    for x in range(len(points)):
        print"\nPoint %d\n\n" %(x + 1)
        print"Longitude: %2.2f" %points[x].longitude
        print "Latitude: %2.2f" %points[x].latitude
        print "Percent of days burned: %2.1f%%" \
              %(sum(points[x].burned) * 100.0 / len(points[x].burned))

        
def print_fire_info(fires):
    '''Call every fire instance's print_attributes method'''
    for x in range(len(fires)):
        print "\nFire ", x + 1, "\n"
        fires[x].print_attributes()

def simulation_day(env, env2, fires, bases, forest, points, stats, inputs):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, fires, forest, inputs))
    env.run(until=inputs.length_run)
    env2.process(main_airtanker_process(env2, fires, bases, inputs))
    env2.run(until=inputs.length_run)
    if inputs.save_daily_averages:
        update_statistics(stats, fires, bases, points)
    else:
        update_statistics_small(stats, fires, bases, points)

def define_undefined(inputs):
    '''Gives values for inputs not entered'''
    if inputs.number_runs == None:
        print "Value of 1 assigned to number of runs\n"
        inputs.number_runs = 1
    if inputs.length_run == None:
        print "Value of 1440 minutes assigned to length of run\n"
        inputs.length_run = 1440.0
    if inputs.show_fire_attributes == None:
        print "Value of True assigned to Show Fire Attributes\n"
        inputs.show_fire_attributes = True
    if inputs.save_daily_averages == None:
        print "Value of True assigned to save daily averages\n"
        inputs.save_daily_averages = True
    if inputs.FFMC == None:
        print "Value of 80.0 assigned to FFMC\n"
        inputs.FFMC = 80.0
    if inputs.ISI == None:
        print "Value of 15.0 assigned to ISI\n"
        inputs.ISI == 15.0
    if inputs.min_lat == None:
        print "Value of 0 assigned to minimum latitude\n"
        inputs.min_lat = 0
    if inputs.max_lat == None:
        print "Value of 200 assigned to maximum latitude\n"
        inputs.max_lat = 200
    if inputs.min_long == None:
        print "Value of 0 assigned to minimum longitude\n"
        inputs.min_long = 0
    if inputs.max_long == None:
        print "Value of 200 assigned to maximum longitude\n"
        inputs.max_long = 200


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
            print "\nFFMC Value Out of Range\n\n"
            return -1
    else:
        print "Invalid FFMC Value Entered"
        return -2
    if type(inputs.ISI) == float or type(inputs.ISI) == int:
        inputs.ISI = float(inputs.ISI)
        if inputs.ISI < 0 or inputs.ISI > 50:
            print "\nISI Value Out of Range\n\n"
            return -1
    else:
        print "Invalid ISI Value Entered\n\n"
        return -2
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
    for x in range(inputs.num_bases):
        if type(inputs.bases_lat[x]) == float or type(inputs.bases_lat[x])==int:
            inputs.bases_lat[x] = float(inputs.bases_lat[x])
            if inputs.bases_lat[x] < -90.0 or inputs.bases_lat[x] > 90.0:
                print "\nBase %d Latitude Out of Range\n\n" %(x + 1)
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
        if inputs.base_num_airtankers[x] != \
           len(inputs.base_airtankers_max_time[x]):
            print "\nNumber of Airtankers and Max Time Don't Match\n\n"
            return -1
        if inputs.base_num_airtankers[x] != \
           len(inputs.base_airtankers_max_distance[x]):
            print "\nNumber of Airtankers and Max Distance Don't Match\n\n"
            return -1
        for y in range(inputs.base_num_airtankers[x]):
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
            temp = inputs.base_airtankers_max_time[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nAirtanker Max Time Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Airtanker Max Time\n\n"
                return -2
            temp = inputs.base_airtankers_max_distance[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nAirtanker Max Time Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Airtanker Max Distance\n\n"
                return -2
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
        if inputs.base_num_bird_dogs[x]!=len(inputs.base_bird_dogs_max_time[x]):
            print "\nNumber of Bird Dogs and Max Times Don't Match\n\n"
            return -1
        if inputs.base_num_bird_dogs[x] != \
           len(inputs.base_bird_dogs_max_distance[x]):
            print "\nNumber of Bird Dogs and Max Distances Don't Match\n\n"
            return -1
        for y in range(inputs.base_num_bird_dogs[x]):
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
            temp = inputs.base_bird_dogs_max_time[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nBird Dog Max Time Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Bird Dog Max Time\n\n"
                return -2
            temp = inputs.base_bird_dogs_max_distance[x][y]
            if type(temp) == float or type(temp) == int:
                temp = float(temp)
                if temp < 0.0:
                    print "\nBird Dog Max Distance Out of Range\n\n"
                    return -1
            else:
                print "\nInvalid Bird Dog Max Distance\n\n"
                return -2
    #Points Check
    if type(inputs.num_points) == float or type(inputs.num_points) == int:
        inputs.num_points = int(inputs.num_points)
        if inputs.num_points < 0:
            print "Number of Points Out of Range\n\n"
            return -1
    else:
        print "Invalid Number of Points"
        return -2
    if inputs.num_points != len(inputs.points_lat):
        print "\nNumber of Points and Point Latitudes Don't Match\n\n"
        return -1
    if inputs.num_points != len(inputs.points_long):
        print "\nNumber of Points and Point Longitudes Don't Match\n\n"
        return -1
    for x in range(inputs.num_points):
        if type(inputs.points_lat[x])==float or type(inputs.points_lat[x])==int:
            inputs.points_lat = float(inputs.points_lat)
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
    forest = create_forest(inputs)
    points = create_points(inputs)
    for days in range(int(inputs.number_runs)):
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
    list1 = [0 for x in range (32)]
    list1[0] = 1
    list1[1] = 1440.0
    for y in range(17, 29):
        list1[y] = []
    main_func(list1)
        
    


























    
