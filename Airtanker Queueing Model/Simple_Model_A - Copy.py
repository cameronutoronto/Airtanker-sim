#from __future__ import division # So int/int can return float
import time # Time
time1 = time.clock()
import math # For sqrt function
import random # Generate random times
import simpy # For modeling processes and queues
import matplotlib.pyplot as plt # For Graphing Purposes
import numpy as np # Should improve performance

#Airtanker Simple Queueing Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

length_run = 40000000 # minutes

class Fire(object):
    def __init__(self, ignition_time):
        self.ignition_time = ignition_time
        self.wait_time = -1.0
        self.controlled_time = -1.0

def calc_mean(list1):
    '''Return list of all the means'''
    mean = 0.0
    new_list = []
    for x in range(len(list1)):
        mean += list1[x]
        new_list.append(mean / (x + 1))
    return new_list

##def calc_std_dev(list1, mean_list):
##    '''Return list of all the standard deviations'''
##    std_dev = 0.0
##    new_list = []
##    for x in range(len(list1)):
##        std_dev += (list1[x] - mean_list[x]) ** 2
        

def calc_std_dev(list1, mean):
    '''Return the standard deviation'''
    std_dev = 0.0
    for element in list1:
        std_dev += (element - mean) ** 2
    return math.sqrt(std_dev / len(list1))

def time_between_fires(fires_per_hour):
    return 60.0 / fires_per_hour # Minutes

def generate_fire_time(mean_time_between_fires):
    ''' Generates random time time based on exponential distribution'''
    return random.expovariate(1.0 / mean_time_between_fires)

def get_time_interval():
    '''return a time interval that data is tracked at'''
    return 500

def fire_generator(env, fires, airtankers, mean_time_between_fires,
                   mean_service_time):
    '''Generates a fire every mean_time_between_fires minutes'''
    while 1:
        wait_time = generate_fire_time(mean_time_between_fires)
        yield env.timeout(wait_time)
        fires.append(Fire(env.now))
        env.process(airtanker_process(env, fires[-1], airtankers,
                                      mean_service_time))


def calc_service_time(mean_service_time):
    '''Calculate service time based on an exponential distribution'''
    return random.expovariate(1.0 / mean_service_time)
    

def airtanker_process(env, fire, airtankers, mean_service_time):
    ''' For a fire requests an airtanker to fight '''
    with airtankers.request() as req:
        time1 = env.now
        yield req
        wait_time = env.now - time1
        fire.wait_time = wait_time
        service_time = calc_service_time(mean_service_time)
        fire.controlled_time = service_time
        yield env.timeout(service_time)
    

def simulation_day(env, fires, mean_time_between_fires, airtankers,
                   mean_service_time):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, fires, airtankers, mean_time_between_fires,
                               mean_service_time))
    env.run(length_run)

def graph_results(ig_times, wait_times, mean_waits, std_dev_waits, xaxis,
                  prob_no_wait, f_p_h, at, s_t):
    '''Graph the queueing simulation results'''
    fig = plt.figure(figsize=(15, 14))
    fig.suptitle("Fires Per Hour: " + str(f_p_h) + "  Airtankers: " + str(at) +
                 "  Service Time: " + str(s_t))
    graph1 = fig.add_subplot(6,1,2)
    #graph1.plot(xaxis, wait_times, color="blue", linestyle="dashed")
    graph1.plot(xaxis, mean_waits, color="blue")
    graph1.set_title("Average Wait Time over Time")
    graph1.set_xlabel('Time')
    graph1.set_ylabel('Mean Wait Time')
    graph2 = fig.add_subplot(6,1,4)
    graph2.plot(xaxis, std_dev_waits, color="red")
    graph2.set_title("Standard Deviation over Time")
    graph2.set_xlabel('Time')
    graph2.set_ylabel('Standard Deviation')
    graph3 = fig.add_subplot(6,1,6)
    graph3.plot(xaxis, prob_no_wait, color="green")
    graph3.set_title("Probability of no Waiting")
    graph3.set_xlabel('Time')
    graph3.set_ylabel('Probability')
    fig.savefig("tempfigplot.png")

def find_controlled_fires(fires, ig_times, wait_times, time_interval):
    '''Goes through fires and handles all handled ones
        returns list of probabilities of no wait'''
    time = time_interval
    prob_no_wait = [0.0]
    for x in range(len(fires)):
        if fires[x].controlled_time != -1.0:
            ig_times.append(fires[x].ignition_time)
            wait_times.append(fires[x].wait_time)
            while ig_times[-1] > time:
                prob_no_wait[-1] /= (x + 1)
                prob_no_wait.append(prob_no_wait[-1] * (x + 1))
                time += time_interval
            if wait_times[-1] == 0:
                prob_no_wait[-1] += 1.0
    return prob_no_wait[:-1]

def get_stats(wait_times, ig_times, time_interval, array_size):
    '''Return Stats for Graphing'''
    mean_waits = np.zeros(array_size)
    std_dev_waits = np.zeros(array_size)
    xaxis = np.zeros(array_size)
    waits = np.zeros(len(wait_times))
    time = time_interval
    count = 0
    calc_std = np.std
    calc_mean = np.mean
    for x in range(array_size):
        try:
            while ig_times[count] < time:
                waits[x] += wait_times[count]
                count += 1
        except IndexError:
            pass
        time += time_interval
        xaxis[x] = x * time_interval
##        std_dev_waits[x] = np.std(waits[:x+1])
##        mean_waits[x] = np.mean(waits[:x+1])
        std_dev_waits[x] = calc_std(waits[:x+1])
        mean_waits[x] = calc_mean(waits[:x+1])
    return xaxis, std_dev_waits, mean_waits
        
            
    


def main_func(inputs):
    '''Handles running simulation and printing results'''
    time_interval = get_time_interval()
    fires = []
    ig_times = []
    wait_times = []
    env = simpy.Environment()
    mean_time_between_fires = time_between_fires(inputs[0])
    number_airtankers = inputs[1]
    mean_service_time = inputs[2]
    airtankers = simpy.Resource(env, capacity = number_airtankers)
    simulation_day(env, fires, mean_time_between_fires, airtankers,
                   mean_service_time)
    print "Finished Simulation"
    prob_no_wait = find_controlled_fires(fires, ig_times, wait_times,
                                          time_interval)
    print "Sorted Controlled Fires"
    xaxis, std_dev_waits, mean_waits = get_stats(wait_times, ig_times,
                                            time_interval, len(prob_no_wait))
    print "Got Stats"
    graph_results(ig_times, wait_times, mean_waits, std_dev_waits, xaxis,
                  prob_no_wait, inputs[0], inputs[1], inputs[2])
    time2 = time.clock()
    print time2 - time1
##    print len(ig_times), len(wait_times), len(mean_waits), len(std_dev_waits)
##    print ig_times
##    print wait_times
##    print mean_waits
##    print std_dev_waits
##    print prob_no_wait
    

if __name__ == '__main__':
    inputs = [2, 1, 29]
    main_func(inputs)
