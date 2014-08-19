out_file = open("100mill_primes.txt", 'w')
primes_list = [2]
out_file.write('2\n')

for x in xrange(3, 1000001):
    flag = True
    for y in xrange(len(primes_list)):
        if x % primes_list[y] == 0:
            flag = False
            break
    if flag:
        primes_list.append(x)
        out_file.write(str(x) + '\n')

out_file.close()
