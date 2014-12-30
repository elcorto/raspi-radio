"""
Experimental shell call methods with timeout based on threading, inspired by
several posts on stackoverflow.com. We played with that b/c we did not want to
install Python 3 (subprocess package has proper timeout support) or
https://pypi.python.org/pypi/subprocess32.

Currently, an mplayer command called with ``backtick`` inside another thread

>>> def target(cmd):
...     txt = backtick(cmd, 5)
...     self.foo = self.parse_txt_get_foo(txt)
>>> cmd = "mplayer --quiet http://cool.stream.ogg"
>>> thread = threading.Thread(target=target, args=(cmd,))
>>> thread.start()

causes the bash prompt to be messed up, probably b/c of the way that mplayer
prints to stdout and the way that subprocess captures that. But "mplayer
--quiet" doesn't help. Maybe we need to further reduce the output even more,
but we need some output since we use that to obtain stream metadata :)

That's why we use a simple hack in player.py like "./timeout.sh <time>
mplayer ...". Here, we don't start a thread, which runs subprocess.Popen() and
gets killed. Instead, we run Popen directly and kill inside ``cmd`` with
``timeout.sh``.
"""

class ShellCommand(object):
    """Run shell command in a thread, possibly with timeout."""

    def __init__(self, cmd, verbose=False):
        self.cmd = cmd
        self.stdout = None
        self.stderr = None
        self.verbose = verbose

    def run(self, timeout=None):
        thread = threading.Thread(target=self.target)
        dbg("ShellCommand: start thread for: '%s'" %self.cmd)
        thread.start()
        if timeout is not None:
            thread.join(timeout)
            if thread.is_alive():
                dbg("ShellCommand: proc terminate")
                self.proc.terminate()
                dbg("ShellCommand: os terminate")
                os.killpg(self.proc.pid, signal.SIGTERM)
                dbg("ShellCommand: join")
                thread.join()
            time.sleep(1)    
            assert not thread.is_alive(), "ShellCommand: error: thread still alive"    
            dbg("ShellCommand: retcode: %i" %self.proc.returncode)
        else:  
            if self.verbose:
                for txt in [self.stdout, self.stderr]:
                    if txt is not None:
                        print txt

    def target(self):
        self.proc = subprocess.Popen(shlex.split(self.cmd), stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     shell=False, preexec_fn=os.setsid,
                                     bufsize=0,
                                     universal_newlines=True,close_fds=True) 
        self.stdout, self.stderr = self.proc.communicate()


def backtick(cmd, timeout):
    sc = ShellCommand(cmd)
    sc.run(timeout)
    return sc.stdout

