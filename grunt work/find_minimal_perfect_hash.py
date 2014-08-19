import random

def hash_func(a, b, c, num, size):
    '''Hash number num based on size output buckets'''
    hashed_value = (num ** (277 * a) * (13177 * b) + (28547 * c))
    hashed_value = hashed_value % size
    return int(hashed_value)

def prime_hash(a, b, c, num, size):
    '''Hash number num based on size output buckets'''
    hashed_value = (num ** (a) * (b) + (c))
    hashed_value = hashed_value % size
    return int(hashed_value)

in_file = open("1bill_primes.txt", 'r')
size  = 2
while 1:
    numbers = [x for x in range(size)]
    count = 0
    while 1:
        in_file.seek(random.randint(0, 1000))
        temp = in_file.readline()
        temp = in_file.readline()
        a = int(temp[:-1])
        in_file.seek(random.randint(0, 10000))
        temp = in_file.readline()
        temp = in_file.readline()
        b = int(temp[:-1])
        in_file.seek(random.randint(0, 26482))
        temp = in_file.readline()
        temp = in_file.readline()
        c = int(temp[:-1])
        flag = True
        hashed_list = map(lambda x: prime_hash(a, b, c, x, size), numbers)
        for x in range(len(hashed_list)):
            if hashed_list[x] in hashed_list[:x] + hashed_list[x+1:]:
                flag = False
                break
        count += 1
        if flag and hashed_list != numbers:
            print "\nSIZE:%d" %size
            print "Try #%d:" %count
            print 'a:', a
            print 'b:', b
            print 'c:', c
            print hashed_list
            break
        if count > 10000:
            break
    size += 1
in_file.close()
