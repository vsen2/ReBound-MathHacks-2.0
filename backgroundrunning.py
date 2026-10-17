import os

from win32com.client import Dispatch
import winshell


#pathing
#get the whole file path
file_path = os.path.abspath(__file__)
#the the directory path of the file
script_dir = os.path.dirname(file_path)
#name of file
file_name = os.path.basename(file_path)
#make link name
link_name = "ReBound.lnk"
#get path of startup folder
startup_folder = winshell.startup()
#make the shortcut path
shortcut_path = os.path.join(startup_folder, link_name)
#make zipped folder
zipped_dir = os.path.join(script_dir,"zipped_dir")
#make stored images path
stored_images = os.path.join(zipped_dir,"images")

#if the shortcut path is not a file
if not os.path.isfile(shortcut_path):
    #make shortcup obj
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    #set working directory
    shortcut.WorkingDirectory = os.path.dirname(file_path)
    #hide console with pythonw
    shortcut.Targetpath = "pythonw.exe"
    #as file_path
    shortcut.Arguments = f'"{file_path}"'
    # Save the shortcut file
    shortcut.Save()
