#!/usr/bin/env python3
#MPH mouse fix for Linux, ver 1.7
#S.D.G.

"""
Notes:

The mouse remains down while looking about. If we detect a mouse left down, we shoot.
If we detect a mouse left up, we stop shooting AND put the mouse left back down again.

Any bound keypress must:
- Lift the mouse left for ??? delay.
- Move the mouse to the correct button.
- Click for the required duration (mainly different for scanvisor).
- Move back to the center.
- Lower the mouse left.
"""

import mouse
import keyboard
import pyautogui #For HUD detection and working around faults in the mouse and keyboard modules
import time
import queue

#Disable all delays in pyautogui
pyautogui.MINIMUM_DURATION=0
pyautogui.MINIMUM_SLEEP=0
pyautogui.PAUSE=0

#Disable failsafe that kills the program if the mouse goes into the corner of the screen, as this can be a problem in fullscreen emulators
pyautogui.FAILSAFE=False

SCALE = (900, 674) #Size of reference window
TOUCH_CENTER = SCALE[0]//2, SCALE[1]//2

MOUSE_RESET_WAIT = 35/1000 #pertains to the time before the mouse moves again, adjust this if your camera keeps jerking when your cursor is reset to center.
BUTTON_WAIT = 120/1000 #pertains to the time before the mouse moves after pressing a button, adjust this if you get ghost inputs (buttons not properly pressed).
KEY_WAIT = 50/1000 #pertains to the time between key inputs, this is used for some macros such as sprinting and crouching in the COD Games, adjust this if those inputs are not caught.
HUD_CHECK_INTERVAL = 1 #How often to check if Samus's HUD is shown
PAUSE_INTERVAL = 0.1 #How often to run the pause loop
BUTTON_HOLD_INTERVAL = 0.05 #How often to rerun the mouse movement command to keep the cursor locked onto a button

#Limits of where to wrap the mouse
MOUSE_DRAG_AREA_X = (0, SCALE[0])
MOUSE_DRAG_AREA_Y = (225, 495)

MOUSE_DRAG_MARGIN = 5 #How close we can get to the edge before we wrap
MOUSE_DROP_MARGIN = MOUSE_DRAG_MARGIN*2 #How far away from the other edge to drop the cursor when we wrap

#MOUSE_DRAG_AREA_SQSIZE = min((MOUSE_DRAG_AREA_X[1]-MOUSE_DRAG_AREA_X[0], MOUSE_DRAG_AREA_Y[1]-MOUSE_DRAG_AREA_Y[0])) #Edge size of a square area that we can drag in, currently for boost ball
MOUSE_DRAG_AREA_CENTER = sum(MOUSE_DRAG_AREA_X)//2, sum(MOUSE_DRAG_AREA_Y)//2 #Center of draggable area

BOOST_SWIPE_SIZE = 400 #The pixel length a boost swipe must be for the ROM to recognize it

IS_HUD_COORDS = (MOUSE_DRAG_MARGIN, SCALE[1] - MOUSE_DRAG_MARGIN) #Coordinates to check for color match if we are in HUD or in the ship
IS_MORPHBALL_COORDS = (800, 530) #Coordinates to check if we are in morphball mode or not
VARIA_ORANGE = 211, 154, 73 #Color of varia components in HUD
COLOR_TOLERANCE = 10

#Keys that the DS emulator is set to interpret as D-pad
DPAD_KEYS = {"w":"UP",
             "s":"DOWN",
             "d":"RIGHT",
             "a":"LEFT"
             }

#Direction names as mapped to screen coordinate factors
DIRECTIONS = {"UP":(0, -1),
              "DOWN":(0, 1),
              "RIGHT":(1, 0),
              "LEFT":(-1, 0)
              }

DEFAULT_BB_DIRECTION = "UP" #Default direction to touch-based boost ball in

#Most key bindings
KEYBINDS = {'q': 'MAIN_WEAPON',
            'e': 'MISSILES',
            'r': 'THIRD_WEAPON',
            'f': 'SCAN_VISOR',
            'z': 'PAGE_LEFT',
            'c': 'PAGE_RIGHT',
            'x': 'OK',
            'v': 'YES',
            'b': 'NO',
            'ctrl': 'MORPH_BALL',
            'tab': 'BOOST_BALL'
            }
    
TOUCHBUTTONS = { #Each button's position, and how long to press it
    "MAIN_WEAPON" : ((300, 112), BUTTON_WAIT),
    "MISSILES" : ((440, 113), BUTTON_WAIT),
    "THIRD_WEAPON" : ((605, 120), BUTTON_WAIT),
    "SCAN_VISOR" : ((450, 608), 0.5),
    "PAGE_LEFT" : ((250, 495), BUTTON_WAIT),
    "PAGE_RIGHT" : ((650, 495), BUTTON_WAIT),
    "OK" : ((450, 495), BUTTON_WAIT),
    "YES" : ((337, 495), BUTTON_WAIT),
    "NO" : ((563, 495), BUTTON_WAIT),
#    "PAGE_LEFT" : ((288, 515), BUTTON_WAIT),
#    "PAGE_RIGHT" : ((612, 515), BUTTON_WAIT),
    "MORPH_BALL" : ((775, 585), BUTTON_WAIT),
    "WEAPON_SELECT" : ((810, 120), BUTTON_WAIT)
    }

WEAPONSELECT_BUTTONS = ( #Positions of each weapon in the weapon select pie menu
    (327, 168),
    (341, 302),
    (373, 439),
    (485, 555),
    (622, 590),
    (763, 604),
    )

#Mouse bindings
MOUSEBINDS = {
    "left" : "fire",
    "middle" : "reset_mouse",
    "right" : "zoom_out"
    }

#Remaining key bindings
PAUSE_KEY="\\" #Pause the mouse fix manually
KILL_KEY="backspace" #Kill the mouse fix
FIRE_KEY="n" #What key the emulator has set for the L shoulder
ZOOMOUT_KEY="m" #What key the emulator has set for the R shoulder

class MPHMousefix(object):
    def __init__(self, run=True, multiplayer=False):
        """MouseFix for Metroid Prime: Hunters"""
        self.multiplayer=multiplayer #Use the Varia HUD detector ONLY if we are NOT in multiplayer, because the colors there could be different
        
        self.touch_offset, self.touch_size = self.get_touch_area()
        if run: #Do not start the mouse fix unless run is True
            self.mainloop()
        
    def get_touch_area(self):
        """Get the initial touch area and return touch_offset and touch_size"""
        print("Click opposite corners of the touch area.")
        mouse.wait(target_types=("down"))
        p1=mouse.get_position()
        print(p1)
        mouse.wait(target_types=("down"))
        p2=mouse.get_position()
        print(p2)
        touch_offset = min((p1[0], p2[0])), min((p1[1], p2[1]))
        touch_size = max((p1[0], p2[0])) - touch_offset[0], max((p1[1], p2[1])) - touch_offset[1]
        print("touch offset", touch_offset, "\ntouch size", touch_size)
        return touch_offset, touch_size

    def get_is_hud(self):
        """Are we in the Varia HUD, not in the ship? Does not work in weapon select"""
        return pyautogui.pixelMatchesColor(*self.rel_to_abs(*IS_HUD_COORDS), VARIA_ORANGE, COLOR_TOLERANCE)

    def get_is_morphball(self):
        """Are we in morphball mode, not standing? Assumes we are in the Varia HUD"""
        return pyautogui.pixelMatchesColor(*self.rel_to_abs(*IS_MORPHBALL_COORDS), VARIA_ORANGE, COLOR_TOLERANCE)
    
    def mainloop(self):
        """Start the program"""
        self.running=True
        keyboard.add_hotkey(KILL_KEY, self.kill) #Kill the program when this key is pressed, no matter what
        
        keyevents=keyboard.start_recording()[0] #Get a keyboard events queue
        
        mouseevents=queue.Queue()
        mouse.hook(mouseevents.put_nowait) #Get a mouse events queue
        
        self.reset_mouse()
        
        last_hudcheck=0 #Time of last HUD check
        was_hud=True
        is_hud=True
        is_paused=False

        while self.running:
            if is_paused:
                while not keyevents.empty():
                    e = keyevents.get()
                    if e.event_type == "down" and e.name == PAUSE_KEY:
                        is_paused = not is_paused
                            
                self.clear_queue(mouseevents) #Clear mouse events queue while waiting to unpause
                    
                if not is_paused: #We were unpaused in this check
                    self.reset_mouse()
                    print("Resumed.")
                else: #We are still paused, so wait and continue
                    time.sleep(PAUSE_INTERVAL)
                    continue

            #If we are in singleplayer and it has been more than HUD_CHECK_INTERVAL seconds since we last checked for Samus's HUD...
            if not self.multiplayer and time.time()-last_hudcheck>HUD_CHECK_INTERVAL:
                last_hudcheck=time.time()
                is_hud=self.get_is_hud()
                if not was_hud and is_hud:
                    print("Hud detected. Engaging...")
                    self.reset_mouse()
                elif not is_hud and was_hud:
                    print("Hud disappeared. Pausing...")
                    pyautogui.mouseUp()
                was_hud=is_hud
                if not is_hud:
                    time.sleep(HUD_CHECK_INTERVAL)

                    #Clear mouse and keyboard events while paused
                    for q in (keyevents, mouseevents):
                        self.clear_queue(q)
                    
                    continue
                
            if not keyevents.empty(): #Do not hold the loop waiting for a keyboard event
                e = keyevents.get()
                if e.event_type != "down": #Only kare about key down events
                    continue
                if e.name in KEYBINDS.keys(): #Deals with keys in the key bindings configuration
                    print(KEYBINDS[e.name])
                    try:
                        self.touchbutton(TOUCHBUTTONS[KEYBINDS[e.name]]) #Push the button associated with the keybinding
                    except KeyError: #Not a regular touchbutton
                        exec("self."+KEYBINDS[e.name].lower()+"(e)")
                    
                elif e.name.isnumeric() and 0 < int(e.name) <= len(WEAPONSELECT_BUTTONS): #Pressed a number key, is in range of weapons
                    print("Weapon %i selected" % int(e.name))
                    self.weaponselect(int(e.name))
                    
                elif e.name == PAUSE_KEY: #Pause the mouse fix
                    print("Paused")
                    pyautogui.mouseUp(_pause = False)
                    is_paused=True
                    continue
                        
            if not mouseevents.empty(): #Do not hold the loop waiting for a mouse event
                e = mouseevents.get()
                if type(e)==mouse.ButtonEvent and e.button in MOUSEBINDS.keys():
                    exec("self."+MOUSEBINDS[e.button]+"(e)") #Run one of our three mouse bound functions

            if not mouse.is_pressed(): #Give up wrap if mouse is actually held down
                self.mousewrap(*self.abs_to_rel(*mouse.get_position())) #Perform a mouse wrap enforcement check

    def clear_queue(self, q):
        """Clears the passed queue"""
        while not q.empty():
            q.get()
            
    def kill(self):
        """End the program."""
        self.running=False
        try:
            pyautogui.mouseUp(_pause = False)
            keyboard.stop_recording()
        finally:
            quit()
    
    def weaponselect(self, weapon):
        """Select a weapon by index 1-6"""
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*TOUCHBUTTONS["WEAPON_SELECT"][0])
        pyautogui.mouseDown(_pause = False)
        time.sleep(TOUCHBUTTONS["WEAPON_SELECT"][1])
        self.goto_relative(*WEAPONSELECT_BUTTONS[weapon-1])
        time.sleep(BUTTON_WAIT)
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.reset_mouse()

    def fire(self, e):
        """Fire the gun, or stop firing"""
        if e.event_type=="down":
            pyautogui.keyDown(FIRE_KEY, _pause = False)
        else:
            pyautogui.keyUp(FIRE_KEY, _pause = False)
            if self.out_of_drag_bounds(*self.abs_to_rel(*mouse.get_position())) != (0, 0): #Mouse moved out of bounds while holding a charged shot
                self.reset_mouse()
            else:
                pyautogui.mouseDown(_pause = False) #The mouse has been truly released, so simulate pressing it again

    def zoom_out(self, e):
        """Press or release the zoom out key"""
        #print("ZOOMOUT_KEY "+e.event_type)
        if e.event_type == "down":
            pyautogui.keyDown(ZOOMOUT_KEY, _pause = False)
        elif e.event_type == "up":
            pyautogui.keyUp(ZOOMOUT_KEY, _pause = False)

        if not self.multiplayer and self.get_is_morphball(): #Sacrifice steering for via-button boost ball
            if e.event_type == "down":
                pyautogui.mouseUp()
            elif e.event_type == "up":
                self.reset_mouse()

    def boost_ball(self, e):
        """Perform a touch-based boost ball"""
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        
        direction=[0, 0]
        
        for key in DPAD_KEYS.keys(): #Sum input directions. If they contradict, they will zero out
            if keyboard.is_pressed(key):
                #print(key)
                direction[0]+=DIRECTIONS[DPAD_KEYS[key]][0]
                direction[1]+=DIRECTIONS[DPAD_KEYS[key]][1]
                
        if direction == [0, 0]: #If there is no direction or all input directions cancelled out, use the default
            direction = DIRECTIONS[DEFAULT_BB_DIRECTION]

        end_x = TOUCH_CENTER[0]+BOOST_SWIPE_SIZE//2*direction[0]
        end_y = TOUCH_CENTER[1]+BOOST_SWIPE_SIZE//2*direction[1]

        start_x = TOUCH_CENTER[0]-BOOST_SWIPE_SIZE/2*direction[0]
        start_y = TOUCH_CENTER[1]-BOOST_SWIPE_SIZE//2*direction[1]
        #print("Direction is", direction)
        #print("Boost from ", start_x, start_y, "to", end_x, end_y)
        self.goto_relative(start_x, start_y)
        time.sleep(MOUSE_RESET_WAIT)
        pyautogui.mouseDown(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(end_x, end_y)
        time.sleep(MOUSE_RESET_WAIT)
        self.reset_mouse()

    def out_of_drag_bounds(self, x, y):
        """Check if coordinates are out of dragging bounds, and return x, y tuple of sign of directions"""
        return - (x < MOUSE_DRAG_AREA_X[0] + MOUSE_DRAG_MARGIN) + (x > MOUSE_DRAG_AREA_X[1] - MOUSE_DRAG_MARGIN), - (y < MOUSE_DRAG_AREA_Y[0] + MOUSE_DRAG_MARGIN) + (y > MOUSE_DRAG_AREA_Y[1] - MOUSE_DRAG_MARGIN)
        
    def mousewrap(self, x, y):
        """Check if the mouse needs wrapping and perform if needed"""
        oob = self.out_of_drag_bounds(x, y)
        if oob == (0, 0):
            return

        print("Wrapping mouse")
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(
             (MOUSE_DRAG_AREA_X[1], MOUSE_DRAG_AREA_CENTER[0], MOUSE_DRAG_AREA_X[0])[oob[0] + 1] + MOUSE_DROP_MARGIN * oob[0],
             (MOUSE_DRAG_AREA_Y[1], MOUSE_DRAG_AREA_CENTER[1], MOUSE_DRAG_AREA_Y[0])[oob[1] + 1] + MOUSE_DROP_MARGIN * oob[1])
        pyautogui.mouseDown(_pause = False)

    def rel_to_abs(self, x, y):
        """Convert relative touch position to real screen position"""
        return int(self.touch_offset[0]+x/SCALE[0]*self.touch_size[0]), int(self.touch_offset[1]+y/SCALE[1]*self.touch_size[1])
    
    def abs_to_rel(self, x, y):
        """Convert real screen position to relative touch position"""
        return int((x-self.touch_offset[0])/self.touch_size[0]*SCALE[0]+0.5), int((y-self.touch_offset[1])/self.touch_size[1]*SCALE[1]+0.5)

    def goto_relative(self, x, y):
        """Move the mouse cursor to a relative touch position"""
        #mouse.move(*self.rel_to_abs(x, y))
        pyautogui.moveTo(*self.rel_to_abs(x, y))

    def touchbutton(self, button):
        """Push a touch button in form ((x, y), wait)"""
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*button[0])
        pyautogui.mouseDown(_pause = False)

        for i in range(int(button[1] / BUTTON_HOLD_INTERVAL)): #Lock the mouse onto the button by constantly moving back to it
            time.sleep(BUTTON_HOLD_INTERVAL)
            self.goto_relative(*button[0])
        time.sleep(button[1] % BUTTON_HOLD_INTERVAL)

        self.reset_mouse()
                    
    def reset_mouse(self, e=None):
        """Reset the mouse to the center position"""
        pyautogui.mouseUp(_pause = False)
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*MOUSE_DRAG_AREA_CENTER)
        pyautogui.mouseDown(_pause = False)
        
mmf=MPHMousefix(multiplayer = "y" in input("Are you going into multiplayer? y/[N]: ").lower())
