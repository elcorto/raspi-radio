#!/usr/bin/python

import os, json, tkFont, socket
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH, \
    Button, Scrollbar, Listbox, Tk, S
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
    
        button_play = Button(top, 
                             text="Play", 
                             command=self.callback_play)
        
        button_stop = Button(top, 
                             text="Stop", 
                             command=self.callback_stop)

        button_shutdown = Button(top, 
                                 text="Shut down", 
                                 command=self.callback_shutdown)

        scrollbar = Scrollbar(top, width=30)
        font = tkFont.Font(size=15)
        listbox = Listbox(top, 
                          yscrollcommand=scrollbar.set,
                          selectmode=SINGLE,
                          font=font)
        listbox.bind("<<ListboxSelect>>", self.callback_listbox)
        
        for stream in self.streams:
            listbox.insert(END, stream['name'])
        
        button_play.place(relx=0, rely=0)
        button_stop.place(relx=0.2, rely=0)
        button_shutdown.place(relx=0.4, rely=0)
        scrollbar.place(relx=0.9, rely=0.2, relheight=0.8)
        scrollbar.config(command=listbox.yview)
        listbox.place(relx=0, rely=0.2, relwidth=0.9, relheight=0.8)
        
        self.action_load_current_stream() 
        if self.selected_stream is not None:
            keys = [ss['name'] for ss in self.streams]
            idx = keys.index(self.selected_stream['name'])
            listbox.selection_set(idx)
            listbox.see(idx)
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

    def callback_shutdown(self):
        if socket.gethostname() == 'raspi':
            os.system("sudo halt")
        else:
            print "shutdown works only on raspi"
    

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
    
    top = Tk()
    top.geometry("320x210")
    top.wm_title("raspi radio")
    p = JsonPlayer(top)
    top.mainloop()
