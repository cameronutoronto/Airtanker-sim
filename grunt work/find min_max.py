FILE = "canadian_forest_data.txt"
in_file = open(FILE, 'r')
MEAN_lat = 51.2589723393
MEAN_long = -90.1901522965
mean_lat = 0.0
mean_long = 0.0
lines = 1
mean_lat_diff = 0.0
mean_long_diff = 0.0
temp = in_file.readline()
temp = in_file.readline()
temp2 = temp.split(',')
try:
    min_lat = temp2[1]
    max_lat = temp2[1]
    min_long = temp2[2]
    max_long = temp2[2]
except IndexError:
    raise SystemExit
temp = in_file.readline()
temp2 = temp.split(',')
while temp != '':
    if temp2[1] == '0' or temp2[2] == '0':
        temp = in_file.readline()
        temp2 = temp.split(',')
        continue
    try:
        mean_lat += float(temp2[1])
        mean_long += float(temp2[2])
        mean_lat_diff += abs(float(temp2[1]) - MEAN_lat)
        mean_long_diff += abs(float(temp2[2]) - MEAN_long)
        lines += 1
        if float(temp2[1]) < float(min_lat) and temp2[1] != '0':
            min_lat = temp2[1]
        if float(temp2[1]) > float(max_lat) and temp2[2] != '0':
            max_lat = temp2[1]
        if float(temp2[2]) < float(min_long) and temp2[2] != '0':
            min_long = temp2[2]
        if float(temp2[2]) > float(max_long) and temp2[2] != '0':
            max_long = temp2[2]
    except IndexError:
        raise SystemExit
    temp = in_file.readline()
    temp2 = temp.split(',')
in_file.close()
mean_lat = mean_lat / lines
mean_long = mean_long / lines
mean_lat_diff = mean_lat_diff / lines
mean_long_diff = mean_long_diff / lines
print "Mean Latitude:", mean_lat
print "Mean Longitude:", mean_long
print "Mean Latitude Difference:", mean_lat_diff
print "Mean Longitude DIfference:", mean_long_diff
print "Min Latitude:", min_lat
print "Max Latitude:", max_lat
print "Min Longitude:", min_long
print "Max Longitude", max_long
