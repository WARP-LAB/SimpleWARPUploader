#
# Sublime 2 plugin for quick sync with destination over SSH using Unison and SSH over rsync
#
# @copyleft (cl) 2013 WARP
# @version 0.0.1
# @licence GPL
# @link http://www.warp.lv/
#

import sublime, sublime_plugin
import subprocess
import threading
import re
import sys
import glob
import os
import json
# from pprint import pprint

# ###################################
# Unison part

def loadUnisonSettings(settingpath):
    with open(settingpath) as data_file:    
        data = json.load(data_file)
    return data

def runUnison(cmd):
    #print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while (True):
        retcode = p.poll()
        line    = p.stdout.readline()
        yield line.decode('utf-8')
        if (retcode is not None):
            break

  
class WarpThreadedUnison(threading.Thread):
    def __init__(self, _settings, _projFolder):
        self.settings    = _settings
        self.projFolder  = _projFolder
        threading.Thread.__init__(self)

    def run(self):
        ignoreStrComp = "-ignore \"Name {"

        for ignore in self.settings["warpunison"][0]["ignores"]:
            ignoreStrComp+=str(ignore)+','

        ignoreStrComp+='._.DS_Store' #default in
        ignoreStrComp += "}\" "

        unisonMode = "-batch " if (int(self.settings["warpunison"][0]["opts"][0]["batch"]) == 1) else "-auto "

        remoteHost = str(self.settings["warpunison"][0]["connection"][0]["host"])
        remotePort = str(self.settings["warpunison"][0]["connection"][0]["port"])
        remoteUser = str(self.settings["warpunison"][0]["connection"][0]["username"])
        remotePath = str(self.settings["warpunison"][0]["connection"][0]["remotepath"])

    #cmd = 'rsync --progress -vv -az --update ' + deleteIfNotLocal + excludeStrComp + deleteExcluded + self.projFolder + '/ ' + '-e \'ssh -p ' + remotePort + '\' ' + remoteUser + '@' + remoteHost + ':' + remotePath
        
        cmd = 'unison -ui text ' + unisonMode + ignoreStrComp + self.projFolder + ' ' +  'ssh://'+ remoteUser + '@' + remoteHost + ':' + remotePort + '/' + remotePath
                
        print("WARPUNISON | start")
        print(cmd)
        
        for line in runUnison(cmd):
            print(line),

        print("WARPUNISON | done")

        if ( int(self.settings["warpunison"][0]["connection"][0]["openuri"]) == 1):
            os.system('open \'' + str(self.settings["warpunison"][0]["connection"][0]["remoteuri"]) + '\'')


class WarpUnisonCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        #self.window.active_view().insert(edit, 0, "inview")
        print("WARPUNISON | starting")
        currWindow = self.view.window()
        folders = currWindow.folders()
        foldersLen = len(folders)
        if (foldersLen > 1):
            print("WARPUNISON | more than one folder at project top level found, aborting")
            for folder in folders:
                print(folder)
            print("WARPUNISON | abort")
            return
        elif (foldersLen == 0):
            print("WARPUNISON | there must be one top level directory, aborting")
            return
        else:
            projFolder = str(folders[0])
            print("WARPUNISON | project folder: " + projFolder)
            
            uploadConfigFound = 0;

            #find upload config file
            projFileSearch = glob.glob(projFolder+'/*.upload-config')
            if (len(projFileSearch) != 1):
                "WARPUNISON | no upload-config file found in top directory, falling back to sublime-project" 
            else:
                uploadConfigFound = 1;

            #if no upload-config found, fall back to project file
            if (uploadConfigFound == 0):
                #find project file
                projFileSearch = glob.glob(projFolder+'/*.sublime-project')
                if (len(projFileSearch) != 1):
                    "WARPUNISON | no sublime-project file found in top directory" 
                    return
                else:
                    if ( str(settings["folders"][0]["path"]) != str(projFolder) ):
                        print("WARPUNISON | physical folder differs from sublime-project path entry (under folders)! aborting")
                        return

            projFilePath =  str(projFileSearch[0])
            print("WARPUNISON | project file: " + projFilePath)

            settings = loadUnisonSettings(projFilePath)
            #pprint(settings)

            WarpThreadedUnison(settings, projFolder).start()


# ###################################
# rsync part

def loadRsyncSettings(settingpath):
    with open(settingpath) as data_file:    
        data = json.load(data_file)
    return data

def runRsync(cmd):
    #print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while (True):
        retcode = p.poll()
        line    = p.stdout.readline()
        yield line.decode('utf-8')
        if (retcode is not None):
            break

  
class WarpThreadedRsync(threading.Thread):
    def __init__(self, _settings, _projFolder):
        self.settings    = _settings
        self.projFolder  = _projFolder
        threading.Thread.__init__(self)

    def run(self):
        # add delete so that if file is removed locally it is also removed from the server
        excludeStrComp = ""
        for exclude in self.settings["warpsync"][0]["excludes"]:
            excludeStrComp+="--exclude="
            excludeStrComp+='\''+str(exclude)+'\' '

        deleteIfNotLocal = "--delete " if (int(self.settings["warpsync"][0]["opts"][0]["delifnotonlocal"]) == 1) else ""
        deleteExcluded = "--delete-excluded " if (int(self.settings["warpsync"][0]["opts"][0]["deleteexcluded"]) == 1) else ""

        remoteHost = str(self.settings["warpsync"][0]["connection"][0]["host"])
        remotePort = str(self.settings["warpsync"][0]["connection"][0]["port"])
        remoteUser = str(self.settings["warpsync"][0]["connection"][0]["username"])
        remotePath = str(self.settings["warpsync"][0]["connection"][0]["remotepath"])

        # -az : v1
        # -az --no-o --no-g : v2
        # -az --chmod=u+rwx,g+rx : v3
        # http://serverfault.com/questions/364709/how-to-keep-rsync-from-chowning-transfered-files
        # http://unix.stackexchange.com/questions/12198/preserve-the-permissions-with-rsync
        #  -a, --archive    archive mode; equals -rlptgoD (no -H,-A,-X)
        # http://www.comentum.com/rsync.html

        cmd = 'rsync --progress -vv -az --chmod=u+rwx,g+rx --update ' + deleteIfNotLocal + excludeStrComp + deleteExcluded + self.projFolder + '/ ' + '-e \'ssh -p ' + remotePort + '\' ' + remoteUser + '@' + remoteHost + ':' + remotePath
        
        print("WARPSYNC | start")

        #os.system(cmd)
        for line in runRsync(cmd):
            print(line)

        print("WARPSYNC | done")

        if ( int(self.settings["warpsync"][0]["connection"][0]["openuri"]) == 1):
            os.system('open \'' + str(self.settings["warpsync"][0]["connection"][0]["remoteuri"]) + '\'')


class WarpRsyncCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        #self.window.active_view().insert(edit, 0, "inview")
        print("WARPSYNC | starting")
        currWindow = self.view.window()
        folders = currWindow.folders()
        foldersLen = len(folders)
        if (foldersLen > 1):
            print("WARPSYNC | more than one folder at project top level found, aborting")
            for folder in folders:
                print(folder)
            print("WARPSYNC | abort")
            return
        elif (foldersLen == 0):
            print("WARPSYNC | there must be one top level directory, aborting")
            return
        else:
            projFolder = str(folders[0])
            print("WARPSYNC | project folder: " + projFolder)
            
            uploadConfigFound = 0;

            #find upload config file
            projFileSearch = glob.glob(projFolder+'/*.upload-config')
            if (len(projFileSearch) != 1):
                "WARPUNISON | no upload-config file found in top directory, falling back to sublime-project" 
            else:
                uploadConfigFound = 1;

            #if no upload-config found, fall back to project file
            if (uploadConfigFound == 0):
                #find project file
                projFileSearch = glob.glob(projFolder+'/*.sublime-project')
                if (len(projFileSearch) != 1):
                    "WARPUNISON | no sublime-project file found in top directory" 
                    return
                else:
                    if ( str(settings["folders"][0]["path"]) != str(projFolder) ):
                        print("WARPUNISON | physical folder differs from sublime-project path entry (under folders)! aborting")
                        return

            projFilePath =  str(projFileSearch[0])
            print("WARPSYNC | project file: " + projFilePath)

            settings = loadRsyncSettings(projFilePath)
            #pprint(settings)

            WarpThreadedRsync(settings, projFolder).start()



