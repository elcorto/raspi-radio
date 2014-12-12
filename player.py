#!/usr/bin/python

import Tkinter, os
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH

##top.attributes("-fullscreen", True)
##top.attributes("-zoomed", True) # show window elements (close button etc)

##os.environ["SDL_FBDEV"] = "/dev/fb1"
##os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
##os.environ["SDL_MOUSEDRV"] = "TSLIB"

top = Tkinter.Tk()

class Player(object):

    def __init__(self, top):
        
        self.selected_stream = None
        self.streams = \
            [('dradio', 'http://dradio_mp3_dlf_s.akacast.akamaistream.net/7/251/142684/v1/gnl.akacast.akamaistream.net/dradio_mp3_dlf_s'),
             ('soma 80s', 'http://ice.somafm.com/u80s-64.aac'),
             ('mdr info', 'http://c22033-ls.i.core.cdn.streamfarm.net/QpZptC4ta9922033/22033mdr/live/app2128740352/w2128904192/live_de_128.mp3'),
             ]

        button_play = Tkinter.Button(top, 
                                     text="Play", 
                                     command=self.callback_play)
        
        button_stop = Tkinter.Button(top, 
                                     text="Stop", 
                                     command=self.callback_stop)

        scrollbar = Tkinter.Scrollbar(top, width=30)
        listbox = Tkinter.Listbox(top, 
                                  yscrollcommand=scrollbar.set,
                                  selectmode=SINGLE)
        listbox.bind("<<ListboxSelect>>", self.callback_listbox)
        
        for name,url in self.streams:
            listbox.insert(END, name)
        
        button_play.pack(side=LEFT)
        button_stop.pack(side=LEFT)
        scrollbar.pack(side=RIGHT, fill=Y)
        scrollbar.config(command=listbox.yview)
        listbox.pack(side=LEFT)
    
    def action_stop(self):
        os.system("killall mplayer")

    def callback_stop(self):
        self.action_stop()

    def callback_play(self):
        self.action_stop()
        if self.selected_stream is None:
            print "error: no stream"
        else:    
            print "playing: %s" %self.selected_stream[0]
            os.system(r"mplayer %s &" %self.selected_stream[1])
        
    def callback_listbox(self, event):
        selection = event.widget.curselection()
        print "selection: ", selection
        self.selected_stream = self.streams[int(selection[0])]
    
    def __del__(self):
        self.action_stop()


p = Player(top)

top.mainloop()
