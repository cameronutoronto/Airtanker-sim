import wx #Python module for generating a GUI
import os #needed to join paths in open/save
import threading #Prevent Crashing
import time #Loading bar functionality
import sys #Redirect stdout
import copy
import fire_sim_model #Simulation

class Redirect_Stdout(): #Redirect Stdout to textctrl
    def __init__(self, stdout_pt, new_out):
        self.stdout_pt = stdout_pt
        self.new_out = new_out
        self.log_pt = new_out
        
    def write(self, string):
        self.new_out.WriteText(string)
        
    def reset(self): #DOESNT WORK
        self.new_out = self.stdout_pt

    def setup(self):
        self.new_out = self.log_pt

        
class mainwindow(wx.Frame):
    def __init__(self, parent, title):
        self.input = ['' for x in range(32)] #Save user entered values
        self.input_fixed = [None for x in range(32)]
        self.dirname = ''
        self.filename = ''
        #Creating the window, setting it blue, and adding a text box to it
        wx.Frame.__init__(self, parent, title = title, size =(1200, 900))
        self.SetBackgroundColour((120, 180, 255)) #light blue
        self.logger = wx.TextCtrl(self, size=(600, 350),style=wx.TE_MULTILINE|\
                                  wx.TE_RICH)
        stdout_pt = sys.stdout
        sys.stdout = Redirect_Stdout(stdout_pt, self.logger)
        self.CreateStatusBar()
        self.gauge = wx.Gauge(self) #loading bar
        self.stop_load_bar_flag = False
        self.Bind(wx.EVT_CLOSE, self.OnExit) #bind x button
        self.input[2] = 'False'
        self.input[3] = 'False'
        self.input_fixed[2] = False
        self.input_fixed[3] = False

################################################################################
#                                   MENU
################################################################################

        #Setting up the "File" menu option
        filemenu = wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open", \
                                   "Open a Text File of Input Options")
        menuSaveOut = filemenu.Append(wx.ID_SAVE, \
                                   "&Save Output",
                                   "Select a Text File to save Output")
        menuSaveIn = filemenu.Append(wx.ID_SAVE, \
                                   "&Save Input",
                                   "Select a Text File to save Input")
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", \
                                    "Information About the Program")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT,"&Exit","Terminate the Program")
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnSaveOut, menuSaveOut)
        self.Bind(wx.EVT_MENU, self.OnSaveIn, menuSaveIn)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)



        #Setting up the "Help" menu option
        helpmenu = wx.Menu()
        self.menuHelp = helpmenu.Append(wx.ID_HELP, "&Help", \
                                   "Help on Using the Program")
        self.Bind(wx.EVT_MENU, self.OnHelp, self.menuHelp)


        #Creating File MenuBar
        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        menubar.Append(helpmenu, "&Help")
        self.SetMenuBar(menubar)

        #Create Sizers 
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.GridBagSizer(hgap=7, vgap=3)
        hSizer = wx.BoxSizer(wx.HORIZONTAL)

################################################################################
#                                   INPUTS
################################################################################

        #Simulation
        self.simulation_title =wx.StaticText(self, label ="SIMULATION")
        grid.Add(self.simulation_title, pos=(0, 2))
        self.make_bold(self.simulation_title)


        #Number of Runs
        self.num_runs_prompt = wx.StaticText(self, label = "Number of Runs: ")
        self.num_runs = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.num_runs_prompt, pos = (1, 0))
        grid.Add(self.num_runs, pos = (1, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 0), self.num_runs)
        self.make_bold(self.num_runs_prompt)

        #Length of Run
        self.length_run_prompt = wx.StaticText(self, label = "Length of Run: ")
        self.length_run = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.length_run_prompt, pos = (1, 2))
        grid.Add(self.length_run, pos = (1, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 1), self.length_run)
        self.make_bold(self.length_run_prompt)

        #Show fire attributes
        self.show_fire_attributes_prompt = wx.StaticText\
                                           (self,label="Show Fire Attributes: ")
        #self.show_fire_attributes = wx.TextCtrl(self,value="", size = (100, -1)
        self.show_fire_attributes = wx.CheckBox(self, style=wx.CHK_2STATE,
                                                name = "Show Fire Attributes")
        grid.Add(self.show_fire_attributes_prompt, pos = (2, 0))
        grid.Add(self.show_fire_attributes, pos = (2, 1))
        #self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 2),
                  #self.show_fire_attributes)
        self.Bind(wx.EVT_CHECKBOX, self.show_fires, self.show_fire_attributes)
        self.make_bold(self.show_fire_attributes_prompt)

        #Save Daily Averages
        self.save_daily_avgs_prompt = wx.StaticText\
                                      (self, label = "Save Daily Averages: ")
        #self.save_daily_avgs = wx.TextCtrl(self, value="", size = (100, -1))
        self.save_daily_avgs = wx.CheckBox(self, style = wx.CHK_2STATE,
                                           name = "Save Daily Averages")
        grid.Add(self.save_daily_avgs_prompt, pos = (2, 2))
        grid.Add(self.save_daily_avgs, pos = (2, 3))
        #self.Bind(wx.EVT_TEXT,lambda x: self.EvtText(x,3),self.save_daily_avgs)
        self.Bind(wx.EVT_CHECKBOX, self.save_daily, self.save_daily_avgs)
        self.make_bold(self.save_daily_avgs_prompt)

        #Weather
        self.weather_title =wx.StaticText(self, label ="WEATHER")
        grid.Add(self.weather_title, pos=(3, 2))
        self.make_bold(self.weather_title)

        #FFMC
        self.ffmc_prompt = wx.StaticText(self, label = "FFMC: ")
        self.ffmc = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.ffmc_prompt, pos = (4, 0))
        grid.Add(self.ffmc, pos = (4, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 4), self.ffmc)
        self.make_bold(self.ffmc_prompt)

        #ISI
        self.isi_prompt = wx.StaticText(self, label = "ISI: ")
        self.isi = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.isi_prompt, pos = (5, 0))
        grid.Add(self.isi, pos = (5, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 5), self.isi)
        self.make_bold(self.isi_prompt)

        #Forest
        self.forest_title =wx.StaticText(self, label ="FOREST")
        grid.Add(self.forest_title, pos=(6, 2))
        self.make_bold(self.forest_title)

        #Minimum Latitude
        self.min_lat_prompt = wx.StaticText(self, label = "Minimum Latitude: ")
        self.min_lat = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.min_lat_prompt, pos = (7, 0))
        grid.Add(self.min_lat, pos = (7, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 6), self.min_lat)
        self.make_bold(self.min_lat_prompt)

        #Maximum Latitude
        self.max_lat_prompt = wx.StaticText(self, label = "Maximum Latitude: ")
        self.max_lat = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_lat_prompt, pos = (7, 2))
        grid.Add(self.max_lat, pos = (7, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 7), self.max_lat)
        self.make_bold(self.max_lat_prompt)

        #Minimum Longitude
        self.min_long_prompt = wx.StaticText(self,label = "Minimum Longitude: ")
        self.min_long = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.min_long_prompt, pos = (8, 0))
        grid.Add(self.min_long, pos = (8, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 8), self.min_long)
        self.make_bold(self.min_long_prompt)

        #Maximum Longitude
        self.max_long_prompt = wx.StaticText(self, label ="Maximum Longitude: ")
        self.max_long = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_long_prompt, pos = (8, 2))
        grid.Add(self.max_long, pos = (8, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 9), self.max_long)
        self.make_bold(self.max_long_prompt)

        #Number of Rows
        self.num_rows_prompt = wx.StaticText(self, label = "Number of Rows: ")
        self.num_rows = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.num_rows_prompt, pos = (9, 0))
        grid.Add(self.num_rows, pos = (9, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 10), self.num_rows)
        self.make_bold(self.num_rows_prompt)

        #Number of Columns
        self.num_columns_prompt = wx.StaticText(self, label = \
                                                "Number of Columns: ")
        self.num_columns = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.num_columns_prompt, pos = (9, 2))
        grid.Add(self.num_columns, pos = (9, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 11), self.num_columns)
        self.make_bold(self.num_columns_prompt)

        #Percent Conifer
        self.p_con_prompt = wx.StaticText(self, label = "Percent Conifer: ")
        self.p_con = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.p_con_prompt, pos = (10, 0))
        grid.Add(self.p_con, pos = (10, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 12), self.p_con)
        self.make_bold(self.p_con_prompt)

        #Percent Dead Fir
        self.p_dead_fir_prompt = wx.StaticText(self, label = \
                                               "Percent Dead Fir: ")
        self.p_dead_fir = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.p_dead_fir_prompt, pos = (10, 2))
        grid.Add(self.p_dead_fir, pos = (10, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 13), self.p_dead_fir)
        self.make_bold(self.p_dead_fir_prompt)

        #Bases
        self.bases_title =wx.StaticText(self, label ="BASES")
        grid.Add(self.bases_title, pos=(11, 2))
        self.make_bold(self.bases_title)

        #Number of Bases
        self.num_bases_prompt = wx.StaticText(self, label = "Number of Bases: ")
        self.num_bases = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.num_bases_prompt, pos = (12, 0))
        grid.Add(self.num_bases, pos = (12, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 14), self.num_bases)
        self.make_bold(self.num_bases_prompt)

        #Bases Latitude
        self.bases_lat_prompt = wx.StaticText(self, label = "Bases Latitude: ")
        self.bases_lat = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bases_lat_prompt, pos = (12, 2))
        grid.Add(self.bases_lat, pos = (12, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 15), self.bases_lat)
        self.make_bold(self.bases_lat_prompt)

        #Bases Longtitude
        self.bases_long_prompt = wx.StaticText(self, label ="Bases Longitude: ")
        self.bases_long = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bases_long_prompt, pos = (12, 4))
        grid.Add(self.bases_long, pos = (12, 5))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 16), self.bases_long)
        self.make_bold(self.bases_long_prompt)

        #Base Number of Airtankers
        self.base_num_at_prompt = wx.StaticText\
                                  (self, label = "Base Number of Airtankers: ")
        self.base_num_at = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.base_num_at_prompt, pos = (13, 0))
        grid.Add(self.base_num_at, pos = (13, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 17), self.base_num_at)
        self.make_bold(self.base_num_at_prompt)

        #Base Number of Bird Dogs
        self.base_num_bd_prompt = wx.StaticText\
                                  (self, label = "Base Number of Bird Dogs: ")
        self.base_num_bd = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.base_num_bd_prompt, pos = (13, 2))
        grid.Add(self.base_num_bd, pos = (13, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 18), self.base_num_bd)
        self.make_bold(self.base_num_bd_prompt)

        #Speeds
        self.speeds_title =wx.StaticText(self, label ="AIRCRAFT SPEEDS(km/m)")
        grid.Add(self.speeds_title, pos=(14, 2))
        self.make_bold(self.speeds_title)


        #Airtanker Cruising Speeds
        self.airtanker_cruising_prompt = wx.StaticText\
                                         (self, label = "Airtanker Cruising: ")
        self.airtanker_cruising = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.airtanker_cruising_prompt, pos = (15, 0))
        grid.Add(self.airtanker_cruising, pos = (15, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 19), \
                  self.airtanker_cruising)
        self.make_bold(self.airtanker_cruising_prompt)

        #Airtanker Fight Speeds
        self.airtanker_fight_prompt = wx.StaticText\
                                      (self, label = "Airtanker Fight: ")
        self.airtanker_fight = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.airtanker_fight_prompt, pos = (15, 2))
        grid.Add(self.airtanker_fight, pos = (15, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 20), \
                  self.airtanker_fight)
        self.make_bold(self.airtanker_fight_prompt)

        #Airtanker Circling
        self.airtanker_circling_prompt = \
                                       wx.StaticText(self, label = \
                                                     "Airtanker Circling: ")
        self.airtanker_circling = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.airtanker_circling_prompt, pos = (15, 4))
        grid.Add(self.airtanker_circling, pos = (15, 5))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 21), \
                  self.airtanker_circling)
        self.make_bold(self.airtanker_circling_prompt)

        #Bird Dog Cruising Speeds
        self.bird_dog_cruising_prompt = wx.StaticText\
                                         (self, label = "Bird Dog Cruising: ")
        self.bird_dog_cruising = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bird_dog_cruising_prompt, pos = (16, 0))
        grid.Add(self.bird_dog_cruising, pos = (16, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 22), \
                  self.bird_dog_cruising)
        self.make_bold(self.bird_dog_cruising_prompt)

        #Bird Dog Fight Speeds
        self.bird_dog_fight_prompt = wx.StaticText\
                                      (self, label = "Bird Dog Fight: ")
        self.bird_dog_fight = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bird_dog_fight_prompt, pos = (16, 2))
        grid.Add(self.bird_dog_fight, pos = (16, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 23), \
                  self.bird_dog_fight)
        self.make_bold(self.bird_dog_fight_prompt)

        #Bird Dog Circling
        self.bird_dog_circling_prompt = \
                                       wx.StaticText(self, label = \
                                                     "Bird Dog Circling: ")
        self.bird_dog_circling = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bird_dog_circling_prompt, pos = (16, 4))
        grid.Add(self.bird_dog_circling, pos = (16, 5))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 24), \
                  self.bird_dog_circling)
        self.make_bold(self.bird_dog_circling_prompt)

        #Airtanker Max Time
        self.max_time_at_prompt = wx.StaticText\
                                      (self, label = "Airtanker Max Time: ")
        self.max_time_at = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_time_at_prompt, pos = (17, 0))
        grid.Add(self.max_time_at, pos = (17, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 25), \
                  self.max_time_at)
        self.make_bold(self.max_time_at_prompt)

        #Airtanker Max Distance
        self.max_distance_at_prompt = wx.StaticText\
                                      (self, label = "Airtanker Max Distance: ")
        self.max_distance_at = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_distance_at_prompt, pos = (17, 2))
        grid.Add(self.max_distance_at, pos = (17, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 26), \
                  self.max_distance_at)
        self.make_bold(self.max_distance_at_prompt)

        #Bird Dog Max Time
        self.max_time_bd_prompt = wx.StaticText\
                                  (self, label = "Bird Dog Max Time: ")
        self.max_time_bd = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_time_bd_prompt, pos = (18, 0))
        grid.Add(self.max_time_bd, pos = (18, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 27), self.max_time_bd)
        self.make_bold(self.max_time_bd_prompt)

        #Bird Dog Max Distance
        self.max_distance_bd_prompt = wx.StaticText\
                                      (self, label = "Bird Dog Max Distance: ")
        self.max_distance_bd = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.max_distance_bd_prompt, pos = (18, 2))
        grid.Add(self.max_distance_bd, pos = (18, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 28), \
                  self.max_distance_bd)
        self.make_bold(self.max_distance_bd_prompt)

        #Points
        self.points_title =wx.StaticText(self, label ="TRACKED POINTS")
        grid.Add(self.points_title, pos=(19, 2))
        self.make_bold(self.points_title)

        #Number of Points
        self.num_points_prompt = wx.StaticText\
                                 (self, label = "Number of Points: ")
        self.num_points = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.num_points_prompt, pos = (20, 0))
        grid.Add(self.num_points, pos = (20, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 29), self.num_points)
        self.make_bold(self.num_points_prompt)

        #Points Latitudes
        self.points_lat_prompt = wx.StaticText\
                                 (self, label = "Points Latitudes: ")
        self.points_lat = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.points_lat_prompt, pos = (20, 2))
        grid.Add(self.points_lat, pos = (20, 3))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 30), self.points_lat)
        self.make_bold(self.points_lat_prompt)

        #Points Longitudes
        self.points_long_prompt = wx.StaticText\
                                  (self, label = "Points Longitudes: ")
        self.points_long = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.points_long_prompt, pos = (20, 4))
        grid.Add(self.points_long, pos = (20, 5))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 31), self.points_long)
        self.make_bold(self.points_long_prompt)

        self.input_select = [self.num_runs, self.length_run,
                             self.show_fire_attributes, self.save_daily_avgs,
                             self.ffmc, self.isi,
                             self.min_lat, self.max_lat, self.min_long,
                             self.max_long, self.num_rows, self.num_columns,
                             self.p_con, self.p_dead_fir, self.num_bases,
                             self.bases_lat, self.bases_long, self.base_num_at,
                             self.base_num_bd, self.airtanker_cruising,
                             self.airtanker_fight, self.airtanker_circling,
                             self.bird_dog_cruising, self.bird_dog_fight,
                             self.bird_dog_circling, self.max_time_at,
                             self.max_distance_at, self.max_time_bd,
                             self.max_distance_bd, self.num_points,
                             self.points_lat, self.points_long]

        try:
            inputs = open("airtanker_saved_input.txt", 'r')
            self.OnStart(inputs, 'read')
        except IOError:
            inputs = open("airtanker_saved_input.txt", 'w')
            self.OnStart(inputs, 'write')

################################################################################
#                                   BUTTONS
################################################################################


        #Run Simulation Button
        self.simulation_button = wx.Button(self, label="Run Simulation")
        self.Bind(wx.EVT_BUTTON, self.OnClick, self.simulation_button)
        self.make_bold(self.simulation_button)

        #Clear Button
        self.clear_button = wx.Button(self, label = "Clear")
        self.Bind(wx.EVT_BUTTON, self.Clear, self.clear_button)
        self.make_bold(self.clear_button)

        #Clear All Button
        self.clear_all_button = wx.Button(self, label = "Clear All")
        self.Bind(wx.EVT_BUTTON, self.ClearAll, self.clear_all_button)
        self.make_bold(self.clear_all_button)

################################################################################
#                                   SETUP
################################################################################

        #Setup sizers and place them
        hSizer.AddSpacer(10)
        hSizer.Add(grid, 0, wx.EXPAND, 10)
        hSizer.AddSpacer(10)
        hSizer.Add(self.logger, 1, wx.EXPAND)
        mainSizer.AddSpacer(10)
        mainSizer.Add(hSizer, 1,wx.EXPAND)
        mainSizer.AddSpacer(10)
        mainSizer.Add(self.simulation_button, 0, wx.EXPAND | wx.CENTER)
        mainSizer.AddSpacer(5)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(self.clear_button, 1, wx.LEFT)
        buttonSizer.AddSpacer(10)
        buttonSizer.Add(self.clear_all_button, 1, wx.LEFT)
        mainSizer.Add(buttonSizer, 0)
        mainSizer.Add(self.gauge, proportion=0, flag=wx.EXPAND)
        self.SetSizerAndFit(mainSizer)
        self.Centre()


################################################################################
#                                   METHODS
################################################################################
    def OnAbout(self, e):
        '''Displays a popup box that gives information about this software'''
        dlg = wx.MessageDialog(self, "Fire Simulation Model " + \
                               "\n\nThis Graphical-" +\
                               "User-Interface for the Fire Simulation Model" +\
                               " Software was created by" +\
                               " Cameron Buttazzoni for research " + \
                               "purposes at the Fires Management " +\
                               "System Laboratory in the Faculty of Forestry"+\
                               " at the University of Toronto\n\n" +\
                               "THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED" +\
                               " FOR OPERATIONAL USE"\
                               + "\nCopyright: Cameron Buttazzoni\n\n", \
                               "About Fire Simulation Model Software", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        
    def OnExit(self, e): 
        '''Exit the software'''
        inputs = open("airtanker_saved_input.txt", 'w')
        self.OnStart(inputs, 'write')
        self.Close(True)
        raise SystemExit
        
    def OnSaveOut(self, e): 
        '''Select a file to print the whole logger to'''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, \
                            "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.logger.SaveFile(os.path.join(self.dirname, self.filename), \
                                 fileType=wx.TEXT_TYPE_ANY)
        dlg.Destroy()

    def OnSaveIn(self, e):
        '''Select a file to save input values to'''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, \
                            "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            open_file = open(os.path.join(self.dirname, self.filename), 'w')
            self.OnStart(open_file, 'write')
        dlg.Destroy()
        

    def OnOpen(self, e): #Open a file of inputs
        '''Open a Point text file of inputs and prints the outputs to logger'''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, \
                            "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            input_file = open(os.path.join(self.dirname, self.filename), 'r')
            self.OnStart(input_file, 'read')
        dlg.Destroy()

    def OnStart(self, in_file, purpose):
        '''Read or right inputs'''
        if purpose == 'read':
            temp_line = in_file.readline()
            temp_line = temp_line.translate(None, ' ')
            temp2 = temp_line.split('|') #Assumed pipe seperated values
            if len(temp2) != len(self.input):
                self.logger.AppendText("\nStored Value error\n\n")
                in_file.close()
                return
            for x in range(len(temp2)):
                self.input[x] = temp2[x]
                try:
                    self.input_select[x].SetValue(self.input[x])
                except (TypeError, AttributeError):
                    if x == 2 or x == 3:
                        if self.input[x] == 'True':
                            self.input_select[x].SetValue(True)
                        else:
                            self.input_select[x].SetValue(False)
            self.input_fixed = self.fix_types(self.input)
            for element in self.input_fixed:
                if element == '':
                    element = None
            in_file.close()
            return
        elif purpose == 'write':
            temp_string = ''
            for x in range(len(self.input)):
                if x < len(self.input) - 1:
                    temp_string += (str(self.input[x]) + '|')
                else:
                    temp_string += str(self.input[x])
            in_file.write(temp_string)
            in_file.close()
            return

################################################################################
#                            CALCULATION METHODS
################################################################################

    def EvtText(self, e, num):
        '''Entering text sets input to new entered value'''
        self.input[num] = e.GetString().encode('ascii', 'ignore')

    def show_fires(self, e):
        if self.input_fixed[2]:
            self.input_fixed[2] = False
            self.input[2] = 'False'
        else:
            self.input_fixed[2] = True
            self.input[2] = 'True'

    def save_daily(self, e):
        if self.input_fixed[3]:
            self.input_fixed[3] = False
            self.input[3] = 'False'
        else:
            self.input_fixed[3] = True
            self.input[3] = 'True'

    def OnClick(self, e):
        self.disable_buttons()
        self.gauge.SetValue(0)
        self.input_fixed = self.fix_types(self.input)
        for element in self.input_fixed:
            if element == '':
                element = None
        load_thread = threading.Thread(target = self.loading_bar)
        load_thread.setDaemon(True)
        load_thread.start()

        sim_thread = threading.Thread(target = self.run_sim)
        sim_thread.setDaemon(True)
        sim_thread.start()

    def run_sim(self):
        fire_sim_model.main_func(self.input_fixed)
        self.stop_load_bar_flag = True
        time.sleep(0.1)
        self.gauge.SetValue(100)
        time.sleep(2)
        self.gauge.SetValue(0)
        self.enable_buttons()

    def Clear(self,e):
        self.logger.Clear()

    def ClearAll(self, e): #clears logger and all entered values
        self.logger.Clear()
        for x in range(len(self.input)):
            self.input[x] = ''
            try:
                self.input_select[x].Clear()
            except AttributeError:
                try:
                    self.input[x].SetValue(0)
                except AttributeError:
                    if x == 2 or x == 3:#Show Fire Attributes Checkbox
                        self.input_fixed[x] = False

    def make_bold(self, text):
        '''Makes prompts and button text bold'''
        temp_font = text.GetFont()
        temp_font.SetWeight(wx.BOLD)
        text.SetFont(temp_font)

################################################################################
#                               OTHER METHODS
################################################################################
    def OnHelp(self, e):
        '''Opens a box displaying this on help'''
        help_text = '''Fire Simulation Model'''
        help_dlg = wx.MessageDialog(self, help_text, "Fire Simulation Model" +\
                                    " Software Help", wx.OK)
        help_dlg.ShowModal()
        help_dlg.Destroy()

    def loading_bar(self):
        '''Thread for loading bar that estimates (poorly) time remaining'''
        self.stop_load_bar_flag = False
        if type(self.input_fixed[0]) == int or type(self.input_fixed[0])==float:
            max_count = self.input_fixed[0] #CHANGE
        else:
            self.logger.AppendText("\nInvalid Number of runs\n\n")
            return
        loaded = 100.0 / (1 + (max_count * 0.008))
        while loaded < 100.0:
            time.sleep(1)
            self.gauge.SetValue(loaded)
            loaded += 100.0 / (20 + (max_count * 0.007))
            if self.stop_load_bar_flag:
                break
        self.gauge.SetValue(100)
        time.sleep(2)
        self.gauge.SetValue(0)
        self.stop_load_bar_flag = False
    
    def disable_buttons(self):
        '''Prevent User from clicking any buttons'''
        self.simulation_button.Enable(False)
        self.clear_button.Enable(False)
        self.clear_all_button.Enable(False)

    def enable_buttons(self):
        '''Reenable buttons to be pressed'''
        self.simulation_button.Enable(True)
        self.clear_button.Enable(True)
        self.clear_all_button.Enable(True)

    def fix_types(self, values):
        input_list = copy.deepcopy(values)
        '''Fix types of elements in a list'''
        for x in range(len(input_list)):
            if input_list[x] == 'False':
                input_list[x] = False
            elif input_list[x] == 'True':
                input_list[x] = True
            elif ',' in input_list[x]:
                input_list[x] = input_list[x].split(',')
                for y in range(len(input_list[x])):
                    try:
                        input_list[x][y] = float(input_list[x][y])
                    except TypeError:
                        pass
            elif '.' in input_list[x]:
                try:
                    input_list[x] = float(input_list[x])
                except ValueError:
                    pass
            else:
                try:
                    input_list[x] = int(input_list[x])
                except ValueError:
                    pass
        return input_list
        

################################################################################
#                                   START
################################################################################
app = wx.App(False)
frame = mainwindow(None, "Fire Simulation Model")
frame.Show()
app.MainLoop()
