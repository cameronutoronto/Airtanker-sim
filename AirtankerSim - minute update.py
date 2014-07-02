import math
import random
import simpy
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
number_runs = 2.0 #Number of "days" simulation repeats
length_run = 1440.0 #minutes

#Weather
FFMC = 90.0 #Used to calculate number of fires per day
ISI = 20.0 #Used to calculate Rate of Spread of Fires

#Forest
min_lat = 0
max_lat = 200
min_long = 0
max_long = 200
num_rows = 10 #Number of forest stands in each row
num_columns = 10 #Number of forest stands in each column 

#Bases
num_bases = 3
bases_lat = [] #If len < num_bases, random number n, min_lat <= x <= max_lat
bases_long = [] #If len < num_bases, random number n, min_long <= x <= max_long
base_num_airtankers = [] #list of the number of airtankers at each base
base_num_bird_dogs = [] #list of the number of bird dogs at each base
base_airtankers_cruising = [[]] #Cruising speed of each airtanker
base_airtankers_fight = [[]] #Fight fire flying speed of each airtanker
base_airtankers_circling = [[]] #circling speed of each airtanker
base_airtankers_max_time = [[]] #Max time airtankers fly w/o return to a base
base_airtankers_max_distance = [[]] #max distance without return to a base
base_bird_dogs_cruising = [[]] #Bird dogs cruising speed
base_bird_dogs_fight = [[]] #Bird dog speed when at fire
base_bird_dogs_circling = [[]] #Bird dogs circling speed
base_bird_dogs_max_time = [[]] #bird dogs max time without return to a base
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
        self.rate_of_growth = calculate_rate_of_growth(fuel_type, slope, ISI)

        #airtanker values
        self.size_at_airtanker_arrival = []
        self.radius_at_airtanker_arrival = []
        self.time_at_airtanker_arrival = []
        self.time_at_controlled = -1.0
        self.controlled = False
        self.airtanker_return_time = []


    def growth(self): #assumed fires grow linearly
        if self.time < self.ignition_time:
            self.radius = -1.0
            self.size = -1.0
        else:
            self.radius = (self.time - self.ignition_time) \
                                  * self.rate_of_growth
            self.size = float(math.pi * (self.radius) ** 2)
        


    def detect(self): #Probably not used
        self.time_at_detection = self.time
        self.radius_at_detection = self.rate_of_growth * \
                                   (self.time_at_detection - \
                                    self.time_at_ignition)
        self.area_at_detection = math.pi * (self.radius_at_detection) ** 2

    def report(self): #Probaly not used
        self.time_at_report = self.time
        self.radius_at_report = self.rate_of_growth * \
                                   (self.time_at_report - \
                                    self.time_at_ignition)
        self.area_at_detection = math.pi * (self.radius_at_report) ** 2
    
    def print_attributes(self):
        print "Time Ignited:", self.time_at_ignition
        if self.detected:
            print "Time Detected:", self.time_at_detection
            print "Time Reported:", self.time_at_report
        print "Slope:", self.slope
        print "Time:", self.time
        print "Latitude:", self.latitude
        print "Longitude:", self.longitude
        print "Fuel Type:", self.fuel_type
        print "Fire Was Detected:", self.detected
        if self.detected:
            print "Size When Detected:", self.size_at_detection
            print "Radius When Detected:", self.radius_at_detection
            print "Size When Reported:", self.area_at_report
            print "Radius When Reported:", self.report_radius
        print "Current Radius:", self.current_radius
        print "Current Size:", self.area_now
        print "Rate of Growth", self.rate_of_growth
        print "Fire Was Controlled:", self.controlled
        if self.controlled:
            print "Controlled at Time:", self.time_at_controlled

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
        self.cruising_airspeed = cruising_airspeed 
        self.fight_airspeed = fight_airspeed
        self.circling_speed = circling_speed
        self.latitude = lat
        self.longitude = lon
        self.travel_time = 0.0
        self.total_travel_time = 0.0
        self.travel_distance = 0.0
        self.total_travel_distance = 0.0
        self.total_wait_time = 0.0
        self.total_fight_fire_time = 0.0
        self.max_flight_time = max_flight_time
        self.max_flight_distance = max_flight_distance

class Base:
    def __init__(self, latitude, longitude, airtankers, bird_dogs,
                 airtankers_resource, bird_dogs_resource):
        self.latitude = latitude
        self.longitude = longitude
        self.airtankers = airtankers
        self.bird_dogs = bird_dogs
        self.airtankers_resource = airtankers_resource
        self.bird_dogs_resource = bird_dogs_resource

class Lake: #Assumed circle
    def __init__(self, latitude, longitude, suitable, radius):
        self.latitude = latitude
        self.longitude = longitude
        self.suitable = suitable #If True, can be used by Airtankers
        self.radius = radius


class Forest_stand: 
    def __init__(self, fuel_type, slope):
        self.fuel_type = fuel_type
        self.slope = slope

class Point:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.times_burned = 0.0
        self.burned_flag = False #If True, point was burned
        
    def burned(self):
        self.times_burned += 1.0

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                   Functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def fires_per_day(ffmc):
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

def mean_time_between_fires(fires_per_day):
    '''Return mean time in minutes between fires'''
    fires_per_hour = fires_per_day / 8.0
    return  60.0 / fires_per_hour

def distance(x1, y1, x2, y2):
    '''Find the Euclidean distance between 2 points'''
    return math.sqrt((x1-x2) ** 2 + (y1 - y2) ** 2)

def calculate_rate_of_growth(fuel_type, slope, ISI):
    '''For given fuel type, slope and ISI values, return the rate of growth'''
    if type(ISI) != float and type(ISI) != int:
        print "Invalid ISI value entered"
        raise SystemExit
    if fuel_type == "C1": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C2": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C3": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C4": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C5": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C6": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "C7": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "D1": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "D2": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "M1": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "M2": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "M3": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "M4": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "O1a": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "O1b": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "S1": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "S2": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    elif fuel_type == "S3": #C2 Jack Pine
        return float((1.0 / 1000.0) * 110.0 * \
                     ((1.0 - math.exp(-0.0282 * ISI)) ** 1.5))
    print "Invalid fuel type entered"
    raise SystemExit
    return -1.0

def generate_fueltype():
    '''Use some probability distribution to return fueltypes'''
    fuel_types = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "D1", "D2", "M1",\
                  "M2", "M3", "M4", "O1a", "O1b", "S1", "S2", "S3"]
    return fuel_types[random.randint(0, len(fuel_types) - 1)]#some fuel type

def generate_slope():
    '''Uses some probability distribution to generate a slope'''
    return random.uniform(0, 5)

def create_forest():
    '''Return a list of lists of stands that represent each row in the forest'''
    forest = []
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
    '''Randomly generates a fire and appends it to paramter fires'''
    ig_time = env.now
    detected = True
    if random.random() < 0.8:
        detect_time = random.expovariate(1.0 / 120.0) + ig_time
    else:
        detect_time = -1.0
        detected = False
    if detected:
        report_time = random.expovariate(1.0 / 10.0) + detect_time
    else:
        report_time = -1.0
    lat = random.uniform(min_lat, max_lat)
    lon = random.uniform(min_long, max_long)
    fuel_type, slope = get_stand_info(lat, lon, forest)
    fires.append(Fire(ig_time, detect_time, report_time, slope, env.now, \
                      lat, lon, fuel_type, detected))

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
    airtanker_resource =[]
    try:
        num = int(base_num_airtankers[base_num])
    except (IndexError, ValueError):
        print "Invalid number of airtankers entered"
        raise SystemExit
    for x in range (num):
        try:
            cruising = float(base_airtankers_crusing[base_num][x])
            fight = float(base_airtankers_fight[base_num][x])
            circling = float(base_airtankers_circling[base_num][x])
            lat = float(bases_lat[base_num])
            lon = float(bases_lon[base_num])
            max_time = float(base_airtankers_max_time[base_num][x])
            max_distance = float(base_airtankers_max_distance[base_num][x])
            airtankers.append(Airtanker(cruising, fight, circling, max_time, \
                                        max_distance, lat, lon))
            airtanker_resource.append(env.Resource(env, 1))
        except IndexError:
            print "Not enough airtanker data entered"
            raise SystemExit
        except ValueError:
            print "Invalid airtanker values entered"
            raise SystemExit
    return airtankers, airtanker_resource

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

def update_statistics(stats, fires, bases): #add bases statistics
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
            control_time += fires[x].time_at_controlled
    max_size = max_size / len(fires) #Find average by dividing by num of fires
    detection_size = detection_size / len(fires)
    report_size = report_size / len(fires)
    ignition_time = ignition_time / len(fires)
    detection_time = detection_time / len(fires)
    report_time = report_time / len(fires)
    detection_rate = detection_rate / len(fires)
    controlled_rate = controlled_rate / len(fires)
    #Calculate airtanker stats
    count = 0
    for x in range(len(bases)):
        for y in range(len(bases[x].airtankers)):
            travel_distance += bases[x].airtankers[y].total_travel_distance
            travel_time += bases[x].airtankers[y].total_travel_time
            wait_time += bases[x].airtankers[y].total_wait_time
            fight_fire_time += bases[x].airtankers[y].total_fight_fire_time
            count += 1
    travel_distance = travel_distance / count #Find average 
    travel_time = travel_time / count
    wait_time = wait_time / count
    fight_fire_time = fight_fire_time / count
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
    stats.average_wait_time.append(wait_time)
    stats.average_control_time.append(control_time)
    stats.average_fight_fire_time.append(fight_fire_time)

def fire_generator(env, fires, forest): #fire generation process
    '''Generates a fire every ___ time'''
    while True:
        wait_time = random.expovariate(1.0/mean_time_between_fires(\
            fires_per_day(FFMC)))
        yield env.timeout(wait_time)
        create_fire(env, fires, forest)

def fight_fire(env, fire):
    '''Simpy process that is called when an airtanker arrives at a fire'''
    pass

def dispatch_airtanker(env, fires, bases):
    '''Requests an airtanker, then calls fight_fire process'''
    while(True):
        yield env.timeout(10)

def circling_process(env, bases):
    '''If an airtanker must stop fighting the fire, this func handles it'''
    pass

def bird_dogs_process(env, fires, bases):
    '''Controls bird dogs in simulation'''
    pass

def main_airtanker_process(env, fires, bases):
    '''When a fire is reported, calls the dispatch_airtanker process'''
    requested_fires = []
    while True:
        print env.now
        min_report = -1.0
        lowest_fire = -1.0
        for x in range(len(fires)):
            if ((fires[x].time_at_report < min_report and fires[x].time_at_report\
               != -1.0) or min_report == -1.0):
                if fires[x].time_at_report != -1.0:
                    if x in requested_fires:
                        continue
                    min_report = fires[x].time_at_report
                    lowest_fire = x
                    requested_fires.append(x)
        if min_report > env.now+ 1 or min_report == -1.0:
            yield env.timeout(1)
            continue
##        if min_report == -1.0:
##            yield env.timeout(1)
##            continue
        yield env.timeout(min_report - env.now)
        env.process(dispatch_airtanker(env, fires[lowest_fire], bases))

def print_simulation_results(stats):
    '''Prints out all of the results obtained from the simulation'''
    pass

def simulation_day(env, fires, bases, forest, points, stats):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, fires, forest))
    env.process(main_airtanker_process(env, fires, bases))
    env.run(until=length_run)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#                                Run Simulation
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
if __name__ == '__main__':
    stats = Statistics()
    forest = create_forest()
    points = create_points()
    for days in range(int(number_runs)):
        fires = []
        env = simpy.Environment()
        bases = create_bases(env)
        simulation_day(env, fires, bases, forest, points, stats)
        
        
    


























    
