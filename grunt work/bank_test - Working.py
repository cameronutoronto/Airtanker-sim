import simpy
import random

LENGTH_SIM = 200.0

class Customer(object):
    def __init__(self, arrive_time, num):
        self.arrive_time = arrive_time
        self.start_service_time = -1.0
        self.finish_service_time = -1.0
        self.served_by = -1.0
        self.num = num
    def print_attributes(self):
        format_string = "#%3d  Arrive: %6.1f  Start Service: %6.1f  "\
        + " End Service: %6.1f" + "   Served By: %3d"
        print format_string %(self.num, self.arrive_time,
                              self.start_service_time,
                                self.finish_service_time, self.served_by)

class Counter(object):
    def __init__(self, number):
        self.number = number
        self.name = "Counter " + str(number)
        self.start_times = []
        self.end_times = []

class Bank(object):
    def __init__(self, env, num_counters):
        self.counters = [Counter(x+1) for x in range(num_counters)]
        self.num_counters = num_counters
        self.counters_resources = [simpy.Resource(env, capacity=1)
                                   for x in range(num_counters)]


def generate_customers(env, customers):
    count = 1
    while 1:
        wait_time = random.randint(8, 12)
        yield env.timeout(wait_time)
        customers.append(Customer(env.now, count))
        print "Generated Customer: ", count
        count += 1

def select_counter(env, bank):
    '''choose a counter for the customer'''
    for x in range(len(bank.counters)):
        if bank.counters_resources[len(bank.counters) - 1 - x].count == 0:
            print "Counter Selected: ", len(bank.counters) - 1 - x
            print bank.counters[len(bank.counters) - 1 - x].number
            print bank.counters_resources[len(bank.counters) - 1 - x].users
            return len(bank.counters) - 1 - x
    return -2.0

def gen_service_time():
    return random.random() * 20.0 + 21.0

def handle_customer(env, bank, customer, customers, num_process):
    '''handles customer'''
    print "Process ", num_process, " started at:", env.now
    counter = select_counter(env, bank)
    print "Process ", num_process, " after counter select:", env.now
    if counter != -2.0:
        with bank.counters_resources[counter].request() as req:
            yield req
            print "Process ", num_process, "Time", env.now, "In if"
            bank.counters[counter].start_times.append(env.now)
            service_time = gen_service_time()
            customer.start_service_time = env.now
            customer.finish_service_time = env.now + service_time
            bank.counters[counter].end_times.append(env.now + service_time)
            customer.served_by = counter + 1
            yield env.timeout(service_time)
    else:
        with bank.counters_resources[0].request() as req:
            yield req
            print "Process ", num_process, "Time", env.now, "In else"
            bank.counters[0].start_times.append(env.now)
            service_time = gen_service_time()
            customer.start_service_time = env.now
            customer.finish_service_time = env.now + service_time
            bank.counters[0].end_times.append(env.now + service_time)
            customer.served_by = 1
            yield env.timeout(service_time)
            
        
    

def run_bank(env, bank, customers):
    while 1:
        min_time = -1.0
        min_customer = -1.0
        for x in xrange(len(customers)):
            if customers[x].arrive_time < min_time or min_time == -1.0:
                if customers[x].arrive_time > env.now:
                    min_time = customers[x].arrive_time
                    min_customer = x
                else:
                    continue
        if min_time == -1.0:
            yield env.timeout(LENGTH_SIM - env.now)
        yield env.timeout(min_time - env.now)
        print "Calling Process: ", min_customer, "At time:", env.now
        env.process(handle_customer(env,bank,customers[min_customer],customers,
                                    min_customer + 1))

def run_sim():
    env = simpy.Environment()
    customers = []
    env.process(generate_customers(env, customers))
    env.run(until=LENGTH_SIM)
    env2 = simpy.Environment()
    bank = Bank(env2, 3)
    env2.process(run_bank(env2, bank, customers))
    env2.run(until = LENGTH_SIM)
    for x in range(len(customers)):
        customers[x].print_attributes()

if __name__ == '__main__':
    run_sim()
        
