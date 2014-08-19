out_file = open("1bill_primes.txt", 'w')
out_file.write('2\n')
primes_list = [x for x in range(3, 100000001, 2)]
for x in xrange(len(primes_list)):
    if primes_list[x] != None:
        num = 2 * primes_list[x]
        while num < 100000001:
            primes_list[(num - 3) / 2] = None
            num += primes_list[x]

for x in xrange(len(primes_list)):
    if primes_list[x] != None:
        out_file.write(str(primes_list[x]) + '\n')
