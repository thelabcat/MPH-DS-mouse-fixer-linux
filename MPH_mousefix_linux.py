#!/usr/bin/env python3
#MPH mouse fix for Linux, ver 1.0
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

SCALE = (900, 674) #Size of reference window
TOUCH_CENTER = SCALE[0]/2, SCALE[1]/2 #Reset point for the mouse

MOUSE_RESET_WAIT = 35/1000 #pertains to the time before the mouse moves again, adjust this if your camera keeps jerking when your cursor is reset to center.
BUTTON_WAIT = 120/1000 #pertains to the time before the mouse moves after pressing a button, adjust this if you get ghost inputs (buttons not properly pressed).
KEY_WAIT = 50/1000 #pertains to the time between key inputs, this is used for some macros such as sprinting and crouching in the COD Games, adjust this if those inputs are not caught.
IS_HUD_INTERVAL=1

#Limits of where to wrap the mouse
MOUSE_DRAG_AREA_X = (0, SCALE[0])
MOUSE_DRAG_AREA_Y = (225, 495)

MOUSE_DRAG_MARGIN = 5 #How close we can get to the edge before we wrap
MOUSE_DROP_MARGIN = MOUSE_DRAG_MARGIN*2 #How far away from the other edge to drop the cursor when we wrap

IS_HUD_COORDS = (MOUSE_DRAG_MARGIN, SCALE[1]-MOUSE_DRAG_MARGIN) #Coordinates to check for color match if we are in HUD or in the ship
VARIA_ORANGE = 211, 154, 73 #Color of varia components in HUD
COLOR_TOLERANCE = 10

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
            'ctrl': 'MORPH_BALL'
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
        self.multiplayer=multiplayer #Use the Varia HUD detector to pause the mouse fix if we are inside the ship ONLY if NOT in multiplayer
        
        if not run: #Do not start the mouse fix unless run is True
            return
        
        self.touch_offset, self.touch_size = self.get_touch_area()
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
    
    def mainloop(self):
        """Start the program"""
        keyboard.add_hotkey(KILL_KEY, quit) #Kill the program when this key is pressed, no matter what
        
        keyevents=keyboard.start_recording()[0] #Get a keyboard events queue
        
        mouseevents=queue.Queue()
        mouse.hook(mouseevents.put_nowait) #Get a mouse events queue
        
        self.reset_mouse()
        
        last_hudcheck=0 #Time of last HUD check
        was_hud=False
        is_hud=False
        
        while True:
            if not self.multiplayer and time.time()-last_hudcheck>IS_HUD_INTERVAL:
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
                    time.sleep(IS_HUD_INTERVAL)
                    continue
                
            if not keyevents.empty(): #Do not hold the loop waiting for a keyboard event
                e = keyevents.get()
                if e.event_type != "down": #Only kare about key down events
                    continue
                if e.name in KEYBINDS.keys(): #Deals with keys in the key bindings configuration
                    print(KEYBINDS[e.name])
                    self.touchbutton(TOUCHBUTTONS[KEYBINDS[e.name]]) #Push the button associated with the keybinding
                    
                elif e.name.isnumeric() and 0 < int(e.name) <= len(WEAPONSELECT_BUTTONS): #Pressed a number key, is in range of weapons
                    print("Weapon %i selected" % int(e.name))
                    self.weaponselect(int(e.name))
                    
                elif e.name == PAUSE_KEY: #Pause the mouse fix
                    print("Paused")
                    pyautogui.mouseUp()
                    keyboard.wait(PAUSE_KEY)
                    while not keyevents.empty():
                        keyevents.get()
                    print("Resumed")
                    self.reset_mouse()
                        
            if not mouseevents.empty(): #Do not hold the loop waiting for a mouse event
                e = mouseevents.get()
                if type(e)==mouse.ButtonEvent and e.button in MOUSEBINDS.keys():
                    exec("self."+MOUSEBINDS[e.button]+"(e)") #Run one of our three mouse bound functions
                    
            self.mousewrap(*self.abs_to_rel(*mouse.get_position())) #Perform a mouse wrap enforcement check

    def weaponselect(self, weapon):
        """Select a weapon by index 1-6"""
        pyautogui.mouseUp()
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*TOUCHBUTTONS["WEAPON_SELECT"][0])
        pyautogui.mouseDown()
        time.sleep(TOUCHBUTTONS["WEAPON_SELECT"][1])
        self.goto_relative(*WEAPONSELECT_BUTTONS[weapon-1])
        time.sleep(BUTTON_WAIT)
        pyautogui.mouseUp()
        time.sleep(MOUSE_RESET_WAIT)
        self.reset_mouse()

    def fire(self, e):
        """Fire the gun, or stop firing"""
        if e.event_type=="down":
            pyautogui.keyDown(FIRE_KEY)
        else:
            pyautogui.keyUp(FIRE_KEY)
            pyautogui.mouseDown() #The mouse has been truly released, so simulate pressing it again

    def zoom_out(self, e):
        """Press or release the zoom out key"""
        exec("pyautogui.key"+e.event_type.title()+"(ZOOMOUT_KEY)")
    
    def mousewrap(self, x, y):
        """Check if the mouse needs wrapping and perform if needed"""
        changed = False #Only give a mouse move command if at least one axis value needs changing

        #Wrap X
        if x < MOUSE_DRAG_AREA_X[0] + MOUSE_DRAG_MARGIN:
            x = MOUSE_DRAG_AREA_X[1] - MOUSE_DROP_MARGIN
            changed = True
        elif x > MOUSE_DRAG_AREA_X[1] - MOUSE_DRAG_MARGIN:
            x = MOUSE_DRAG_AREA_X[0] + MOUSE_DROP_MARGIN
            changed = True

        #Wrap Y
        if y < MOUSE_DRAG_AREA_Y[0] + MOUSE_DRAG_MARGIN:
            y = MOUSE_DRAG_AREA_Y[1] - MOUSE_DROP_MARGIN
            changed = True
        elif y > MOUSE_DRAG_AREA_Y[1] - MOUSE_DRAG_MARGIN:
            y = MOUSE_DRAG_AREA_Y[0] + MOUSE_DROP_MARGIN
            changed = True

        if changed:
            print("Wrapping mouse")
            pyautogui.mouseUp()
            time.sleep(MOUSE_RESET_WAIT)
            self.goto_relative(x, y)
            pyautogui.mouseDown()

    def rel_to_abs(self, x, y):
        """Convert relative touch position to real screen position"""
        return self.touch_offset[0]+x/SCALE[0]*self.touch_size[0], self.touch_offset[1]+y/SCALE[1]*self.touch_size[1]
    
    def abs_to_rel(self, x, y):
        """Convert real screen position to relative touch position"""
        return int((x-self.touch_offset[0])/self.touch_size[0]*SCALE[0]+0.5), int((y-self.touch_offset[1])/self.touch_size[1]*SCALE[1]+0.5)

    def goto_relative(self, x, y):
        """Move the mouse cursor to a relative touch position"""
        #mouse.move(*self.rel_to_abs(x, y))
        pyautogui.moveTo(*self.rel_to_abs(x, y), _pause=False)

    def touchbutton(self, button):
        """Push a touch button in form ((x, y), wait)"""
        pyautogui.mouseUp()
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*button[0])
        pyautogui.mouseDown()
        time.sleep(button[1])
        self.reset_mouse()
                    
    def reset_mouse(self, e=None):
        """Reset the mouse to the center position"""
        pyautogui.mouseUp()
        time.sleep(MOUSE_RESET_WAIT)
        self.goto_relative(*TOUCH_CENTER)
        pyautogui.mouseDown()
        
mmf=MPHMousefix(multiplayer = "y" in input("Are you going into multiplayer? y/[N]: ").lower())