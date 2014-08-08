import simpy
import random

env = simpy.Environment()

def func1(env):
    yield env.timeout(random.randint(800, 1200) / 100.0)

def func2(env, resources, x):
    with resources[x].request() as req:
        print "in", env.now
        yield req
        print resources[x].count, env.now
        yield env.process(func1(env))

def func3(env, resources):
    reqs = ['' for x in range(len(resources))]
    for x in range(len(resources)):
        print "Resource", x + 1, "requested"
        reqs[x] =  resources[x].request()
    print "Starting yield"
    for x in range(len(resources)):
        yield simpy.Resource.release(resources[x], reqs[x])
        print "Users:", resources[x].users, resources[x].queue
    yielded = yield simpy.events.AnyOf(env, reqs)
    print "Done yield", yielded
    for x in range(len(resources)):
        resources[x].release(reqs[x])
        print "Users:", resources[x].users, resources[x].queue
    yield env.process((func1(env)))
    for x in range(len(resources)):
        simpy.Resource.release(resources[x], reqs[x])
    print "Done final yield"
    print yielded
    for x in range(len(resources)):
        print resources[x].count, "Reqs Count"
        print reqs[x]
    with resources[2].request() as req:
        print env.now, "start"
        yield req
        print env.now
    for key in yielded:
        try:
            print key, "done"
            simpy.Resource.release(env, key)
        except AttributeError:
            print key, "fail"
    

def foo(env, resources):
    print "Start"
    for x in range(len(resources)):
        env.process(func2(env, resources, x))
        yield env.timeout(1)
        print resources[x].count, env.now
    print "starting new req", env.now, resources[0].count
    env.process(func3(env, resources))
    yield env.timeout(1)
    for x in range(len(resources)):
        print resources[x].count, env.now
    yield env.timeout(10)
    for x in range(len(resources)):
        print resources[x].count, env.now

def bar(env, resources):
    while 1:
        env.process(foo(env, resources))
        yield env.timeout(100)

resources = []
for x in range(3):
    resources.append(simpy.Resource(env, capacity=1))

env.process(bar(env, resources))
env.run(until = 100)
            
