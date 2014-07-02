import math
import random
import simpy
import time
#Airtanker Simulation Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

#Please note that values of -1.0 are unchanged or erroneous values

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                           Read-only Variables (editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#Simulation
number_runs = 1000.0 #Number of "days" simulation repeats
length_run = 1440.0 #minutes
show_fire_attributes = False #If True, shows all of the data for every fire
save_daily_averages = True #If True, save more statistics at the cost of memory

#Weather
FFMC = 90.0 #Used to calculate number of fires per day
ISI = 10.0 #Used to calculate Rate of Spread of Fires

#Forest
min_lat = 0
max_lat = 200
min_long = 0
max_long = 200
num_rows = 10 #Number of forest stands in each row
num_columns = 10 #Number of forest stands in each column
PC = 50.0 #For M1, M2 fuel types, needs 0.0 <= PC <= 100.0
PDF = 50.0 #For M3, M4 fuel types, needs 0.0 <= PDF <= 100.0

#Bases
num_bases = 2
bases_lat = [75, 125] #If len < num_bases, random number n, min_lat <= x <= max_lat
bases_long = [75, 125] #If len < num_bases, random number n, min_long <= x <= max_long
base_num_airtankers = [1, 1] #list of the number of airtankers at each base
base_num_bird_dogs = [0] #list of the number of bird dogs at each base
base_airtankers_cruising = [[3], [4]] #Cruising speed of each airtanker, km/min
base_airtankers_fight = [[2], [3]] #Fight fire flying speed of each airtanker km/min
base_airtankers_circling = [[2], [3]] #circling speed of each airtanker km/min
base_airtankers_max_time = [[500], [500]] #Max mins airtankers fly w/o return to a base
base_airtankers_max_distance = [[500], [500]] #max distance without return to a base km
base_bird_dogs_cruising = [[]] #Bird dogs cruising speed km/min
base_bird_dogs_fight = [[]] #Bird dog speed when at fire km/min
base_bird_dogs_circling = [[]] #Bird dogs circling speed km/min
base_bird_dogs_max_time = [[]] #bird dogs max time without return to a base mins
base_bird_dogs_max_distance = [[]] #bird dogs max distance w/o return to a base

#Random Points
num_points = 6 #Number of points in forest to track
points_lat = [] #If len < num_points, random number n, min_lat <= n <= max_lat
points_long = [] #If len < num_points, random number n, min_long<= n <= max_long

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                       Read-only Variables (non-editable)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
num_stands = num_rows * num_columns

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Classes
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
class Fire:
    def __init__(self, time_at_ignition, time_at_detection, time_at_report,  \
                 slope, time, latitude, longitude, fuel_type, detected):
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
        self.rate_of_growth = calculate_rate_of_growth(fuel_type, slope, ISI)

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

def distance(x1, y1, x2, y2):
    '''Find the Euclidean distance between 2 points'''
    return math.sqrt((x1-x2) ** 2 + (y1 - y2) ** 2)

def obj_distance(obj1, obj2):
    '''Return Euclidean distance between the objects'''
    distance = math.sqrt((obj1.longitude - obj2.longitude) ** 2 + \
                         (obj1.latitude - obj2.latitude) ** 2)
    if isinstance(obj1, Fire):
        pass
    if isinstance(obj2, Fire):
        pass
    return distance

def calculate_rate_of_growth(fuel_type, slope, ISI):
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

def create_forest(): #Generate forest with random stands
    '''Return a list of lists of stands that represent each row in the forest'''
    forest = []
    if type(num_rows) != int:
        print "Please enter num_rows as an integer"
        raise SystemExit
    if type(num_columns) != int:
        print "Please enter num_columns as an integer"
        raise SystemExit
    for x in range (num_rows):
        forest.append([])
        for y in range(num_columns):
            forest[x].append(Forest_stand(generate_fueltype(),generate_slope()))
    return forest

def get_stand_info(lat, lon, forest):
    '''Returns slope and fuel type and given location'''
    lat_stand = len(forest) - int(((lat - min_lat) / (max_lat - min_lat)) * \
                                  len(forest))
    if lat_stand == 0:
        lat_stand = 1
    long_stand = len(forest[0]) - int(((lon - min_long) /(max_long - min_long))\
                                      * len(forest[0]))
    if long_stand == 0:
        long_stand = 1
    return forest[lat_stand - 1][long_stand - 1].fuel_type, \
        forest[lat_stand - 1][long_stand - 1].slope

def create_fire(env, fires, forest):
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
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_long, max_long)
    fuel_type, slope = get_stand_info(lat, lon, forest)
    fires.append(Fire(ig_time, detect_time, report_time, slope, env.now, \
                      lat, lon, fuel_type, detected))
    if detected:
        fires[-1].detect()
    fires[-1].time = length_run #Initally set to grow til end of day
    fires[-1].growth()
    fires[-1].max_radius = fires[-1].radius
    fires[-1].max_size = fires[-1].size

def create_points():
    '''Return a list of points in the forest to track'''
    points = []
    for x in range(num_points):
        try:
            lat = points_lat[x]
        except IndexError:
            lat = random.uniform(min_lat, max_lat)
        try:
            lon = points_long[x]
        except IndexError:
            lon = random.uniform(min_long, max_long)
        points.append(Point(lat, lon))
    return points

def create_airtankers(base_num, env):
    '''Return a list of Airtanker objects'''
    airtankers = []
    airtankers_resource =[]
    try:
        num = int(base_num_airtankers[base_num])
    except (IndexError, ValueError):
        print "Invalid number of airtankers entered"
        raise SystemExit
    for x in range (num):
        try:
            cruising = float(base_airtankers_cruising[base_num][x])
            fight = float(base_airtankers_fight[base_num][x])
            circling = float(base_airtankers_circling[base_num][x])
            lat = float(bases_lat[base_num])
            lon = float(bases_long[base_num])
            max_time = float(base_airtankers_max_time[base_num][x])
            max_distance = float(base_airtankers_max_distance[base_num][x])
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

def create_bird_dogs(base_num, env):
    '''Return a list of bird dogs as Airtanker objects'''
    bird_dogs = []
    bird_dogs_resource = []
    try:
        num = int(base_num_bird_dogs[base_num])
    except (IndexError, ValueError):
        print "Invalid number of bird dogs entered"
        raise SystemExit
    for x in range(num):
        airtankers = []
        try:
            cruising = float(base_bird_dogs_crusing[base_num][x])
            fight = float(base_bird_dogs_fight[base_num][x])
            circling = float(base_bird_dogs_circling[base_num][x])
            lat = float(bases_lat[base_num])
            lon = float(bases_lon[base_num])
            max_time = float(base_bird_dogs_max_time[base_num][x])
            max_distance = float(base_bird_dogs_max_distance[base_num][x])
            bird_dogs.append(Airtanker(cruising, fight, circling, max_time, \
                                        max_distance, lat, lon))
        except IndexError:
            print "Not enough bird dog data entered"
            raise SystemExit
        except ValueError:
            print "Invalid bird dog values entered"
            raise SystemExit
    return bird_dogs, bird_dogs_resource
        
def create_bases(env):
    '''Return a list of bases in the forest'''
    bases = []
    global num_bases
    if type(num_bases) != int:
        try:
            num_bases = int(num_bases)
        except ValueError:
            print "Invalid number of bases value entered"
            raise SystemExit
    for x in range(num_bases):
        try:
            lat = bases_lat[x]
        except IndexError:
            lat = random.uniform(min_lat, max_lat)
            bases_lat.append(lat)
        try:
            lon = bases_long[x]
        except IndexError:
            lon = random.uniform(min_long, max_long)
            bases_long.append(lon)
        try:
            num_airtankers = base_num_airtankers[x]
        except IndexError:
            #num_airtankers = random.uniform(1, 3)
            num_airtankers = 0
            base_num_airtankers.append(0)
        try:
            num_birddogs = base_num_bird_dogs[x]
        except IndexError:
            #num_bird_dogs = 1
            num_bird_dogs = 0
            base_num_bird_dogs.append(0)
        airtankers, airtankers_resource = create_airtankers(x, env)
        bird_dogs, bird_dogs_resource = create_bird_dogs(x, env)
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

def update_points(fires, points):
    '''Updates points' burned attribute'''
    for x in range(len(points)):
        points[x].burned.append(0.0)
        for y in range(len(fires)):
            if obj_distance(fires[y], points[x]) <= fires[y].max_radius:
                points[x].burned[-1] = 1.0
                break

                

def fire_generator(env, fires, forest): #fire generation process
    '''Generates a fire every ___ time'''
    while True:
        wait_time = random.expovariate(1.0/mean_time_between_fires(\
            fires_per_day(FFMC)))
        yield env.timeout(wait_time)
        create_fire(env, fires, forest)

def fight_fire_time(env, fire, airtanker):
    '''Determines amount of time airtanker spends fighting the fire for'''
    yield env.timeout(100)

def fight_fire(env, fire, airtanker):
    '''Simpy process that is called when an airtanker arrives at a fire'''
    fire.time = env.now
    fire.growth()
    fire.max_radius = fire.radius
    fire.max_size = fire.size
    yield env.process(fight_fire_time(env, fire, airtanker))
    fire.controlled = True
    fire.time_at_controlled = env.now
    fire.time = length_run
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

def dispatch_airtanker(env, fire, bases, fires):
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
                                     bases[base_num].airtankers[airtanker_num]))
        #Add function that handles airtanker after fighting a fire

def circling_process(env, bases):
    '''If an airtanker must stop fighting the fire, this func handles it'''
    pass

def bird_dogs_process(env, fires, bases):
    '''Controls bird dogs in simulation'''
    pass

def main_airtanker_process(env, fires, bases):
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
            yield env.timeout(length_run - env.now)
        yield env.timeout(min_report - env.now)
        env.process(dispatch_airtanker(env, fires[lowest_fire], bases, fires))

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

def print_fire_info(fires):
    '''Call every fire instance's print_attributes method'''
    for x in range(len(fires)):
        print "\nFire ", x + 1, "\n"
        fires[x].print_attributes()

def simulation_day(env, env2, fires, bases, forest, points, stats):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, fires, forest))
    env.run(until=length_run)
    env2.process(main_airtanker_process(env2, fires, bases))
    env2.run(until=length_run)
    update_statistics(stats, fires, bases, points)

def main_func(read_only_values):
    '''Main Simulation Program, call to run the program'''
    time1 = time.clock()
    stats = Statistics()
    forest = create_forest()
    points = create_points()
    for days in range(int(number_runs)):
        fires = []
        env = simpy.Environment()
        env2 = simpy.Environment()
        bases = create_bases(env2)
        simulation_day(env, env2, fires, bases, forest, points, stats)
        if show_fire_attributes:
            print_fire_info(fires)
    print_simulation_results(stats, points)
    time2 = time.clock()
    print"\n\nIt took %f seconds to do %d runs!\n\n" %(time2-time1, number_runs)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                Run Simulation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
if __name__ == '__main__':
    time1 = time.clock()
    stats = Statistics()
    forest = create_forest()
    points = create_points()
    for days in range(int(number_runs)):
        fires = []
        env = simpy.Environment()
        env2 = simpy.Environment()
        bases = create_bases(env2)
        simulation_day(env, env2, fires, bases, forest, points, stats)
        if show_fire_attributes:
            print_fire_info(fires)
    print_simulation_results(stats, points)
    time2 = time.clock()
    print"\n\nIt took %f seconds to do %d runs!\n\n" %(time2-time1, number_runs)
        
    


























    
