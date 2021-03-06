from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import SlideTransition
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Rectangle

from StudentDetailsWidget import StudentDetailsWidget
from ColorBoxLayout import ColorBoxLayout

from functools import partial
from DateHelper import DateStringToDay, DateStringToEpoch, DateTimeStringToEpoch, TodayEpoch

import copy

#CONSTANTS
itemSpacing = 12
contentPadding = 12

headerHeight = 40 #date header
buttonHeight = 120 #slot buttons       

studentDetailsHeight = 200
navigationBarHeight = 140

profButtonColor = (1,1,1,1)
profButtonTextColor = (0.1,0.1,0.1,1)

class ProfessorsScreen(Screen):    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
        #this data should be a subject        
        self.selectedSubjectID = None

        #this data should be an int
        self.selectedProfIndex = None
        
        boxLayout = ColorBoxLayout(orientation='vertical', color=Color(162/255, 162/255, 165/255,1))
        
        self.bodyContainer = BoxLayout(orientation='horizontal')                

        #navigation bar ==
        self.navigationBar = ColorBoxLayout(orientation='horizontal', size_hint_y=None, height=navigationBarHeight)        
        
        self.backButton = Button(size_hint=(None,1), width= 260, text='< Back', background_color=(0, 0, 0, 0))
        self.backButton.on_press = self.back
                
        navBarTitles = BoxLayout(size_hint_x=None, orientation='vertical', width=800, padding=[20,0,0,8])        
        self.subjectLabel = Label(text='No subject selected', color=(0,0,0,1), size_hint_y=None, height=40, halign="left", pos_hint={'x': 0}, pos=(20, 100))
        self.subjectLabel.bind(size=self.subjectLabel.setter('text_size'))

        self.headerLabel = Label(text='Professors', size_hint_x=None, width=380, font_size=70)
        self.headerLabel.bind(size=self.headerLabel.setter('text_size'))
        navBarTitles.add_widget(self.headerLabel)
        navBarTitles.add_widget(self.subjectLabel)

        self.navigationBar.add_widget(navBarTitles)
        self.navigationBar.add_widget(Widget())
        self.navigationBar.add_widget(self.backButton)
        #end == 

        #profs
        self.scrollView = ScrollView()
        self.contentView = BoxLayout(orientation='vertical', padding=contentPadding, spacing=itemSpacing, pos_hint={'top': 1})
        self.scrollView.add_widget(self.contentView)
        self.profButtons = []

        #slots
        slotsHeight=self.height-navigationBarHeight-studentDetailsHeight
        self.slotsView = SlotsWidget(orientation='vertical', color=Color(228/255,228/255,228/255,1))
        self.slotsView.confirm_slot_callback = self.confirm_slot
        self.slotsView.logout = self.logout        

        #prof detail        
        self.profDetailsView = ProfDetailsWidget(orientation='vertical', color=Color(248/255,248/255,248/255,1))

        self.bodyContainer.add_widget(self.scrollView)         
        self.bodyContainer.add_widget(self.slotsView)
        self.bodyContainer.add_widget(self.profDetailsView)

        boxLayout.add_widget(self.navigationBar)
        boxLayout.add_widget(self.bodyContainer)       

        self.add_widget(boxLayout)     
        
        self.studentDetailsWidget = StudentDetailsWidget(size_hint_y=None, height=studentDetailsHeight)
        boxLayout.add_widget(self.studentDetailsWidget)         

    #This is to retrieve the data from dbManager
    def get_subject_data(self):                        
        if self.selectedSubjectID != None:
            subject = self.parent.dbManager.structured_data['modules'][self.selectedSubjectID]
            return subject

    #This is to update the navigation bar subtitle
    def select_subject(self, subjectID):
        self.selectedSubjectID = subjectID                
        self.update()

    #This retrieves the details of the current student logged in
    def get_student_data(self):
        if self.parent:
            return self.parent.dbManager.structured_data['current']

    #This updates the user interface at the bottom of the screen, showing student data
    def set_student_data(self, student_data):
        self.student_data = student_data
        self.studentDetailsWidget.set_student_data(student_data)     
        self.slotsView.student_data = student_data   

    #This should be run after confirming a booking in order to update all information displayed
    def reloadData(self):
        newStructuredData = self.parent.dbManager.reloadStructuredData()                
        print(newStructuredData["current"]["credits"])
        self.update()

    #Update user interface when navigating to this screen
    def on_pre_enter(self, *args):                
        self.update()

    #Reset when leaving screen
    def on_leave(self, *args):
        #reset all views
        self.selectedSubjectID = None
        self.selectedProfIndex = None
        self.update()
        self.slotsView.set_slots([]) 
        self.profDetailsView.reset_prof_data()             


    #This updates the userinterface:
    # - Updates navigation subtitle
    # - Updates Professors buttons and selection    
    def update(self):
        if self.selectedSubjectID != None:            
            subject = self.get_subject_data()
            self.subjectLabel.text = '{0} {1}'.format(subject['id'], subject['name'])

        student_data = self.get_student_data()

        if student_data:
            self.studentDetailsWidget.set_student_data(student_data)     
            self.slotsView.student_data = student_data   

        self.contentView.clear_widgets()  
        self.profButtons = []      
        buttonHeight = 200        
        for i in range(len(self.get_profs())):            
            profButton = Button(background_normal='', color=profButtonTextColor, font_size=50)            
            profButton.size_hint_y = None 
            profButton.height = buttonHeight
            profButton.text = self.get_prof_at_index(i)['name']
            profButton.on_press=partial(self.select_prof, i)            
            self.contentView.add_widget(profButton)
            self.profButtons.append(profButton)

        
        #if there is already a prof selected, reselect it to update user interface
        if self.selectedProfIndex != None:
            self.select_prof(self.selectedProfIndex)

        self.contentView.size_hint_y = None
        self.contentView.height = len(self.get_profs())*(buttonHeight + itemSpacing) - itemSpacing + 2*contentPadding
        
    def back(self):
        self.parent.transition = SlideTransition(direction="right")
        self.parent.current = 'SUBJECTS_SCREEN'

    #When a prof button is pressed
    def select_prof(self, index):  
        self.reset_button_colors()    
        
        #if attempted to select a prof that is out of range, deselect all
        if index >= len(self.get_profs()):
            self.selectedProfIndex = None            
            self.slotsView.set_slots([])
            self.profDetailsView.reset_prof_data()
        else:
            self.selectedProfIndex = index
            self.profButtons[index].background_color = (142/255, 229/255, 179/255,1)
            self.profButtons[index].color = profButtonColor

            self.slotsView.set_slots(self.get_prof_at_index(index)['slots'])
            self.profDetailsView.set_prof_data(self.get_prof_at_index(index))

    
    def reset_button_colors(self):
        for button in self.profButtons:
            button.background_color = profButtonColor
            button.color = profButtonTextColor
            button.background_normal=''

    def get_profs(self):
        subjectData = self.get_subject_data()
        return subjectData['professors'] if subjectData != None else []

    def get_prof_at_index(self, index):
        subjectData = self.get_subject_data()        
        return subjectData['professors'][index] if subjectData != None else []

    #returns the slot that was confirmed
    def confirm_slot(self, slot_uuid):        
        confirmed_slot = self.parent.dbManager.confirm_slot(slot_uuid)

        if confirmed_slot == None:
            return None        

        #after confirming a slot, reload the data to update student and slots data 
        self.reloadData()        
        return confirmed_slot

    def logout(self):
        self.parent.transition = SlideTransition(direction="right")
        self.parent.current = 'LOGIN_SCREEN'

class SlotsWidget(ColorBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.scrollView = ScrollView()
        self.contentView = BoxLayout(orientation='vertical', padding=contentPadding, spacing=itemSpacing)    #, pos_hint={'top': 1}
        self.scrollView.add_widget(self.contentView)
        self.add_widget(self.scrollView)
        self.student_data = {}

    #Takes in a list of slots and seperates by date
    def categorize_slots(self, slots):
        output = {}                                

        for slot in slots:
            if slot['date'] in output.keys():
                output[slot['date']].append(slot)
            else:
                output[slot['date']] = [slot]

        return output     

    #Sorts by datetime, filters only those not booked, and filters those that are only in the future
    def sort_filter_slots(self, input_slots):
        output = []
        slots = copy.copy(input_slots)
        slots.sort(key=lambda x: DateTimeStringToEpoch(x['date']+' '+x['time']))
        
        for slot in slots:
            if slot['student_id'] != 'null': #if booked, ignore
                continue

            if DateTimeStringToEpoch(slot['date']+' '+slot['time']) < TodayEpoch(): #if old, ignore
                continue

            output.append(slot)

        return output

    #This is called by professors screen whenever a prof is selected. Comes as a list
    def set_slots(self, slots):                        

        self.contentView.clear_widgets()

        filtered_slots = self.sort_filter_slots(slots) #filters out slots that are not booked yet        
        cat_slots = self.categorize_slots(filtered_slots) #categorizes it by date into a dictionary
        
        self.slotsData = filtered_slots #keeps a reference to the slots it is currently displaying (So that it knows what to do on selection)         
                
        #Generate headers that seperate slots by dates. 
        for date in cat_slots.keys():
            slotlist = cat_slots[date]

            date_header_text = '{} ({})'.format(date, DateStringToDay(date)) 

            day_height = len(slotlist)*buttonHeight + headerHeight            
            day_header = Label(text=date_header_text, size_hint_y=None, height=headerHeight, halign="left", valign='center', color=profButtonTextColor)            
            day_header.bind(size=day_header.setter('text_size'))            
            self.contentView.add_widget(day_header)
               
            for i in range(len(slotlist)):            
                thisslot = slotlist[i]                                
                slotButton = Button(background_normal='',color=profButtonTextColor, font_size=40)            
                slotButton.size_hint_y = None 
                slotButton.height = buttonHeight
                slotButton.text = thisslot['time']
                slotButton.on_press=partial(self.select_slot, filtered_slots.index(thisslot))           
                self.contentView.add_widget(slotButton)                
                
        self.contentView.size_hint_y = None        

        number_of_slots = len(filtered_slots)
        number_of_headers = len(cat_slots.keys())

        self.contentView.height = number_of_slots*(buttonHeight)+ 2*contentPadding + number_of_headers*headerHeight + (number_of_slots + number_of_headers-1) * itemSpacing   
        

    def select_slot(self, index):            
        selectedSlot = self.slotsData[index]

        modalview = ModalView(size_hint=(None,None), width=600, height=400)
        # view = ModalView(auto_dismiss=False)
        container = ColorBoxLayout(orientation='vertical', color=Color(1,1,1,1))

        headerLabel = Label(text='Confirm Booking', font_size=30, color=(0,0,0,1))        

        dateLabel = Label(text='Date: {0}'.format(selectedSlot['date']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        timeLabel = Label(text='Time: {0}'.format(selectedSlot['time']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        costLabel = Label(text='Cost: {0} credits'.format(50),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        remaindingLabel = Label(text='Remainder: {0} credits'.format(self.student_data['credits'] - 50),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)

        buttonRow = BoxLayout(orientation='horizontal')
        
        cancelButton = Button(text='Cancel', size_hint=(None, None), width=300, height=80)
        cancelButton.on_press = self.close_modal
        confirmButton = Button(text='Confirm', size_hint=(None, None), width=300, height=80)
        confirmButton.on_press = partial(self.confirm_slot, selectedSlot['id'])            
        buttonRow.add_widget(cancelButton)     
        buttonRow.add_widget(confirmButton)

        container.add_widget(headerLabel)        
        container.add_widget(dateLabel)        
        container.add_widget(timeLabel)        
        container.add_widget(costLabel)        
        container.add_widget(remaindingLabel)        
        container.add_widget(buttonRow)
        modalview.add_widget(container)        
        self.modalview = modalview

        self.open_modal()    

    def on_confirmed_booking(self, confirmed_slot):
        confirmationmodalview = ModalView(size_hint=(None,None), width=600, height=400)
        # view = ModalView(auto_dismiss=False)
        container = ColorBoxLayout(orientation='vertical', color=Color(1,1,1,1))

        headerLabel = Label(text='Booking Confirmed!', font_size=30, color=(0,0,0,1))        

        slotidLabel = Label(text='Confirmation ID: \n {0}'.format(confirmed_slot['id']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60, halign='center')
        dateLabel = Label(text='Date: {0}'.format(confirmed_slot['date']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        timeLabel = Label(text='Time: {0}'.format(confirmed_slot['time']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        costLabel = Label(text='Cost: {0} credits'.format(50),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)
        remainderLabel = Label(text='Credits Left: {0}'.format(self.student_data['credits']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60)

        buttonRow = BoxLayout(orientation='horizontal')
        
        backButton = Button(text='Back', size_hint=(None, None), width=300, height=80)
        backButton.on_press = self.close_confirmation_modal
        logoutButton = Button(text='Logout', size_hint=(None, None), width=300, height=80)
        logoutButton.on_press = partial(self.requestlogout)            
        buttonRow.add_widget(backButton)     
        buttonRow.add_widget(logoutButton)

        container.add_widget(headerLabel)          
        container.add_widget(slotidLabel)        
        container.add_widget(dateLabel)        
        container.add_widget(timeLabel)        
        # container.add_widget(costLabel)        
        container.add_widget(remainderLabel)        
        container.add_widget(buttonRow)
        confirmationmodalview.add_widget(container)        
        self.confirmationmodalview = confirmationmodalview
        self.confirmationmodalview.open()

    def on_failed_booking(self):        
        confirmationmodalview = ModalView(size_hint=(None,None), width=600, height=400)
        # view = ModalView(auto_dismiss=False)
        container = ColorBoxLayout(orientation='vertical', color=Color(1,1,1,1))

        headerLabel = Label(text='Booking Failed :(', font_size=30, color=(0,0,0,1))        

        # slotidLabel = Label(text='Confirmation ID: \n {0}'.format(confirmed_slot['id']),font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60, halign='center')        
        descriptionLabel = Label(text='You have insufficient credits!\nPlease contact your professor \nto allocate credits.',font_size=23, color=(0,0,0,1), size_hint=(1, None), height=60, halign='center')        
        buttonRow = BoxLayout(orientation='horizontal')
        
        backButton = Button(text='Back', size_hint=(None, None), width=300, height=80)
        backButton.on_press = self.close_confirmation_modal
        logoutButton = Button(text='Logout', size_hint=(None, None), width=300, height=80)
        logoutButton.on_press = partial(self.requestlogout)            
        buttonRow.add_widget(backButton)     
        buttonRow.add_widget(logoutButton)

        container.add_widget(headerLabel)          
        container.add_widget(descriptionLabel)   
        container.add_widget(buttonRow)
        confirmationmodalview.add_widget(container)        
        self.confirmationmodalview = confirmationmodalview
        self.confirmationmodalview.open()

    def open_modal(self):        
        self.modalview.open()
        
    def close_modal(self):
        self.modalview.dismiss()

    def close_confirmation_modal(self):
        try:
            self.close_modal()        
        finally:
            pass
        self.confirmationmodalview.dismiss()

    
    #calls a function in ProfessorScreen class, that accesses DBManager to confirm the slot
    def confirm_slot(self, slot_uuid):
        confirmedBooking = self.confirm_slot_callback(slot_uuid)

        #signifies that the booking has failed due to insufficient credits
        if confirmedBooking == None:
            self.on_failed_booking()
            return


        self.close_modal()    
        print('confirmed: ', confirmedBooking['id'])
        self.on_confirmed_booking(confirmedBooking)        

    def requestlogout(self):
        self.close_confirmation_modal()
        self.logout()


class ProfDetailsWidget(ColorBoxLayout):   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)        

        self.padding = [24,18,0,0]

        self.headerLabel = ProfDetailLabel(text='Professor Details:')
        self.add_widget(self.headerLabel)

        self.profNameLabel = ProfDetailLabel(text='Name: ')
        self.add_widget(self.profNameLabel)
        
        self.profEmailLabel = ProfDetailLabel(text='Email: ')
        self.add_widget(self.profEmailLabel)
        
        self.profContactLabel = ProfDetailLabel(text='Contact: ')
        self.add_widget(self.profContactLabel)        

        self.add_widget(Widget())

        self.reset_prof_data()

    #When a prof is selected, this is called and the information displayed is updated
    def set_prof_data(self, prof_data):
        self.prof_data = prof_data
        self.update()        

    def reset_prof_data(self):
        self.prof_data = None

        self.update()

    def update(self):
        if self.prof_data == None:
            self.profNameLabel.text = 'No Selection'
            self.profEmailLabel.text = ''
            self.profContactLabel.text = ''
        else:    
            self.profNameLabel.text = 'Name: ' + self.prof_data['name']
            self.profEmailLabel.text = 'Email: ' + self.prof_data['email']
            self.profContactLabel.text = 'Contact: ' + self.prof_data['contact']
        


class ProfDetailLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.bind(size=self.setter('text_size'))
        self.color = (0,0,0,1)
        self.size_hint_y = None
        self.height = 40
