import math
import random
EARTHS_RADIUS = 6371 #KM

def distance_euc2(x1, y1, x2, y2):
    '''Find the Euclidean distance between 2 points'''
    return math.sqrt((x1-x2) ** 2 + (y1 - y2) ** 2)

def distance_euc(long1, lat1, long2, lat2):
    to_rad = math.pi / 180.0
    long1 = long1 * to_rad
    lat1 = lat1 * to_rad
    long2 = long2 * to_rad
    lat2 = lat2 * to_rad
    x1 = EARTHS_RADIUS * math.cos(long1) * math.cos(lat1)
    y1 = EARTHS_RADIUS * math.cos(long1) * math.sin(lat1)
    z1 = EARTHS_RADIUS * math.sin(long1)
    x2 = EARTHS_RADIUS * math.cos(long2) * math.cos(lat2)
    y2 = EARTHS_RADIUS * math.cos(long2) * math.sin(lat2)
    z2 = EARTHS_RADIUS * math.sin(long2)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)

def distance(x1, y1, x2, y2):
    '''Find the Euclidean distance between 2 points'''
    to_rad = math.pi / 180.0
    lat_diff = (y1 * to_rad) - (y2 * to_rad)
    long_diff = (x1 * to_rad) - (x2 * to_rad)
    lat_diff_2 = lat_diff / 2.0
    long_diff_2 = long_diff / 2.0
    const = 2.0 * EARTHS_RADIUS
    distance = const * math.asin(math.sqrt(math.sin(lat_diff_2) ** 2 + \
                                           (math.cos(y1 * to_rad) *
                                            math.cos(y2 * to_rad) *
                                                    (math.sin(long_diff_2) ** 2\
                                                     ))))
    return distance


count = 0
in_file = open("canadian_forest_data.txt", 'r')
lines = 0
for x in range(1000):
    point1 = [random.uniform(47.5, 55.5), random.uniform(-96, -84.5)]
    point2 = [random.uniform(47.5, 55.5), random.uniform(-96, -84.5)]
    temp = in_file.readline()
    temp = in_file.readline()
    temp2 = temp.split(',')
    flag = False
    while temp != '':
        temp2[1] = float(temp2[1])
        temp2[2] = float(temp2[2])
        euc_dist1 = distance_euc(point1[1], point1[0], temp2[2], temp2[1])
        non_euc_dist1 = distance(point1[1], point1[0], temp2[2], temp2[1])
        euc_dist2 = distance_euc(point2[1], point2[0], temp2[2], temp2[1])
        non_euc_dist2 = distance(point2[1], point2[0], temp2[2], temp2[1])
        if euc_dist1 < euc_dist2 and not non_euc_dist1 < non_euc_dist2:
##            print euc_dist1, euc_dist2, non_euc_dist1, non_euc_dist2, line
##            print point1, point2
            flag = True
            count += 1
##        break
        elif euc_dist1 > euc_dist2 and not non_euc_dist1 > non_euc_dist2:
##        print euc_dist1, euc_dist2, non_euc_dist1, non_euc_dist2, line
##        print point1, point2
            flag = True
##        break
            count += 1
        temp = in_file.readline()
        temp2 = temp.split(',')
        lines += 1
    in_file.seek(0)

in_file.close()
if not flag:
    "Theory Passed"
else:
    print "Percent same:", ((lines - count) / float(lines)) * 100
    
