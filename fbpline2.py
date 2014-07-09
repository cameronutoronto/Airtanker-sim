import fbp #import python wrappers of C FBP program
import math #import math library
def FBP_Calculate(var):
    '''
    Input (var) is a list of the form:
    Fueltype, month(int), day(int), jd_min month(int), jd_min day(int),latitude,
    longitude, elevation, ffmc, ws, waz (wind direction, int)Percent slope,
    saz (slope azimult, direction uphill), pc (percent conifer), pdf(percent -
    dead fir), gfl (grass fuel load),cur (percent cure), time (int), name
    '''
    if len(var) != 20: #check size of list is correct number of elements
        return "Invalid inputs\n\n"
    data = fbp.inputs() #start creating c structures to hold input/output data
    coef = fbp.create_fuel_array(18)
    try:
        fbp.setup_const(coef)
    except Exception:
        return "Error Calculating...Please Check Inputs...\n"
    mainout = fbp.main_outs()
    head = fbp.fire_struc()
    flank = fbp.fire_struc()
    backs = fbp.fire_struc()
    sec = fbp.snd_outs()
    month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    #Now assign numerical input data to structure to pass to calculate function
    for x in range(len(var)): #change all unentered data to a value of -9
        if var[x] == '' or var[x] == '-9' or var[x] == None:
            var[x] = -9
    if var[1] == -9:
        var[1] = 0
    if var[3] == -9:
        var[3] = 0
    try:
        data.fueltype = var[0] 
    except TypeError:
        return "Invalid Fueltype Selected.\n\n"
    try:
        if len (data.fueltype) == 2 and data.fueltype not in ("O1", 'M1'):
            data.fueltype += ' '
        else:
            if var[1] == 0 or var[2] == -9:
                print "Date is Required."
                raise SystemExit
            if data.fueltype == 'M1':
                if int(var[1]) >= 6:
                    data.fueltype = 'M2 '
                else:
                    data.fueltype = 'M1 '
            if data.fueltype == 'O1':
                if int(var[1]) >= 6:
                    data.fueltype = 'O1b'
                else:
                    data.fueltype = 'O1a'
    except TypeError:
        return "Invalid Fueltype Selected.\n\n"
    try:
        data.ffmc = float(var[8])
    except ValueError:
        return "Invalid ffmc Selected.\n\n"
    try:
        data.ws = float(var[9])
    except ValueError:
        return "Invalid Wind Speed Selected.\n\n"
    try:
        data.bui = float(var[11])
    except ValueError:
        return "Invalid BUI Selected.\n\n"
    try:
        data.lat = float(var[5])  #latitude
    except ValueError:
        return "Invalid latitude Selected.\n\n"
    try:
        data.lon = float(var[6])  #longitude ...should be positive in the west hemisphere
    except ValueError:
        return "Invalid longitude Selected.\n\n"
    try:
        data.waz = int(float(var[10])) #wind direction
        #now ADD 180 DEGREES TO INPUT WIND DIRECTION..to get wind direction is going to
        data.waz += 180
        if data.waz >= 360:
            data.waz -= 360
    except ValueError:
        return "Invalid Wind Direction Selected.\n\n"
    try:
        data.ps = int(float(var[12])) #percent slope
    except ValueError:
        return "Invalid Slope Selected.\n\n"
    try:
        data.saz = int(float(var[13])) #slope azimult...directiuon up hill
    except ValueError:
        return "Invalid Slope Azimult Selected.\n\n"
    try:
        data.pc = int(float(var[14])) #percentage conifer of mixedwood stands  m1/ m2
    except ValueError:
        return "Invalid Percent Conifer Selected.\n\n"
    try:
        data.pdf = int(float(var[15])) #percent dead fir in m3/ m4
    except ValueError:
        return "Invalid Percent Dead Fir Selected.\n\n"
    try:
        data.gfl = float(var[16])       #grass fuel load
    except ValueError:
        return "Invalid Grass Fuel Load Selected.\n\n"
    try:
        data.cur = int(float(var[17])) #percent cure of grass o1
    except ValueError:
        return "Invalid Percent Cured Selected.\n\n"
    try:
        data.elev = int(float(var[7])) #elevation...only used in the foliar moisture scheme
    except ValueError:
        return "Invalid Elevation Selected.\n\n"
    try:
        data.time = int(float(var[18])) #length of time you want spread calc for...this is
    except ValueError:
        return "Invalid Time Selected.\n\n"
                             # only important if calculating distance of spread
    if data.time == -9:
        data.time = 0
    try:
        data.mon = int(float(var[1]))
    except ValueError:
        return "Invalid Month Selected.\n\n"
    m = data.mon
    try:
        d = int(float(var[2]))
    except ValueError:
        return "Invalid Day Selected.\n\n"
    if m != 0:
        try:
            if d == -9:
                d = 0
            data.jd = month[m - 1] + d
        except IndexError:
            return "Invalid Month Selected.\n\n"
    else:
        data.jd = 0
    try:
        m = int(float(var[3])) #This is minimum foliar moisture date
    except ValueError:
        return "Invalid Min Month Selected.\n\n"
    try:
        if d == -9:
            d = 0
        d = int(float(var[4])) #only use if EXPLICITLY specified which is RARE
    except ValueError:
        return "Invalid Min FMC Day Selected.\n\n"
    if m > 0:
        try:
            data.jd_min = month[m - 1] + d
        except IndexError:
            return "Invalid Min FMC Month Selected.\n\n"
    else:
        data.jd_min = 0

    data.pattern = var[19] #point source ignition...so acceleration is included


    #HERE is the call to the FBP calculation routine
    try:
        fbp.calculate(data, coef, mainout, sec, head, flank, backs)
    except Exception:
        return "Error Calculating...Please Check Inputs...\n"
    #now just simple output
    accn = fbp.acceleration(data, head.cfb)
    lbt = (sec.lb - 1.0) * (1.0 - math.exp( -1.0 * accn * data.time)) + 1.0
    return data.fueltype, data.ffmc, data.bui, data.ws, int(float(var[10])), \
           data.waz, data.ps, data.saz, data.lat, data.lon, data.elev, data.jd,\
           data.jd_min, data.time, data.pc, data.pdf, data.gfl, data.cur, \
           mainout.wsv, mainout.raz, mainout.be, mainout.sf, mainout.isi, \
           mainout.fmc, mainout.jd_min, mainout.rss, mainout.sfc, mainout.sfi, \
           head.cfc, mainout.rso, mainout.csi, head.fc, sec.lb, lbt, sec.area, \
           sec.perm/ 1000.0, sec.pgr, head.cfb, head.fd, head.ros, head.fi, \
           head.rost,  (head.dist), flank.cfb, flank.fd, flank.ros, flank.fi,\
           flank.rost,  flank.dist, backs.cfb, backs.fd, backs.ros, backs.fi, \
           backs.rost,  backs.dist


if __name__ == '__main__':
    input1 = ['O1', 7, 11, '', '', 3.9262492553876704, 54.58351564161577, 0.0,
             0.0, 0, '', '', 0, 0, 0.0, 0.0, 0, 0, 626.7717106225749, 1]
    bob = FBP_Calculate(input1)
    print '\n', bob
