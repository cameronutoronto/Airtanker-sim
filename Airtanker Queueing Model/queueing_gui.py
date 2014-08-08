import wx #Python module for generating a GUI
import os #needed to join paths in open/save
##import random
import sys # Redirect Standard Out
import threading
import multiprocessing
import simple_queue_model
##from time import sleep

class Redirect_Stdout(): #Redirect Stdout to textctrl
    def __init__(self, stdout_pt, new_out):
        self.stdout_pt = stdout_pt
        self.new_out = new_out
        self.log_pt = new_out
        
    def write(self, string1):
        self.new_out.WriteText(string1)
        
    def reset(self): #DOESNT WORK
        self.new_out = self.stdout_pt

    def setup(self):
        self.new_out = self.log_pt

class mainwindow(wx.Frame):
    def __init__(self, parent, title):
        # Inputs passed to fbp system for calculating and printing outputs
        self.inputs = ['' for x in range(6)]
        self.dirname = ''
        self.input_file = "Simple_Queue_Model_Inputs.txt"
        #Creating the window, setting it blue, and adding a text box to it
        wx.Frame.__init__(self, parent, title = title, size =(1000, 800))
        self.SetBackgroundColour((215, 80, 80))
        self.logger = wx.TextCtrl(self, size=(500, 250),style=wx.TE_MULTILINE |\
                                  wx.TE_RICH)
        self.stdout_pt = sys.stdout
        sys.stdout = Redirect_Stdout(self.stdout_pt, self.logger)
        self.CreateStatusBar()
        self.gauge = wx.Gauge(self)
        self.Bind(wx.EVT_CLOSE, self.OnExit) #bind x button

        #Setting up the "File" menu option
        filemenu = wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open", \
                                   "Open a Text File of Inputs")
        menuSave = filemenu.Append(wx.ID_SAVE, \
                                   "&Save", "Save the Results to a Text File")
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", \
                                    "Information About the Program")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "&Exit", "Terminate the Program")

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



        #Binding all the menu options to their respective functions
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        #Calculate Button
        self.calculate_button = wx.Button(self, label="Calculate")
        self.Bind(wx.EVT_BUTTON, lambda x: self.OnClick(x, 77),
                  self.calculate_button)
        self.make_bold(self.calculate_button)
        
        #Clear Button
        self.clear_button = wx.Button(self, label = "Clear")
        self.Bind(wx.EVT_BUTTON, self.Clear, self.clear_button)
        self.make_bold(self.clear_button)

        #Clear Button
        self.clear_all_button = wx.Button(self, label = "Clear All")
        self.Bind(wx.EVT_BUTTON, self.ClearAll, self.clear_all_button)
        self.make_bold(self.clear_all_button)


        #Fires Per Hour
        self.fires_prompt = wx.StaticText(self, label = "Fires Per Hour: ")
        self.fires = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.fires_prompt, pos = (0, 0))
        grid.Add(self.fires, pos = (0, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 0), self.fires)
        self.make_bold(self.fires_prompt)
        self.make_bold(self.fires)
        
        #Number of Airtankers
        self.airtanker_prompt = wx.StaticText(self, label =
                                              "Number of Airtankers: ")
        self.airtanker = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.airtanker_prompt, pos = (1, 0))
        grid.Add(self.airtanker, pos = (1, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 1), self.airtanker)
        self.make_bold(self.airtanker_prompt)
        self.make_bold(self.airtanker)
        
        #Service Time
        self.service_prompt = wx.StaticText(self, label =
                                            "Service Rate: ")
        self.service = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.service_prompt, pos = (2, 0))
        grid.Add(self.service, pos = (2, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 2), self.service)
        self.make_bold(self.service_prompt)
        self.make_bold(self.service)

        #Simulation Length
        self.run_length_prompt = wx.StaticText(self, label =
                                               "Simulation Length (hours): ")
        self.run_length = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.run_length_prompt, pos = (3, 0))
        grid.Add(self.run_length, pos = (3, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 3), self.run_length)
        self.make_bold(self.run_length_prompt)
        self.make_bold(self.run_length)
        
        #Bin Size
        self.bin_size_prompt = wx.StaticText(self, label = "Bin Size (hours): ")
        self.bin_size = wx.TextCtrl(self, value="", \
                                      size = (100, -1))
        grid.Add(self.bin_size_prompt, pos = (4, 0))
        grid.Add(self.bin_size, pos = (4, 1))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 4), self.bin_size)
        self.make_bold(self.bin_size_prompt)
        self.make_bold(self.bin_size)

        #Directory of Coefficients
        self.save_graph_text = wx.StaticText(self, label =
                                               "Save Graph Location: ")
        self.save_graph_input = wx.TextCtrl(self, value='', size = (150, -1))
        grid.Add(self.save_graph_text, pos = (5, 0))
        grid.Add(self.save_graph_input, pos = (6, 0))
        self.Bind(wx.EVT_TEXT, lambda x: self.EvtText(x, 5), \
                  self.save_graph_input)
        self.make_bold(self.save_graph_text)
        self.make_bold(self.save_graph_input)

        #Browse Button Coefs
        self.browse_button_save = wx.Button(self, label = "Browse..")
        self.Bind(wx.EVT_BUTTON, self.OnSave, self.browse_button_save)
        self.make_bold(self.browse_button_save)
        grid.Add(self.browse_button_save, pos = (7, 0))



        #Setup sizers and place them
        hSizer.AddSpacer(10)
        hSizer.Add(grid, 0, wx.EXPAND, 10)
        hSizer.AddSpacer(10)
        hSizer.Add(self.logger, 1, wx.EXPAND)
        hSizer.AddSpacer(10)
        mainSizer.AddSpacer(10)
        mainSizer.Add(hSizer, 1,wx.EXPAND)
        mainSizer.AddSpacer(10)
        mainSizer.Add(self.calculate_button, 0, wx.EXPAND | wx.CENTER)
        mainSizer.AddSpacer(5)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(self.clear_button, 1, wx.LEFT)
        buttonSizer.AddSpacer(5)
        buttonSizer.Add(self.clear_all_button, 1, wx.LEFT)
        mainSizer.Add(buttonSizer, 0)
        mainSizer.Add(self.gauge, proportion=0, flag=wx.EXPAND)
        self.SetSizerAndFit(mainSizer)

        self.Centre()

        self.boxes = [self.fires, self.airtanker, self.service, self.run_length,
                      self.bin_size, self.save_graph_input]
        self.OnStartUp()


    def OnAbout(self, e):
        '''Displays a pupup box that gives information about this software'''
        dlg = wx.MessageDialog(self, "This Graphical-" +\
                               "User-Interface for _____ was created by" +\
                               " Cameron Buttazzoni for research " + \
                               "purposes at the Fires Management " +\
                               "System Laboratory in the Faculty of Forestry"+\
                               " at the University of Toronto\n\n" +\
                               "THIS SOFTWARE IS NOT VALIDATED OR CERTIFIED" +\
                               " FOR OPERATIONAL USE"\
                               + "\nCopyright: Cameron Buttazzoni\n\n", \
                               "About FBP", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, e):
        '''Exit the software'''
        temp = ''
        try:
            in_file = open(self.input_file, 'w')
            for x in range(len(self.inputs) - 1):
                temp += str(self.inputs[x]) + ','
            temp += str(self.inputs[-1])
            in_file.write(temp)
            in_file.close()
        except IOError:
            pass
        raise SystemExit

    def OnSave(self, e):
        '''Select a file to save the graph to'''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, \
                            "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.inputs[5] = os.path.join(self.dirname, self.filename)
            self.boxes[5].SetValue(os.path.join(self.dirname, self.filename))
        dlg.Destroy()

    def OnOpen(self, e):
        '''Open a csv text file of inputs and prints the outputs to logger'''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, \
                            "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            print "Calculating... (This may take a long time)"
            sys.stdout = sys.__stdout__
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            in_file = open(os.path.join(self.dirname, self.filename), 'r')
            in_file.seek(0)
            line = in_file.readline()
            while line != '':
                if line[-1] == '\n':
                    temp = line[:-1].split(',')
                else:
                    temp = line.split(',')
                for x in range(len(temp)):
                    try:
                        self.inputs[x] = temp[x]
                    except IndexError:
                        pass
##                self.OnClick(None)
                calc_thread = threading.Thread(target=self.OnClick,
                                        args = (None, None))
                calc_thread.start()
                line = in_file.readline()
            in_file.close()
        dlg.Destroy()

    def OnClick(self, e, num):
        '''Run the queueing model'''
        if num == 77:
            sys.stdout = Redirect_Stdout(self.stdout_pt, self.logger)
        try:
            self.inputs[0] = float(self.inputs[0])
            self.inputs[1] = int(self.inputs[1])
            self.inputs[2] = float(self.inputs[2])
            self.inputs[3] = float(self.inputs[3])
            self.inputs[4] = float(self.inputs[4])
        except ValueError:
            print "\nInvalid Inputs...\n"
            return
        temp = []
        for x in range(len(self.inputs)):
            temp.append(self.inputs[x])
        queue_thread = threading.Thread(target=simple_queue_model.main_func,
                                        args = (temp,))
        queue_thread.setDaemon(True)
        queue_thread.start()

    def Clear(self, e):
        '''Clear the logger'''
        self.logger.Clear()

    def ClearAll(self, e):
        '''Clear logger and all inputted values'''
        self.logger.Clear()

    def EvtText(self, e, num):
        '''Entering text sets input to new entered value'''
        self.inputs[num] = e.GetString().encode('ascii', 'ignore')

    def make_bold(self, text):
        '''Makes prompts and button text bold'''
        temp_font = text.GetFont()
        temp_font.SetWeight(wx.BOLD)
        text.SetFont(temp_font)

    def OnHelp(self, e):
        '''Opens a box displaying this on help'''
        help_text = "Help Information for this GUI:\n\n"
        help_dlg = wx.MessageDialog(self, help_text, "Software Help", wx.OK)
        help_dlg.ShowModal()
        help_dlg.Destroy()

    def OnStartUp(self):
        '''Saves inputs to a file'''
        try:
            in_file = open(self.input_file, 'r')
            temp = in_file.readline().split(',')
            for x in range(len(self.inputs)):
                self.inputs[x] = temp[x]
                self.boxes[x].SetValue(self.inputs[x])
            in_file.close()
        except IOError:
            in_file = open(self.input_file, 'w')
            in_file.close()
        except IndexError:
            in_file.close()


def run_gui():
    '''Run GUI'''
    app = wx.App(False)
    frame = mainwindow(None, "Fire Queueing Model")
    frame.Show()
    app.MainLoop()
    
#run the GUI
if __name__ == '__main__':
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
##    app = wx.App(False)
##    frame = mainwindow(None, "Fire Behaviour Prediction System")
##    frame.Show()
##    app.MainLoop()
    run_everything = multiprocessing.Process(target = run_gui)
    run_everything.start()
    run_everything.join()
