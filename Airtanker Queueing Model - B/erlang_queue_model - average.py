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

class Parameters(object):
    def __init__(self, inputs):
        self.time_interval = inputs[3] * 60.0 #hours to mins
        self.wait_times = []
        self.service_times = []
        self.mean_time_between_fires = time_between_fires(inputs[0])
        self.number_airtankers = inputs[1]
        self.length_run = inputs[2] * 60.0 #change hours to mins
        self.num_fires = [0.0 for x in range(int(math.ceil(self.length_run /
                                                    self.time_interval)))]
        self.save_file_location = inputs[4]
        self.alpha_t = get_alpha_t(inputs[5])
        self.beta_t = get_beta_t(inputs[6])
        self.alpha_s = get_alpha_s(inputs[7])
        self.beta_s = get_beta_s(inputs[8])
        self.alpha_r = get_alpha_r(inputs[9])
        self.beta_r = get_beta_r(inputs[10])

class Outputs(object):
    def __init__(self, intervals):
        self.xaxis = [0.0 for x in range(intervals)]
        self.mean_waits = [0.0 for x in range(intervals)]
        self.mean_service = [0.0 for x in range(intervals)]
        self.mean_waits_continuous = [0.0 for x in range(intervals)]
        self.prob_no_wait = [0.0]

def time_between_fires(fires_per_hour):
    return 60.0 / fires_per_hour # Minutes

def generate_fire_time(mean_time_between_fires):
    ''' Generates random time time based on exponential distribution'''
    return random.expovariate(1.0 / mean_time_between_fires)

def generate_gamma_time(alpha, beta):
    '''Uses erlang distribution to generate a random gamma time'''
    return random.gammavariate(alpha, beta)

def get_time_interval():
    '''return a time interval that data is tracked at'''
    return 10000

def get_alpha_t(num):
    return num

def get_beta_t(num):
    return num

def get_alpha_s(num):
    return num

def get_beta_s(num):
    return num

def get_alpha_r(num):
    return num

def get_beta_r(num):
    return num

def fire_generator(env, airtankers, parameters, outputs):
    '''Generates a fire every mean_time_between_fires minutes'''
    time = parameters.time_interval
    count = 0
    while 1:
        wait_time = generate_fire_time(parameters.mean_time_between_fires)
        yield env.timeout(wait_time)
        while env.now > time:
            count += 1
            time += parameters.time_interval
            outputs.prob_no_wait.append(outputs.prob_no_wait[-1])
        env.process(airtanker_process(env, airtankers, parameters,
                                      outputs, count))


def calc_service_time(mean_service_time):
    '''Calculate service time based on an exponential distribution'''
    return random.expovariate(1.0 / mean_service_time)
    

def airtanker_process(env, airtankers, parameters, outputs, index):
    ''' For a fire requests an airtanker to fight '''
    with airtankers.request() as req:
        time1 = env.now
        yield req
        wait_time = env.now - time1
        if wait_time == 0.0:
            outputs.prob_no_wait[index] += 1.0
        travel_time = generate_gamma_time(parameters.alpha_t, parameters.beta_t)
        scene_time = generate_gamma_time(parameters.alpha_s, parameters.beta_s)
        return_time = generate_gamma_time(parameters.alpha_r, parameters.beta_r)
        service_time = travel_time + scene_time + return_time
        outputs.mean_waits[int(env.now / parameters.time_interval)] += \
                                           wait_time
        outputs.mean_service[int(env.now / parameters.time_interval)] += \
                                              service_time
        parameters.num_fires[int(env.now / parameters.time_interval)] += 1.0
        yield env.timeout(service_time)
    

def simulation_day(env, airtankers, parameters, outputs):
    '''Main simulation function, runs whole simulation for one day'''
    env.process(fire_generator(env, airtankers, parameters, outputs))
    env.run(parameters.length_run)
    temp = 0
    for x in xrange(len(outputs.prob_no_wait)):
        temp += parameters.num_fires[x]
        try:
            outputs.prob_no_wait[x] /= temp
        except ZeroDivisionError:
            pass

def graph_results(outputs, f_p_h, at, s_t, save_file_location):
    '''Graph the queueing simulation results'''
    fig = plt.figure(figsize=(20, 18))
    fig.suptitle("Fires Per Hour: " + str(f_p_h) + "  Airtankers: " + str(at) +
                 "  Mean Service Rate: " + s_t + " Mean Wait Time:" +
                 "%1.4f" %outputs.mean_waits[-1])
    graph1 = fig.add_subplot(8,1,2)
    #graph1.plot(xaxis, wait_times, color="blue", linestyle="dashed")
    graph1.plot(outputs.xaxis, outputs.mean_waits, color="blue")
    graph1.set_title("Average Wait Time Over Time")
    graph1.set_xlabel('Time (Hours)')
    graph1.set_ylabel('Mean Wait Time (Hours)')
    graph2 = fig.add_subplot(8,1,4)
    graph2.plot(outputs.xaxis, outputs.mean_waits_continuous, color="red")
    graph2.set_title("Average Wait Time Per Interval")
    graph2.set_xlabel('Time (Hours)')
    graph2.set_ylabel('Mean Wait Time (Hours)')
    graph3 = fig.add_subplot(8,1,6)
    graph3.plot(outputs.xaxis, outputs.mean_waits, color="purple")
    graph3.set_title("Average Service Time Over Time")
    graph3.set_xlabel('Time (Hours)')
    graph3.set_ylabel('Mean Service Time (Hours)')
    graph4 = fig.add_subplot(8,1,8)
    graph4.plot(outputs.xaxis, outputs.prob_no_wait, color="green")
    graph4.set_title("Probability of No Waiting Time")
    graph4.set_xlabel('Time (Hours)')
    graph4.set_ylabel('Probability')
    if save_file_location != '':
        try:
            fig.savefig(save_file_location)
        except IOError:
            print "\nInvalid Save File Location\n"
##    else:
##        plt.show()
    plt.show()
        

def get_stats(parameters, outputs, array_size):
    summation = 0.0
    fires = 0.0
    '''Return Stats for Graphing'''
    for x in xrange(array_size):
        outputs.xaxis[x] = x * parameters.time_interval / 60.0
        summation += outputs.mean_waits[x]
        fires += parameters.num_fires[x]
        outputs.mean_waits[x] /= parameters.num_fires[x]
        outputs.mean_waits_continuous[x] = summation / fires


def main_func(inputs):
    '''Handles running simulation and printing results'''
    time1 = time.clock()
    #time_interval = get_time_interval()
    print "\nSimulating..."
    env = simpy.Environment()
    parameters = Parameters(inputs)
    outputs = Outputs(int(math.ceil(parameters.length_run /
                                    parameters.time_interval)))
    airtankers = simpy.Resource(env, capacity = parameters.number_airtankers)
    simulation_day(env, airtankers, parameters, outputs)
    print (sum(parameters.num_fires), len(parameters.num_fires),
           len(parameters.wait_times))
    temp_time1 = time.clock()
    print "Finished Simulation in:", temp_time1 - time1, "Seconds"
    print "Calculating Simulation Statistics..."
    get_stats(parameters, outputs, len(parameters.num_fires))
    temp_time2 = time.clock()
    print "Got Stats in:", temp_time2 - temp_time1, "Seconds"
    print "Graphing..."
##    graph_results(outputs, inputs[0], inputs[1],
##                     "%1.4f" %outputs.mean_service[-1], inputs[4])
    print ('[', outputs.mean_waits_continuous[-1], ']', '[',
           outputs.mean_waits_continuous[int(len(outputs.mean_waits) / 2)], ']')
    graphing = multiprocessing.Process(target = graph_results, args =
                    (outputs, inputs[0], inputs[1],
                     "%1.4f" %outputs.mean_service[-1], inputs[4]))
    graphing.start()
    graphing.join()
##    graph_results(outputs, inputs[0], inputs[1], outputs.mean_service[-1],
##                  inputs[4])
    print "Finished Graphing"
    print "Total Time:", 1 + temp_time2 - time1, "\n"
    

if __name__ == '__main__':
    inputs = [5, 8, 300000, 100, 'check_the_graph.png', 5, 5, 5, 5, 5, 5]
    main_func(inputs)
