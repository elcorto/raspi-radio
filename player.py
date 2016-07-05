#!/usr/bin/python

import os, json, tkFont, socket, subprocess, threading, time, types, \
    re, sys, shlex, argparse
import Queue as queue
from Tkinter import TOP, BOTTOM, LEFT, RIGHT, SINGLE, END, X, Y, BOTH, \
    INSERT, Button, Scrollbar, Listbox, Tk, Text
pj = os.path.join

HERE = os.path.dirname(__file__)
CONF = pj(os.environ['HOME'], '.raspi-radio')
VERBOSE = False

def msg(txt):
    print "[raspi-radio] %s" %txt


def dbg(txt):
    if VERBOSE:
        print "DEBUG [raspi-radio] %s" %txt
    else:
        pass

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
        
        # In fill_queue_playing_stream_metadata(), the metadata queue
        # (self.metadata_queue) with the currently selected stream metadata (artist,
        # title) is updated every _fill_metadata_sleep seconds.
        self._fill_metadata_sleep = 2
        
        # timeout for all polling commands and threads
        self._poll_timeout = 5
        
        self._flag_stop_all_threads = False
        self._flag_is_polling_metadata = False
        
        self.selected_stream = None

        # json player:
        # [{'name': 'radio1', 'url': 'http://radio1...'},
        #  {'name': 'radio2', 'url': 'http://radio2...'},
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
        listbox.bind("<<ListboxSelect>>", self.callback_stream_selected)
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

        self.playing_stream_metadata_thread = None
        self.threads = {}
        
        # start thread: see start_playing_stream_metadata_thread()
        self.root.after(self._poll_sleep_ms, self.poll_queue_playing_stream_metadata)
        
        self.update_threads()
        
        self.display_stream_names()
        self.play_last()
    
    def update_threads(self):
        dbg('update_threads: start')
        self.threads['playing_stream_metadata_thread'] = self.playing_stream_metadata_thread
        dbg('update_threads: end')

    def wait_for_threads_to_die(self):
        for name,thread in self.threads.iteritems():
            timeout = 1
            passed = -timeout
            while (thread is not None) and thread.is_alive():
                passed += timeout
                dbg("wait_for_threads_to_die: %s" %name)
                time.sleep(timeout)
                if int(passed) == int(self._poll_timeout*2):
                    exit("thread not finished: %s" %name)

    def start_playing_stream_metadata_thread(self):
        dbg("start_playing_stream_metadata_thread: starting")
        if (self.playing_stream_metadata_thread is not None) and \
                self.playing_stream_metadata_thread.is_alive():
            exit("playing_stream_metadata_thread is alive")
        self.playing_stream_metadata_thread = threading.Thread(target=self.fill_queue_playing_stream_metadata)
        self.playing_stream_metadata_thread.start()
        self.update_threads()

    def play_last(self):
        self.action_load_last_stream() 
        if self.selected_stream is not None:
            self.callback_play()
    
    # not called if window closed but self.playing_stream_metadata_thread still running
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
                self.start_playing_stream_metadata_thread()
                self._flag_is_polling_metadata = True

    def callback_stream_selected(self, event):
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
    
    def fill_queue_playing_stream_metadata(self):
        while True:
            if self._flag_stop_all_threads:
                break
            txt = self.get_playing_stream_metadata()
            dbg("    fill_queue_playing_stream_metadata: txt: %s" %txt)
            self.metadata_queue.put(txt)
            time.sleep(self._fill_metadata_sleep)

    def poll_queue_playing_stream_metadata(self):
        def _fill_txt_field(txt):
            self.text.delete(1.0, END)
            self.text.insert(END, txt)
        oldtxt = ' '
        while True:
            try:
                txt = self.metadata_queue.get(block=False, timeout=1)
                dbg("    poll_queue_playing_stream_metadata: txt: %s" %txt)
                if txt != oldtxt:
                    self.root.after_idle(_fill_txt_field, txt)
                oldtxt = txt
            except queue.Empty:
                break
        self.root.after(self._poll_sleep_ms, self.poll_queue_playing_stream_metadata)

    def highlight_selected_stream(self):
        if self.selected_stream is not None:
            idx = self.stream_urls.index(self.selected_stream['url'])
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
    
    def display_stream_names(self):
        def _insert_stream_name_txt(idx):
            txt = self.streams[idx]['name']
            if txt != '':
                dbg("insert_stream_name_txt: insert loop: idx: %i" %idx)
                self.listbox.delete(idx)
                self.listbox.insert(idx, trim(txt))
        for idx,stream in enumerate(self.streams):
            if self.streams[idx].has_key('name'):
                self.root.after_idle(_insert_stream_name_txt, idx)
        self.root.after_idle(self.highlight_selected_stream)

    def action_load_last_stream(self):
        if os.path.exists(self._fn_last_stream):
            self.selected_stream = self.load_streams(fn=self._fn_last_stream)[0]


# player application base classes

class Mplayer(object):
    _fn_mplayer_stdout = pj(CONF, 'mplayer_stdout')
    old_mtime = -0.0
    old_meta = ''

    def get_mtime(self):
        return os.stat(self._fn_mplayer_stdout).st_mtime

    def action_stop(self):
        os.system("killall -q mplayer")
    
    def action_play(self):
        cmd = r"rm -f {out}; mplayer --quiet --cache=400 {url}" 
        if VERBOSE:
            cmd += " 2>&1 | tee -a {out} &"
        else:
            cmd += " > {out} 2>&1 & "
        cmd = cmd.format(out=self._fn_mplayer_stdout,
                         url=self.selected_stream['url'])
        dbg("mplayer cmd: %s" %cmd)
        os.system(cmd)
                       
    def get_playing_stream_metadata(self):
        if not os.path.exists(self._fn_mplayer_stdout):
            dbg("%s not found, no stream metadata" %self._fn_mplayer_stdout)
            return ''
        else:
            # Checking for the last modification time makes sense if we use
            # "mplayer --quiet ...". Then, it writes new stdout only when the
            # stream changes the track and prints a new line "StreamTitle=...".
            # W/o --quiet, mplayer is rather chatty and prints some stream
            # progess info.
            mtime = self.get_mtime()
            dbg("old mtime: %s, mtime: %s" %(self.old_mtime, mtime))
            if mtime > self.old_mtime:   
                dbg("new mtime")
                with open(self._fn_mplayer_stdout) as fd:
                    lst = re.findall(r".*StreamTitle='(.*?)';*.*", fd.read(), re.M)
                    if lst == []:
                        dbg("no stream metadata in %s" %self._fn_mplayer_stdout)
                        return ''
                    else:    
                        dbg("stream info: %s" %lst[-1])
                        self.old_mtime = self.get_mtime()
                        self.old_meta = lst[-1]
                        return self.old_meta
            else:
                return self.old_meta
    

class MplayerJson(Player, Mplayer):
    _fn_last_stream = pj(CONF, 'last_stream.json')

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
            for idx,stream in enumerate(streams):
                if not stream.has_key('name'):
                    stream['name'] = self.get_stream_name(idx)
        return streams

    def action_dump_last_stream(self):
        # None -> 'null'
        # dict -> dict
        with open(self._fn_last_stream, 'w') as fd:
            json.dump(self.selected_stream, fd)
    
    def get_stream_name(self, idx):
        return self.streams[idx]['name']
    

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='raspi radio')
    parser.add_argument('-v', '--verbose', help="verbose debug output",
                        action='store_true', default=False)
    args = parser.parse_args()

    root = Tk()
    root.geometry("320x210")
    FONTSIZE = 15
    COLUMNS = 26
    root.wm_title("raspi radio")
    if args.verbose:
        VERBOSE = True
    p = MplayerJson(root)
    root.mainloop()
