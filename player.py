#!/usr/bin/python

import Tkinter, os, json
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH

##top.attributes("-fullscreen", True)
##top.attributes("-zoomed", True) # show window elements (close button etc)

##os.environ["SDL_FBDEV"] = "/dev/fb1"
##os.environ["SDL_MOUSEDEV"] = "/dev/input/touchscreen"
##os.environ["SDL_MOUSEDRV"] = "TSLIB"

top = Tkinter.Tk()
here = os.path.dirname(__file__)

class Player(object):
    def __init__(self, top):
        self.selected_stream = None
        fn = 'streams.json'
        assert os.path.exists(fn), "error: file %s not found" %fn 
        with open(fn) as fd:
            self.streams = json.load(fd)
        # {'radio1': {'url': http:/foo/bar}} ->
        # {'radio1': {'url': http:/foo/bar}, 'name': 'radio1'}
        for k,dct in self.streams.iteritems():
            dct['name'] = k
        print self.streams    

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
        
        for stream_name in self.streams.iterkeys():
            listbox.insert(END, stream_name)
        
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
            print "playing: %s" %self.selected_stream['name']
            os.system(r"mplayer %s &" %self.selected_stream['url'])
        
    def callback_listbox(self, event):
        # tuple (1,) or ('1',) on raspi -> 1
        stream_idx = int(event.widget.curselection()[0])
        print "stream_idx: ", stream_idx
        key = self.streams.keys()[stream_idx]
        self.selected_stream = self.streams[key]
    
    def __del__(self):
        self.action_stop()


p = Player(top)

top.mainloop()
