from __future__ import division # So int/int can return float
import time # Time
import math # For sqrt function
import random # Generate random times
import simpy # For modeling processes and queues
import matplotlib.pyplot as plt # For Graphing Purposes
import numpy as np # Should improve performance
import multiprocessing

#Airtanker Simple Queueing Model
#Written by Cameron Buttazzoni for the Fire Management Lab
#at the Faculty of Forestry at the University of Toronto.
#THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED FOR OPERATIONAL USE
#Copyright: Cameron Buttazzoni

##length_run = 10000000 # minutes

def time_between_fires(fires_per_hour):
    return 60.0 / fires_per_hour # Minutes

def generate_fire_time(mean_time_between_fires):
    ''' Generates random time time based on exponential distribution'''
    return random.expovariate(1.0 / mean_time_between_fires)

def get_time_interval():
    '''return a time interval that data is tracked at'''
    return 10000

def fire_generator(env, airtankers, mean_time_between_fires,
                   mean_service_time, time_interval, num_fires, wait_times,
                   prob_no_wait):
    '''Generates a fire every mean_time_between_fires minutes'''
    time = time_interval
    count = 0
    while 1:
        wait_time = generate_fire_time(mean_time_between_fires)
        yield env.timeout(wait_time)
        while env.now > time:
            count += 1
            time += time_interval
            num_fires.append(0.0)
            prob_no_wait.append(prob_no_wait[-1])
        env.process(airtanker_process(env, airtankers, mean_service_time,
                                num_fires, wait_times, prob_no_wait, count))


def calc_service_time(mean_service_time):
    '''Calculate service time based on an exponential distribution'''
    return random.expovariate(1.0 / mean_service_time)
    

def airtanker_process(env, airtankers, mean_service_time, num_fires,
                      wait_times, prob_no_wait, index):
    ''' For a fire requests an airtanker to fight '''
    with airtankers.request() as req:
        time1 = env.now
        yield req
        wait_time = env.now - time1
        service_time = calc_service_time(mean_service_time)
        num_fires[index] += 1.0
        wait_times.append(wait_time)
        if wait_time == 0.0:
            prob_no_wait[index] += 1.0
        yield env.timeout(service_time)
    

def simulation_day(env, airtankers, mean_time_between_fires,
                   mean_service_time, time_interval, num_fires, wait_times,
                   prob_no_wait, length_run):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, airtankers, mean_time_between_fires,
                   mean_service_time, time_interval, num_fires, wait_times,
                   prob_no_wait))
    env.run(length_run)
    temp = 0
    for x in range(len(prob_no_wait)):
        temp += num_fires[x]
        prob_no_wait[x] /= temp

def graph_results(wait_times, mean_waits, std_dev_waits, xaxis,
                  prob_no_wait, f_p_h, at, s_t, save_file_location):
    '''Graph the queueing simulation results'''
    fig = plt.figure(figsize=(15, 14))
    fig.suptitle("Fires Per Hour: " + str(f_p_h) + "  Airtankers: " + str(at) +
                 "  Service Rate: " + str(s_t))
    graph1 = fig.add_subplot(6,1,2)
    #graph1.plot(xaxis, wait_times, color="blue", linestyle="dashed")
    graph1.plot(xaxis, mean_waits, color="blue")
    graph1.set_title("Average Wait Time Over Time")
    graph1.set_xlabel('Time (Hours)')
    graph1.set_ylabel('Mean Wait Time (Hours)')
    graph2 = fig.add_subplot(6,1,4)
    graph2.plot(xaxis, std_dev_waits, color="red")
    graph2.set_title("Standard Deviation Over Time")
    graph2.set_xlabel('Time (Hours)')
    graph2.set_ylabel('Standard Deviation (Hours)')
    graph3 = fig.add_subplot(6,1,6)
    graph3.plot(xaxis, prob_no_wait, color="green")
    graph3.set_title("Probability of No Waiting Time")
    graph3.set_xlabel('Time (Hours)')
    graph3.set_ylabel('Probability')
    if save_file_location != '':
        try:
            fig.savefig(save_file_location)
        except IOError:
            print "\nInvalid Save File Location\n"
##    else:
##        plt.show()
    plt.show()
        

def get_stats(wait_times, time_interval, num_fires, array_size):
    '''Return Stats for Graphing'''
    mean_waits = np.zeros(array_size)
    std_dev_waits = np.zeros(array_size)
    xaxis = np.zeros(array_size)
    waits = np.array(wait_times)
    calc_std = np.std
    calc_mean = np.mean
    calc_sum = np.sum
    for x in range(array_size):
        xaxis[x] = x * time_interval / 60.0
        std_dev_waits[x] = calc_std(waits[:int(calc_sum(num_fires[:x+1]))])/60.0
        mean_waits[x] = calc_mean(waits[:int(calc_sum(num_fires[:x+1]))]) / 60.0
    return xaxis, std_dev_waits, mean_waits


def main_func(inputs):
    '''Handles running simulation and printing results'''
    time1 = time.clock()
    #time_interval = get_time_interval()
    print "\nSimulating..."
    time_interval = inputs[4] * 60.0 #hours to mins
    wait_times = []
    num_fires = [0.0]
    prob_no_wait = [0.0]
    env = simpy.Environment()
    mean_time_between_fires = time_between_fires(inputs[0])
    number_airtankers = inputs[1]
    #mean_service_time = inputs[2]
    mean_service_time = time_between_fires(inputs[2]) #from rate to mean time
    length_run = inputs[3] * 60.0 #change hours to mins
    save_file_location = inputs[5]
    airtankers = simpy.Resource(env, capacity = number_airtankers)
    simulation_day(env, airtankers, mean_time_between_fires,
                   mean_service_time, time_interval, num_fires, wait_times,
                   prob_no_wait, length_run)
    temp_time1 = time.clock()
    print "Finished Simulation in:", temp_time1 - time1, "Seconds"
    print "Calculating Simulation Statistics..."
    xaxis, std_dev_waits, mean_waits = get_stats(wait_times, time_interval,
                                                 num_fires, len(num_fires))
    temp_time2 = time.clock()
    print "Got Stats in:", temp_time2 - temp_time1, "Seconds"
    print "Graphing..."
    graphing = multiprocessing.Process(target = graph_results, args =
                    (wait_times, mean_waits, std_dev_waits, xaxis,
                  prob_no_wait, inputs[0], inputs[1], inputs[2],
                  save_file_location))
    graphing.start()
    graphing.join()
    time2 = time.clock()
    print "Graphed in:", time2 - temp_time2, "Seconds"
    print "Total Time:", time2 - time1, "\n"
    

if __name__ == '__main__':
    inputs = [5, 8, 85.71, 2000000, 10000, '']
    main_func(inputs)
