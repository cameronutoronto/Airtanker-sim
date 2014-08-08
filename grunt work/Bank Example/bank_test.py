import simpy #For all of the simulation work
import random #For generating random customer generation and service times

LENGTH_SIM = 30.0 #how long will the simulations run for?

class Customer(object): #Class to hold info about each customer in the sim
    def __init__(self, arrive_time, num):
        self.arrive_time = arrive_time #Time they arrived at bank
        self.start_service_time = -1.0 #Time they get to counter
        self.finish_service_time = -1.0 #Time they finish their service
        self.served_by = -1.0 #The counter they were served by
        self.num = num #Which customer in the sim they are (an ID)
    def print_attributes(self): #print all of the statistics for the customer
        format_string = "#%3d  Arrive: %6.1f  Start Service: %6.1f  "\
        + " End Service: %6.1f" + "   Served By: %3d"
        print format_string %(self.num, self.arrive_time,
                              self.start_service_time,
                                self.finish_service_time, self.served_by)

class Counter(object): #class for each counter in the bank
    def __init__(self, number):
        self.number = number #Counter ID
        self.name = "Counter " + str(number) #Name made from ID
        self.start_times = [] #List of all start service times
        self.end_times = [] #List of all service end times

class Bank(object): #Class for the bank
    def __init__(self, env, num_counters):
        self.counters = [Counter(x+1) for x in range(num_counters)]#list counter
        self.num_counters = num_counters #redundant 
        self.counters_resources = [simpy.Resource(env, capacity=1)
                                   for x in range(num_counters)] #simpy resource


def generate_customers(env, customers):
    count = 1 #Keep track of customer number
    while 1: #Infinite loop generate customers until simulation ends
##        wait_time = random.randint(8, 12)
        wait_time = 1
        yield env.timeout(wait_time) #Causes simulation to yield wait_time time
        customers.append(Customer(env.now, count)) #After wait_time new customer
        print "Generated Customer: ", count
        count += 1

def select_counter(env, bank):
    '''choose a counter for the customer'''
    for x in range(len(bank.counters)):
##        if bank.counters_resources[len(bank.counters) - 1 - x].count == 0 and\
##        bank.counters_resources[len(bank.counters) - 1 - x].queue == []:
        if bank.counters_resources[len(bank.counters) - 1 - x].count == 0:
            print "COUNT:", \
                  bank.counters_resources[len(bank.counters) - 1 - x].count
            print "QUEUE:", \
                  bank.counters_resources[len(bank.counters) - 1 - x].queue
            print "Counter Selected: ", len(bank.counters) - 1 - x
            return len(bank.counters) - 1 - x
    return -2.0

def gen_service_time():
    '''Return a service time for a customer'''
##    return random.random() * 20.0 + 19.0
##    return random.randint(4, 8)
    return 7


def handle_customer(env, bank, customer, customers, num_process):
    '''handles customer'''
    print "Process ", num_process, " started at:", env.now
    counter = select_counter(env, bank) #pick most suitable counter
    if counter != -2.0: #Found an available counter
        #Go to counter and keep the resource the whole time
        with bank.counters_resources[counter].request() as req:
            yield req
            #Add start time to the counters list
            bank.counters[counter].start_times.append(env.now)
            #Generate a service time
            service_time = gen_service_time()
            #Start service time is the current simulation time
            customer.start_service_time = env.now
            #End service time is the service time + current time
            customer.finish_service_time = env.now + service_time
            #Add this end service time to the counters list
            bank.counters[counter].end_times.append(env.now + service_time)
            #Record which counter served the customer
            customer.served_by = counter + 1
            #The simulation waits this time, then release the counter resource
            yield env.timeout(service_time)
    else: #Join line and wait for first available counter
        reqs = []
        got_counter = 0
        #Cause list reqs to hold a request for every counter in the bank
        for x in range(len(bank.counters)):
            reqs.append(bank.counters_resources[x].request())
        #Make the customer wait for any of the counters to become available
        good_req = yield simpy.events.AnyOf(env, reqs)
        #Assign req to the request for a now available counter
        req = good_req.keys()[0]
        #Cancel all of the other requests and find out which counter is now open
        for x in range(len(bank.counters)):
            if req != reqs[x]: #cancel other requests
                bank.counters_resources[x].release(reqs[x])
                reqs[x].cancel(None, None, None)
            else: #Get counter number that is available
                got_counter = x
        #Now that a counter is available, do the same as the above
        bank.counters[got_counter].start_times.append(env.now)
        service_time = gen_service_time()
        customer.start_service_time = env.now
        customer.finish_service_time = env.now + service_time
        bank.counters[got_counter].end_times.append(env.now + service_time)
        customer.served_by = got_counter + 1
        yield env.timeout(service_time)
        print "Process ", num_process, " finished at:", env.now
        bank.counters_resources[got_counter].release(req)
            
        
    

def run_bank(env, bank, customers):
    '''Infinite loop running the bank for the whole simulation time.'''
    while 1:
        min_time = -1.0
        min_customer = -1.0
        #Go through list of customers and get the first one
        for x in xrange(len(customers)):
            #Get first customer that has arrived and not yet known about
            if customers[x].arrive_time < min_time or min_time == -1.0:
                if customers[x].arrive_time > env.now:
                    min_time = customers[x].arrive_time
                    min_customer = x
                else:
                    continue
        #All customers have been processed so go to end of simulation
        if min_time == -1.0:
            yield env.timeout(LENGTH_SIM - env.now)
        #Else move simulation to next customers arrive time
        yield env.timeout(min_time - env.now)
        print "Calling Process: ", min_customer+1, "At time:", env.now
        #For every customer call a seperate process to handle that customer
        env.process(handle_customer(env,bank,customers[min_customer],customers,
                                    min_customer + 1))

def run_sim(): #Run the whole simulation
    #First run one simulation to get all of the customer arrival times
    env = simpy.Environment()
    customers = []
    env.process(generate_customers(env, customers))
    env.run(until=LENGTH_SIM)
    #Run second simulation to handle all of these customers
    env2 = simpy.Environment()
    bank = Bank(env2, 3) #Create bank
    env2.process(run_bank(env2, bank, customers))
    env2.run(until = LENGTH_SIM)
    #Print Simulation results
    for x in range(len(customers)):
        customers[x].print_attributes()

if __name__ == '__main__':
    run_sim()
        
