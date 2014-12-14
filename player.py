#!/usr/bin/python

import Tkinter, os, json, tkFont
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH
pj = os.path.join

here = os.path.dirname(__file__)

class Player(object):
    def __init__(self, top):
        self.selected_stream = None
        # [{'name': 'radio1', 'url': 'http://...'},
        #  {'name': 'radio2', 'url': 'http://...'},
        #  ...
        #  ]
        self.streams = self.load_streams()
    
        button_play = Tkinter.Button(top, 
                                     text="Play", 
                                     command=self.callback_play)
        
        button_stop = Tkinter.Button(top, 
                                     text="Stop", 
                                     command=self.callback_stop)

        scrollbar = Tkinter.Scrollbar(top, width=30)
        font = tkFont.Font (size=15)
        listbox = Tkinter.Listbox(top, 
                                  yscrollcommand=scrollbar.set,
                                  selectmode=SINGLE,
                                  font=font)
        listbox.bind("<<ListboxSelect>>", self.callback_listbox)
        
        for stream in self.streams:
            listbox.insert(END, stream['name'])
        
        button_play.place(relx=0, rely=0.1)
        button_stop.place(relx=0, rely=0.3)
        scrollbar.place(relx=0.9, relheight=1)
        scrollbar.config(command=listbox.yview)
        listbox.place(relx=0.2, relwidth=0.7, relheight=1)
        
        self.action_load_current_stream() 
        if self.selected_stream is not None:
            self.action_play()

    def __del__(self):
        self.action_stop()

    def callback_stop(self):
        self.action_stop()

    def callback_play(self):
        self.action_stop()
        if self.selected_stream is None:
            print "error: no stream"
        else:    
            print "playing: %s" %self.selected_stream['name']
            self.action_dump_current_stream()
            self.action_play()
        
    def callback_listbox(self, event):
        # tuple (1,) or ('1',) on raspi -> 1
        stream_idx = int(event.widget.curselection()[0])
        print "stream_idx: ", stream_idx
        self.selected_stream = self.streams[stream_idx]


class JsonPlayer(Player):
    _fn_last_stream = pj(here, 'last_stream.json')

    def load_streams(self, fn=pj(here, 'streams.json')):
        assert os.path.exists(fn), "error: file %s not found" %fn 
        with open(fn) as fd:
            streams = json.load(fd)
        return streams

    def action_stop(self):
        os.system("killall mplayer")
    
    def action_play(self):
        os.system(r"mplayer %s &" %self.selected_stream['url'])
    
    def action_dump_current_stream(self):
        # None -> 'null'
        # dict -> dict
        with open(self._fn_last_stream, 'w') as fd:
            json.dump(self.selected_stream, fd)
    
    def action_load_current_stream(self):
        if os.path.exists(self._fn_last_stream):
            self.selected_stream = self.load_streams(fn=self._fn_last_stream)

if __name__ == '__main__':
    
    top = Tkinter.Tk()
    top.geometry("320x210")
    top.wm_title("raspi radio")
    p = JsonPlayer(top)
    top.mainloop()
