#!/usr/bin/python

import os, json, tkFont, socket, subprocess, threading, time, types
import Queue as queue
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH, \
    INSERT, Button, Scrollbar, Listbox, Tk, Text
pj = os.path.join

here = os.path.dirname(__file__)

def msg(txt):
    print "[raspi-radio] %s" %txt

def dbg(txt):
    print "DEBUG [raspi-radio] %s" %txt
    ##pass

class Player(object):
    def __init__(self, root):
        self._polltime_s = 1
        self._polltime_ms = int(self._polltime_s * 1000)
        self._stop_thread = False
        self.selected_stream = None
        
        # json player:
        # [{'name': 'radio1', 'url': 'http://radio1...'},
        #  {'name': 'radio2', 'url': 'http://radio2...'},
        #  ...
        #  ]
        # m3u player:
        # [{'url': 'http://radio1...'},
        #  {'url': 'http://radio2...'},
        #  ...
        #  ]
        self.streams = self.load_streams()
        self.stream_urls = [stream['url'] for stream in self.streams]

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
        for idx,url in enumerate(self.stream_urls):
            listbox.insert(idx, url)
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
        self.listbox = listbox
        root.protocol("WM_DELETE_WINDOW", self.callback_close)
       
        # thread which starts nstreams sub-threads for getting the stream name
        self.stream_names_thread = threading.Thread(target=self.set_stream_names)
        self.stream_names_thread.start()

        # start metadata thread which fills metadata queue self.queue
        self.selected_stream_metadata_thread = threading.Thread(target=self.selected_stream_metadata_into_queue)
        self.selected_stream_metadata_thread.start()

        # start polling loop with recursive self.poll_selected_stream_metadata_queue()
        self.root.after(self._polltime_ms, self.poll_selected_stream_metadata_queue)
        
        self.action_load_last_stream() 
        if self.selected_stream is not None:
            self.callback_play()
    
    # not called if window closed but self.selected_stream_metadata_thread still running
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

    def poll_selected_stream_metadata_queue(self):
        oldtxt = ''
        dbg("poll_selected_stream_metadata_queue .... start")
        while True:
            try:
                txt = self.queue.get(block=False, timeout=1)
                dbg("    poll_selected_stream_metadata_queue .... txt: %s" %txt)
                if txt != oldtxt:
                    self.root.after_idle(self.insert_metadata_txt, txt)
                oldtxt = txt
            except queue.Empty:
                break
        self.root.after(self._polltime_ms, self.poll_selected_stream_metadata_queue)

    def selected_stream_metadata_into_queue(self):
        dbg("selected_stream_metadata_into_queue .... start")
        while True:
            if self._stop_thread:
                break
            txt = self.get_selected_stream_metadata()
            dbg("    selected_stream_metadata_into_queue .... txt: %s" %txt)
            self.queue.put(txt)
            time.sleep(self._poll_sleep)

    def highlight_selected_stream(self):
        if self.selected_stream is not None:
            idx = self.stream_urls.index(self.selected_stream['url'])
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
    
    def set_stream_names(self):
        nstreams = len(self.stream_urls)
        def func_get(idx):
            stream = self.streams[idx]
            if not stream.has_key('name'):
                stream['name'] = self.get_stream_name(idx)
        
        def have_all_names():
            names = [stream['name'] for stream in self.streams if \
                stream.has_key('name')]
            dbg("check: names: %s" %str(names))  
            if len(names) == nstreams:
                return True
            else:
                return False
        
        for idx in range(len(self.stream_urls)):
            dbg("start thread for: %i" %idx)
            thread = threading.Thread(target=func_get, args=(idx,))
            thread.start()
        
        while True:
            if not have_all_names():
                dbg("set_stream_names: while loop: wait ....")
                time.sleep(1)
            else:
                dbg("set_stream_names: while loop: break")
                break
        
        # update listbox after we have all stream names
        for idx,stream in enumerate(self.streams):
            dbg("set_stream_names: insert loop: idx: %i" %idx)
            name = self.streams[idx]['name']
            if name != '':
                self.listbox.delete(idx)
                self.listbox.insert(idx, name)
        
        self.highlight_selected_stream()

    def action_load_last_stream(self):
        if os.path.exists(self._fn_last_stream):
            self.selected_stream = self.load_streams(fn=self._fn_last_stream)[0]


class Mplayer(object):
    def action_stop(self):
        os.system("killall mplayer")
    
    def action_play(self):
        os.system(r"mplayer -cache 300 %s &" %self.selected_stream['url'])
    
    def get_selected_stream_metadata(self):
        if self.selected_stream is None:
            return ''
        else:    
            cmd = r"timeout %i mplayer --ao=null %s 2>&1 \
                | sed -nre 's/.*StreamTitle='\''(.[^;]*)'\'';*.*/\1/p' &" \
                    %(self._mplayer_poll_timeout, self.selected_stream['url'])
            return subprocess.check_output(cmd, shell=True)
    
 
class JsonPlayer(Player, Mplayer):
    _fn_last_stream = pj(here, 'last_stream.json')
    _mplayer_poll_timeout = 5
    _poll_sleep = 15
    
    @staticmethod
    def _tolist(x):
        if isinstance(x, types.DictType):
            return [x]
        else:
            return x

    def load_streams(self, fn=pj(here, 'streams.json')):
        assert os.path.exists(fn), "error: file %s not found" %fn 
        with open(fn) as fd:
            streams = self._tolist(json.load(fd))
        return streams

    def action_dump_last_stream(self):
        # None -> 'null'
        # dict -> dict
        with open(self._fn_last_stream, 'w') as fd:
            json.dump(self.selected_stream, fd)
    
    def get_stream_name(self, idx):
        return self.streams[idx]['name']
    

class M3UPlayer(Player, Mplayer):
    _fn_last_stream = pj(here, 'last_stream.m3u')
    _mplayer_poll_timeout = 5
    _poll_sleep = 15

    def load_streams(self, fn=pj(here, 'streams.m3u')):
        assert os.path.exists(fn), "error: file %s not found" %fn 
        with open(fn) as fd:
            streams = [{'url': x} for x in [z.strip() for z in \
                       fd.readlines()] if not x.startswith('#')]
        return streams

    def action_dump_last_stream(self):
        # None -> 'null'
        # dict -> dict
        with open(self._fn_last_stream, 'w') as fd:
            fd.write(self.selected_stream['url'] + '\n')
    
    def get_stream_name(self, idx):
        dbg("get_stream_name: url: %s" %self.streams[idx]['url'])
        cmd = r"timeout %i mplayer --ao=null %s 2>&1 \
            | sed -nre 's/^Name\s*:\s*(.*)$/\1/p' &" \
                %(self._mplayer_poll_timeout, self.streams[idx]['url'])
        return subprocess.check_output(cmd, shell=True).strip()


if __name__ == '__main__':
    
    root = Tk()
    root.geometry("320x210")
    root.wm_title("raspi radio")
##    p = JsonPlayer(root)
    p = M3UPlayer(root)
    root.mainloop()
