#!/usr/bin/python

import os, json, tkFont, socket, subprocess, threading, time, types, \
    signal, re, sys, shlex
import Queue as queue
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH, \
    INSERT, Button, Scrollbar, Listbox, Tk, Text
pj = os.path.join

HERE = os.path.dirname(__file__)
CONF = pj(os.environ['HOME'], '.raspi-radio')

def msg(txt):
    print "[raspi-radio] %s" %txt


def dbg(txt):
    print "DEBUG [raspi-radio] %s" %txt
    ##pass

def trim(line):
    ret = line[:(COLUMNS-3)]
    if len(line.strip()) > COLUMNS:
        return  ret + '...'
    else:
        return ret

def exit(msg):
    raise StandardError(msg)
    sys.exit(1)


def backtick(cmd, timeout):
    cmd = r"{}/timeout.sh {} {}".format(HERE, timeout, cmd)
    proc = subprocess.Popen(shlex.split(cmd), 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    stdout, stderr = proc.communicate()
    return stdout


class Player(object):
    def __init__(self, root):
        # time interval for queue polling loops
        self._poll_sleep_s = 1 # seconds
        self._poll_sleep_ms = int(self._poll_sleep_s * 1000)
        
        # poll for new stream metadata after that many seconds,
        # _mplayer_poll_timeout should be smaller, such as 5 seconds or so
        self._fill_metadata_sleep = 15
        
        # let mplayer run this many seconds to obtain stream name or metadata
        self._mplayer_poll_timeout = 15

        self._stop_thread = False
        self._have_all_stream_names = False
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
        font = tkFont.Font(size=FONTSIZE)
        listbox = Listbox(root, 
                          yscrollcommand=scrollbar.set,
                          selectmode=SINGLE,
                          font=font)
        listbox.bind("<<ListboxSelect>>", self.callback_listbox)
        for idx,url in enumerate(self.stream_urls):
            listbox.insert(idx, trim(url))
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
        
       
        self.queue = queue.LifoQueue()
        
        self.selected_stream_metadata_thread = threading.Thread(target=self.fill_queue_selected_stream_metadata)
        self.selected_stream_metadata_thread.start()
        self.root.after(self._poll_sleep_ms, self.poll_queue_selected_stream_metadata)
        
        self.stream_names_thread = threading.Thread(target=self.fill_stream_names)
        self.stream_names_thread.start()
        self.root.after(self._poll_sleep_ms, self.poll_stream_names)
        
        self.play_last()
    

    def play_last(self):
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

    def fill_queue_selected_stream_metadata(self):
        while True:
            if self._stop_thread:
                break
            txt = self.get_selected_stream_metadata()
            dbg("    fill_queue_selected_stream_metadata: txt: %s" %txt)
            self.queue.put(txt)
            time.sleep(self._fill_metadata_sleep)

    def poll_queue_selected_stream_metadata(self):
        oldtxt = ''
        while True:
            try:
                txt = self.queue.get(block=False, timeout=1)
                dbg("    poll_queue_selected_stream_metadata: txt: %s" %txt)
                if txt != oldtxt:
                    self.root.after_idle(self.insert_metadata_txt, txt)
                oldtxt = txt
            except queue.Empty:
                break
        self.root.after(self._poll_sleep_ms, self.poll_queue_selected_stream_metadata)

    def highlight_selected_stream(self):
        if self.selected_stream is not None:
            idx = self.stream_urls.index(self.selected_stream['url'])
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
    
    def fill_stream_names(self):
        dbg("fill_stream_names: start")
        nstreams = len(self.stream_urls)
        
        def func_put_name(idx):
            dbg("func_put_name: idx: %i" %idx)
            stream = self.streams[idx]
            if not stream.has_key('name'):
                stream['name'] = self.get_stream_name(idx)
        
        def have_all_names():
            names = [stream['name'] for stream in self.streams if \
                stream.has_key('name')]
            dbg("fill_stream_names: check: names: %s" %str(names))  
            if len(names) == nstreams:
                return True
            else:
                return False
        
        for idx in range(len(self.stream_urls)):
            dbg("fill_stream_names: start thread for stream idx: %i" %idx)
            thread = threading.Thread(target=func_put_name, args=(idx,))
            thread.start()
            time.sleep(self._stream_name_sleep)
        
        cnt = -1
        while True:
            cnt += 1
            if cnt == int(self._mplayer_poll_timeout*5):
                dbg("fill_stream_names: while loop: break b/c count timed out")
                break

            if not have_all_names():
                dbg("fill_stream_names: while loop: wait ....")
                time.sleep(1)
            else:
                dbg("fill_stream_names: while loop: break b/c have_all_names")
                self._have_all_stream_names = True
                break
        
        dbg("fill_stream_names: end")

    def poll_stream_names(self):
        for idx,stream in enumerate(self.streams):
            if self.streams[idx].has_key('name'):
                self.root.after_idle(self.insert_stream_name_txt, idx)
        if self._have_all_stream_names:
            dbg("poll_stream_names: highlight_selected_stream")
            self.root.after_idle(self.highlight_selected_stream)
        else:    
            self.root.after(self._poll_sleep_ms, self.poll_stream_names)
    
    def insert_stream_name_txt(self, idx):
        txt = self.streams[idx]['name']
        if txt != '':
            dbg("insert_stream_name_txt: insert loop: idx: %i" %idx)
            self.listbox.delete(idx)
            self.listbox.insert(idx, trim(txt))

    def action_load_last_stream(self):
        if os.path.exists(self._fn_last_stream):
            self.selected_stream = self.load_streams(fn=self._fn_last_stream)[0]


class Mplayer(object):
    def action_stop(self):
        os.system("killall mplayer")
    
    def action_play(self):
        os.system(r"mplayer --quiet --cache=300 %s &" %self.selected_stream['url'])

    def get_selected_stream_metadata(self):
        if self.selected_stream is None:
            return ''
        else:    
            cmd = r"mplayer --quiet --vo=null --ao=null %s" %self.selected_stream['url']
            txt = backtick(cmd, self._mplayer_poll_timeout)
            match = re.search(r".*StreamTitle='(.*?)';*.*", txt, re.M)
            if match is None:
                msg("match is None for selected stream: %s" %self.selected_stream['url'])
                return ''
            else:    
                return match.group(1)                             
    
    def get_stream_name(self, idx):
        dbg("get_stream_name: url: %s" %self.streams[idx]['url'])
        cmd = r"mplayer --quiet --vo=null --ao=null %s" %self.streams[idx]['url']
        txt = backtick(cmd, self._mplayer_poll_timeout)
        match = re.search(r'^\s*Name\s*:\s*(.*)$', txt, re.M)
        if match is None: 
            msg("match is None for stream: %s" %self.streams[idx]['url'])
            return ''
        else:    
            return match.group(1)                             

 
class JsonPlayer(Player, Mplayer):
    _fn_last_stream = pj(CONF, 'last_stream.json')
    _stream_name_sleep = 0

    @staticmethod
    def _tolist(x):
        if isinstance(x, types.DictType):
            return [x]
        else:
            return x

    def load_streams(self, fn=pj(CONF, 'streams.json')):
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
    _fn_last_stream = pj(CONF, 'last_stream.m3u')
    _stream_name_sleep = 1

    def load_streams(self, fn=pj(CONF, 'streams.m3u')):
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
    
if __name__ == '__main__':
    
    root = Tk()
    root.geometry("320x210")
    FONTSIZE = 15
    COLUMNS = 26
    root.wm_title("raspi radio")
    p = JsonPlayer(root)
##    p = M3UPlayer(root)
    root.mainloop()
