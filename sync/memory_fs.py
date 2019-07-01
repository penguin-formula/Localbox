# -*- coding: utf-8 -*-
import os, sys
import random, string, time
from fs.memoryfs import MemoryFS
from fs.expose import fuse


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

            if not os.path.exists(self.mount_directory):
                os.makedirs(self.mount_directory)
                fuse.mount(self.memory, self.mount_directory)
    
    
    def createfile(self, path, content, wipe=True):
        self.memory.createfile(path, wipe=wipe)
        with self.memory.open(path, "wb") as f:
            f.write(content)
        
        if not os.path.exists(self.mount_directory):
            os.makedirs(self.mount_directory)
            fuse.mount(self.memory, self.mount_directory)
        else:
            fuse.unmount(self.mount_directory)
            fuse.mount(self.memory, self.mount_directory)
        
        return self.mount_directory + path

    def destroy(self):
        time.sleep(2) #Wait 2 seconds while app open's file then destroy and unmount
        fuse.unmount(self.mount_directory)
        os.removedirs(self.mount_directory)