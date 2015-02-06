#!/usr/bin/python

import os, json, tkFont, socket, subprocess, threading, time, types, \
    signal, re, sys, shlex, argparse
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


def backtick(cmd, timeout=None, shell=False):
    if timeout is not None:
        cmd = r"{}/timeout.sh {} {}".format(HERE, timeout, cmd)
    if not shell:
        cmd = shlex.split(cmd)
    proc = subprocess.Popen(cmd, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=shell)
    stdout, stderr = proc.communicate()
    return stdout


class Player(object):
    """Player base class."""
    def __init__(self, root):
        # time interval for queue polling loops
        self._poll_sleep_s = 1 # seconds
        self._poll_sleep_ms = int(self._poll_sleep_s * 1000)
        
        # In fill_queue_selected_stream_metadata(), the metadata queue
        # (self.metadata_queue) with the currently selected stream metadata (artist,
        # title) is updated every _fill_metadata_sleep + _mplayer_poll_timeout
        # seconds usually, if get_selected_stream_metadata() uses mplayer with
        # _mplayer_poll_timeout. This is for example not the case for
        # MPDPlayerM3U, which just uses a call to "mpc current".
        self._fill_metadata_sleep = 5
        self._mplayer_poll_timeout = 5
        
        self._flag_stop_all_threads = False
        self._flag_stop_poll_stream_names = False
        self._flag_is_polling_metadata = False
        
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
        button_play.place(relx=0.18, rely=0)
        button_close.place(relx=0.5, rely=0)
        button_shutdown.place(relx=0.7, rely=0)
        scrollbar.place(relx=0.9, rely=0.2, relheight=0.7)
        listbox.place(relx=0, rely=0.2, relwidth=0.9, relheight=0.7)
        text.place(relx=0, rely=0.9)
        
        self.text = text
        self.root = root
        self.listbox = listbox
        root.protocol("WM_DELETE_WINDOW", self.callback_close)
        
        self.metadata_queue = queue.LifoQueue()

        self.selected_stream_metadata_thread = None
        self.stream_names_thread = None
        self.threads = {}
        
        self.stream_names_thread = threading.Thread(target=self.fill_stream_names)
        self.stream_names_thread.start()
        self.root.after(self._poll_sleep_ms, self.poll_stream_names)
        
        # start thread: see start_selected_stream_metadata_thread()
        self.root.after(self._poll_sleep_ms, self.poll_queue_selected_stream_metadata)
        
        self.update_threads()
        
        self.play_last()
    
    def update_threads(self):
        dbg('update_threads: start')
        self.threads['selected_stream_metadata_thread'] = self.selected_stream_metadata_thread
        self.threads['stream_names_thread'] = self.stream_names_thread
        dbg('update_threads: end')

    def wait_for_threads_to_die(self):
        for name,thread in self.threads.iteritems():
            timeout = 1
            passed = -timeout
            while (thread is not None) and thread.is_alive():
                passed += timeout
                dbg("wait_for_threads_to_die: %s" %name)
                time.sleep(timeout)
                if int(passed) == int(self._mplayer_poll_timeout*2):
                    ##raise StandardError("thread not finished: %s" %name)
                    exit("thread not finished: %s" %name)

    def start_selected_stream_metadata_thread(self):
        dbg("start_selected_stream_metadata_thread: starting")
        if (self.selected_stream_metadata_thread is not None) and \
                self.selected_stream_metadata_thread.is_alive():
            exit("selected_stream_metadata_thread is alive")
        self.selected_stream_metadata_thread = threading.Thread(target=self.fill_queue_selected_stream_metadata)
        self.selected_stream_metadata_thread.start()
        self.update_threads()

    def play_last(self):
        self.action_load_last_stream() 
        if self.selected_stream is not None:
            self.callback_play()
    
    # not called if window closed but self.selected_stream_metadata_thread still running
    def __del__(self):
        self.callback_stop()

    def callback_stop(self):
        self.action_stop()
        self._flag_stop_all_threads = True
        self._flag_is_polling_metadata = False
        self.wait_for_threads_to_die()

    def callback_play(self):
        self.action_stop()
        if self.selected_stream is None:
            msg("error: no stream")
        else:   
            self.action_dump_last_stream()
            self._flag_stop_all_threads = False
            self.action_play()
            if not self._flag_is_polling_metadata:
                self.start_selected_stream_metadata_thread()
                self._flag_is_polling_metadata = True

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
        self.callback_stop()
        self.root.destroy()
    
    def insert_metadata_txt(self, txt):
        self.text.delete(1.0, END)
        self.text.insert(END, txt)

    def fill_queue_selected_stream_metadata(self):
        while True:
            if self._flag_stop_all_threads:
                break
            txt = self.get_selected_stream_metadata()
            dbg("    fill_queue_selected_stream_metadata: txt: %s" %txt)
            self.metadata_queue.put(txt)
            time.sleep(self._fill_metadata_sleep)

    def poll_queue_selected_stream_metadata(self):
        oldtxt = ' '
        while True:
            try:
                txt = self.metadata_queue.get(block=False, timeout=1)
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
        
        for idx in range(nstreams):
            dbg("fill_stream_names: start thread for stream idx: %i" %idx)
            thread = threading.Thread(target=func_put_name, args=(idx,))
            thread.start()
            time.sleep(self._stream_name_sleep)
        
        timeout = 1
        passed = -timeout
        while True:
            passed += timeout
            if passed == int(self._mplayer_poll_timeout*5):
                dbg("fill_stream_names: while loop: break b/c count timed out")
                self._flag_stop_poll_stream_names = True
                break

            if have_all_names():
                dbg("fill_stream_names: while loop: break b/c have_all_names")
                self._flag_stop_poll_stream_names = True
                break
            else:
                dbg("fill_stream_names: while loop: wait ....")
                time.sleep(timeout)
        
        dbg("fill_stream_names: end")

    def poll_stream_names(self):
        for idx,stream in enumerate(self.streams):
            if self.streams[idx].has_key('name'):
                self.root.after_idle(self.insert_stream_name_txt, idx)
        if self._flag_stop_poll_stream_names:
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


# player application base classes

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
        txt = backtick(cmd, self._mplayer_poll_timeout*3)
        match = re.search(r'^\s*Name\s*:\s*(.*)$', txt, re.M)
        if match is None: 
            msg("match is None for stream: %s" %self.streams[idx]['url'])
            return ''
        else:    
            return match.group(1)                             


class MPDPlayer(object):
    def action_stop(self):
        os.system("mpc stop")
    
    def action_play(self):
        idx = self.stream_urls.index(self.selected_stream['url']) + 1
        dbg("MPDPlayer.action_play: idx+1: %i" %idx)
        os.system(r"mpc play %i" %idx)

    def get_selected_stream_metadata(self):
        dbg("MPDPlayer: get_selected_stream_metadata: start")
        cmd = r"mpc current"
        txt = backtick(cmd, shell=True)
        ret = txt.split(':')[-1].strip()                         
        dbg("MPDPlayer: get_selected_stream_metadata: end")
        return ret 


# actual player classes which are used in __main__

class MplayerJson(Player, Mplayer):
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
    

class MplayerM3U(Player, Mplayer):
    _fn_last_stream = pj(CONF, 'last_stream.m3u')
    _stream_name_sleep = .5
    
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


class MPDPlayerM3U(MPDPlayer, MplayerM3U):
    def __init__(self, *args, **kwds):
        self._stream_name_sleep = 0
        super(MPDPlayerM3U, self).__init__(*args, **kwds)
        self._fill_metadata_sleep = 2
     
    def load_streams(self, *args, **kwds):
        streams = super(MPDPlayerM3U, self).load_streams(*args, **kwds)
        os.system("mpc clear; mpc load streams")
        return streams

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='raspi radio')
    parser.add_argument('-f', '--format', help="playlist format [json,m3u]",
                        default='json')
    parser.add_argument('-p', '--player', help="player [mplayer,mpd]",
                        default='mplayer')
    args = parser.parse_args()

    root = Tk()
    root.geometry("320x210")
    FONTSIZE = 15
    COLUMNS = 26
    root.wm_title("raspi radio")
    if args.player == 'mplayer':
        if args.format == 'json':
            p = MplayerJson(root)
        elif args.format == 'm3u':
            p = MplayerM3U(root)
        else:
            raise StandardError("unknown playlist format '%s'" %args.format)
    elif args.player == 'mpd':
        if args.format == 'json':
            raise StandardError("player mpd + format json not implemented")
        elif args.format == 'm3u':
            p = MPDPlayerM3U(root)
        else:
            raise StandardError("unknown playlist format '%s'" %args.format)
    else:
        raise StandardError("unknown player '%s'" %args.player)
    root.mainloop()
