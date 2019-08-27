import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import time
from configparser import ConfigParser
from io import StringIO

import click
import cv2
import sendgrid
import numpy as np
from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, TextClip
from PIL import Image, ImageDraw, ImageFont
from sendgrid.helpers.mail import Content, Email, Mail


class VideoProcessor:

    def __init__(self, config_location):
        # Setup settings configuration for settings.ini file
        settings_config = ConfigParser()
        settings_config.read(config_location)
        # Mail Settings
        self.send_mail = settings_config.get('mail_settings', 'send_mail')
        self.sendgrid_API = settings_config.get(
            'mail_settings', 'sendgrid_API')
        self.from_email = settings_config.get('mail_settings', 'from_email')
        self.to_email = settings_config.get('mail_settings', 'to_email')
        # Directory Settings
        self.current_directory = os.path.join(os.path.dirname(os.getcwd()), "handbrake_util")
        # Movie Directory Settings
        self.movie_input_directory = settings_config.get(
            'directory_settings', 'movie_input_directory')
        self.copy_to_plex = settings_config.get(
            'directory_settings', 'copy_to_plex')
        self.movie_file_extensions = json.loads(settings_config.get(
            'directory_settings', 'movie_file_extensions'))
        self.plex_home_video_directory = settings_config.get(
            'directory_settings', 'plex_home_video_directory')
        # print(json.loads((self.movie_file_extensions)))
        self.movie_file_dir_list = find_dirs(self.movie_input_directory)
        self.files = []

    def list_dirs(self):
        return self.movie_file_dir_list

    def get_files(self, dir_name):
        pathName = os.path.join(self.movie_input_directory,dir_name)
        files = walklevel(pathName, 5)
        rootDirFileList = list(files)
        fileList = []
        for item in rootDirFileList:
            for file in item[2]:
                if not(file.lower().endswith(tuple(self.movie_file_extensions))):
                    continue
                fileList += [f"{item[0]}\{file}"]
        fileDateList = []
        for item in fileList:
            fileDateList.append((item, os.path.getmtime(item)))
        fileDateList.sort(key=lambda file: os.path.getctime(file[0]))
        self.files = fileDateList
        return fileDateList

    def concat(self, folder):
        start_time = time.clock()
        self.createTitleSlide(folder)
        filesToConcat = self.get_files(folder)
        filesToConcat = list(map(lambda file: VideoFileClip(file[0]), filesToConcat))
        # filesToConcat=  []
        titleSlide = ImageClip(f"{self.movie_input_directory}temp.PNG", duration=3)
        filesToConcat =  [titleSlide] + filesToConcat
        final_clip = concatenate_videoclips(filesToConcat)
        final_clip.write_videofile(f"{self.movie_input_directory}/{folder}.mp4")
        end_time = time.clock()
        os.remove(f"{self.movie_input_directory}temp.PNG")
        print(f"done in {str(datetime.timedelta(seconds=end_time - start_time))}")
        # print(filesToConcat)

    def copyOutputFile(self, folder):
        try:
            os.makedirs(os.path.join(self.plex_home_video_directory,folder))
        except FileExistsError:
            print(f"{self.plex_home_video_directory}/{folder} already exists.")
        shutil.move(f"{self.movie_input_directory}/{folder}.mp4",
                    f"{self.plex_home_video_directory}/{folder}/{folder}.mp4")

    def createTitleSlide(self, folder):
        W, H = (1920, 1080)
        msg = folder
        im = Image.new("RGBA", (W, H), "black")
        draw = ImageDraw.Draw(im)
        dfont = ImageFont.truetype(font="arial", size=int(48))
        w, h = draw.textsize(msg, font=dfont)
        draw.text(((W-w)/2, (H-h)/2), msg, fill="white", font=dfont)
        im.save(f"{self.movie_input_directory}temp.PNG", "PNG")

    def send_email(self, body, subject):
        sg = sendgrid.SendGridAPIClient(apikey=self.sendgrid_API)
        from_email = Email(self.from_email)
        to_email = Email(self.to_email)
        content = Content("text/html", body)
        mail = Mail(from_email, subject, to_email, content)
        sg.client.mail.send.post(request_body=mail.get())



def find_dirs(root_dir):
    file_list = []
    for root, dirs, files in walklevel(root_dir):
        file_name = root.replace(root_dir, "")
        file_list.append((root, file_name))

    return file_list[1:]


def walklevel(some_dir, level=1):
    """ Same as os.walk with level command """
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]
