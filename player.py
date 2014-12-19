#!/usr/bin/python

import os, json, tkFont, socket, subprocess, threading, time
import Queue as queue
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH, \
    INSERT, Button, Scrollbar, Listbox, Tk, Text
pj = os.path.join

here = os.path.dirname(__file__)

def msg(txt):
    print "[raspi-radio] %s" %txt

def dbg(txt):
    ##print "DEBUG [raspi-radio] %s" %txt
    pass

class Player(object):
    def __init__(self, root):
        self._polltime_s = 1
        self._polltime_ms = int(self._polltime_s * 1000)
        self._stop_thread = False
        self.selected_stream = None
        
        # [{'name': 'radio1', 'url': 'http://...'},
        #  {'name': 'radio2', 'url': 'http://...'},
        #  ...
        #  ]
        self.streams = self.load_streams()
        
        self.queue = queue.LifoQueue()

        button_play = Button(root, 
                             text="Play", 
                             command=self.callback_play)
        
        button_stop = Button(root, 
                             text="Stop", 
                             command=self.callback_stop)

        button_shutdown = Button(root, 
                                 text="Shut down", 
                                 command=self.callback_shutdown)

        button_close = Button(root, 
                              text="Close", 
                              command=self.callback_close)

        text = Text(root, height=1)
        
        scrollbar = Scrollbar(root, width=30)
        font = tkFont.Font(size=15)
        listbox = Listbox(root, 
                          yscrollcommand=scrollbar.set,
                          selectmode=SINGLE,
                          font=font)
        listbox.bind("<<ListboxSelect>>", self.callback_listbox)
        for stream in self.streams:
            listbox.insert(END, stream['name'])
        scrollbar.config(command=listbox.yview)
        
        button_stop.place(relx=0, rely=0)
        button_play.place(relx=0.2, rely=0)
        button_close.place(relx=0.5, rely=0)
        button_shutdown.place(relx=0.7, rely=0)
        scrollbar.place(relx=0.9, rely=0.2, relheight=0.7)
        listbox.place(relx=0, rely=0.2, relwidth=0.9, relheight=0.7)
        text.place(relx=0, rely=0.9)
        
        self.text = text
        self.root = root
        
        # start metadata thread which fills metadata queue self.queue
        self.thread = threading.Thread(target=self.poll_current_metadata_thread_callback)
        self.thread.start()
        
        # start polling loop with recursive self.poll_current_metadata_queue()
        self.root.after(self._polltime_ms, self.poll_current_metadata_queue)
        
        root.protocol("WM_DELETE_WINDOW", self.callback_close)
        
        self.action_load_last_stream() 
        if self.selected_stream is not None:
            keys = [ss['name'] for ss in self.streams]
            idx = keys.index(self.selected_stream['name'])
            listbox.selection_set(idx)
            listbox.see(idx)
            self.callback_play()
    
    # not called if window closed but self.thread still running
    def __del__(self):
        self.action_stop()
        self._stop_thread = True

    def callback_stop(self):
        self.action_stop()

    def callback_play(self):
        self.action_stop()
        if self.selected_stream is None:
            msg("error: no stream")
        else:    
            msg("playing: %s" %self.selected_stream['name'])
            self.action_dump_last_stream()
            self.action_play()

    def callback_listbox(self, event):
        # tuple (1,) or ('1',) on raspi -> 1
        stream_idx = int(event.widget.curselection()[0])
        msg("stream_idx: %i" %stream_idx)
        self.selected_stream = self.streams[stream_idx]

    def callback_shutdown(self):
        if socket.gethostname() == 'raspi':
            os.system("sudo shutdown -h now")
        else:
            msg("shutdown works only on raspi")
    
    def callback_close(self):
        self.action_stop()
        self._stop_thread = True
        self.root.destroy()
        msg("wait for threads to terminate ...")
    
    def insert_metadata_txt(self, txt):
        self.text.delete(1.0, END)
        self.text.insert(END, txt)

    def poll_current_metadata_queue(self):
        oldtxt = ''
        dbg("poll_current_metadata_queue .... start")
        while True:
            try:
                txt = self.queue.get(block=False, timeout=1)
                dbg("    poll_current_metadata_queue .... txt: %s" %txt)
                if txt != oldtxt:
                    self.root.after_idle(self.insert_metadata_txt, txt)
                oldtxt = txt
            except queue.Empty:
                break
        self.root.after(self._polltime_ms, self.poll_current_metadata_queue)

    def poll_current_metadata_thread_callback(self):
        dbg("poll_current_metadata_thread_callback .... start")
        while True:
            if self._stop_thread:
                break
            txt = self.get_selected_stream_metadata()
            dbg("    poll_current_metadata_thread_callback .... txt: %s" %txt)
            self.queue.put(txt)
            time.sleep(self._poll_sleep)


class JsonPlayer(Player):
    _fn_last_stream = pj(here, 'last_stream.json')
    _mplayer_poll_timeout = 5
    _poll_sleep = 15

    def load_streams(self, fn=pj(here, 'streams.json')):
        assert os.path.exists(fn), "error: file %s not found" %fn 
        with open(fn) as fd:
            streams = json.load(fd)
        return streams

    def action_stop(self):
        os.system("killall mplayer")
    
    def action_play(self):
        os.system(r"mplayer -cache 300 %s &" %self.selected_stream['url'])
    
    def action_dump_last_stream(self):
        # None -> 'null'
        # dict -> dict
        with open(self._fn_last_stream, 'w') as fd:
            json.dump(self.selected_stream, fd)
    
    def action_load_last_stream(self):
        if os.path.exists(self._fn_last_stream):
            self.selected_stream = self.load_streams(fn=self._fn_last_stream)
    
    def get_selected_stream_metadata(self):
        if self.selected_stream is None:
            return ''
        else:    
            cmd = r"timeout %i mplayer --ao=null %s 2>&1 \
                | sed -nre 's/.*StreamTitle='\''(.[^;]*)'\'';*.*/\1/p' &" \
                    %(self._mplayer_poll_timeout, self.selected_stream['url'])
            return subprocess.check_output(cmd, shell=True)


if __name__ == '__main__':
    
    root = Tk()
    root.geometry("320x210")
    root.wm_title("raspi radio")
    p = JsonPlayer(root)
    root.mainloop()
