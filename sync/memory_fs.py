# -*- coding: utf-8 -*-
import os, sys
import random, string, time
from fs.memoryfs import MemoryFS
from fs.expose import fuse
from multiprocessing import Process

from six import b
NATIVE_ENCODING = sys.getfilesystemencoding()


class LocalBoxMountProcess(fuse.MountProcess):
    '''
    Class that will mount virtual folder

    '''
    def __init__(self, fs, path, fuse_opts={}, nowait=False, **kwds):
        # super(LocalBoxMountProcess, self).__init__(fs, path, fuse_opts, nowait, **kwds)
        self.path = path

        (r, w) = os.pipe()

        data = (fs, path, fuse_opts, r, w)
        p = Process(target=fuse.MountProcess._do_mount_wait, args=(data,))
        p.start()

        os.close(w)
        byte = os.read(r, 1)
        if byte != b("S"):
            err_text = os.read(r, 20)
            self.terminate()
            if hasattr(err_text, 'decode'):
                err_text = err_text.decode(NATIVE_ENCODING)
            raise RuntimeError("FUSE error: " + err_text)


def mount(fs, path, foreground=False, ready_callback=None, unmount_callback=None, **kwds):
    """Mount the given FS at the given path, using FUSE.

    By default, this function spawns a new background process to manage the
    FUSE event loop.
    """
    path = os.path.expanduser(path)
    mp = LocalBoxMountProcess(fs, path, kwds)
    if ready_callback:
        ready_callback()
    if unmount_callback:
        orig_unmount = mp.unmount

        def new_unmount():
            orig_unmount()
            unmount_callback()
        mp.unmount = new_unmount
    return mp


class LocalBoxMemoryFS():
    '''
    #
    # Class that handles in memory file system for localbox
    #
    '''

    def __init__(self):
        self.memory = MemoryFS()

        ## WINDOWS
        if sys.platform == 'win32': 
            from fs.expose import dokan
            letter = random.choice(string.letters) + ":\\"
            
            while os.path.exists(letter):
                letter = random.choice(string.letters) + ":\\"

            self.mount_directory = letter
            if not os.path.exists(letter):
                dokan.mount(self.memory, letter)

        ## LINUX
        else:
            self.mount_directory = os.path.join(os.path.expanduser('~')) +'/mtdecoded/'


    def createfile(self, path, content, wipe=True):
        self.memory.createfile(path, wipe=wipe)
        with self.memory.open(path, "wb") as f:
            f.write(content)
        
        if not os.path.exists(self.mount_directory):
            os.makedirs(self.mount_directory)
            mount(self.memory, self.mount_directory)
        # else:
        #     fuse.unmount(self.mount_directory)
        #     mount(self.memory, self.mount_directory)
        # If system is mounted with video it can't be unmounted, find a wait o update mounted resources TODO

        return self.mount_directory + path

    def destroy(self):
        time.sleep(2)
        try:
            fuse.unmount(self.mount_directory)
            os.removedirs(self.mount_directory)
        except OSError: #Mounted in use, try again
            self.destroy()