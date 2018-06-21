import os
import subprocess
import sys
import time
from configparser import ConfigParser
from io import StringIO

import sendgrid
from sendgrid.helpers.mail import *


class VideoProcessor:

    def __init__(self):
        # Setup settings configuration for settings.ini file
        settings_config = ConfigParser()
        settings_config.read('settings.ini')
        # Mail Settings
        self.send_mail = settings_config.get('mail_settings', 'send_mail')
        self.sendgrid_API = settings_config.get('mail_settings', 'sendgrid_API')
        self.from_email = settings_config.get('mail_settings', 'from_email')
        self.to_email = settings_config.get('mail_settings', 'to_email')
        # Directory Settings
        ## Movie Directory Settings
        self.process_movies = settings_config.get('directory_settings', 'process_movies')
        self.movie_input_directory = settings_config.get(
            'directory_settings', 'movie_input_directory')
        self.movie_processed_directory = settings_config.get(
            'directory_settings', 'movie_processed_directory')
        self.movie_output_directory = settings_config.get(
            'directory_settings', 'movie_output_directory')
        ## TV Show Directory Settings #TODO: Write TV Processing
        self.process_tv_shows = settings_config.get(
            'directory_settings', 'process_tv_shows')
        self.tv_shows_input_directory = settings_config.get(
            'directory_settings', 'tv_shows_input_directory')
        self.tv_shows_processed_directory = settings_config.get(
            'directory_settings', 'tv_shows_processed_directory')
        self.tv_shows_output_directory = settings_config.get(
            'directory_settings', 'tv_shows_output_directory')
        # Other Settings
        self.preset_settings_location = settings_config.get(
            'settings', 'preset_setting')

        self.movie_file_dir_list = find_dirs(self.movie_input_directory)

    def proc_movies(self):
        ''' Processes Movies in given input directory and moves them to processed directory '''
        for folder in self.movie_file_dir_list:
            in_file = folder[0]
            out_file = os.path.join(
                self.movie_output_directory, folder[1] + ".mkv")
            move_file = os.path.join(self.movie_processed_directory, folder[1])
            # Subprocess call for handbrake encode
            ## Output JSON format (for later use...)
            ## Select main feature track
            ## Import pre-selected preset file
            subproc_handbrake_call = 'HandBrakeCLI --json -i "{}" --main-feature -o "{}" --preset-import-file "{}"'.format(
                in_file, out_file, self.preset_settings_location)
            self.command_proc(subproc_handbrake_call)
            subproc_mv_call = 'mv "{}" "{}"'.format(in_file, move_file)
            self.command_proc(subproc_mv_call)

    def command_proc(self, runstr):
        print("Processing Command: {}\n".format(runstr))
        subproc_call = subprocess.Popen(runstr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = subproc_call.communicate()
        errcode = subproc_call.returncode

        if errcode is not 0:
            print("ERROR\nOUTPUT SHOWN BELOW\n\n")
            print("-------------------OUTPUT-------------------" + "\n")
            print(out.decode('utf-8') + "\n")
            print("-------------------ERRORS-------------------" + "\n")
            print(err.decode('utf-8') + "\n")
            print("-------------------ERCODE-------------------" + "\n")
            print(str(errcode) + "\n")
        else:
            print("Processed Command:  " + runstr + " successfully" + "\n")

    def send_email(self, body):
        sg = sendgrid.SendGridAPIClient(apikey=self.sendgrid_API)

        from_email = Email(self.from_email)
        to_email = Email(self.to_email)
        subject = "PLEX Processing Result"
        content = Content("text/plain", body)
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

def main():
    old_stdout = sys.stdout
    sys.stdout = proc_stdout = StringIO()
    vProc = VideoProcessor()
    vProc.proc_movies()
    sys.stdout = old_stdout
    email = proc_stdout.getvalue()
    print(email)
    vProc.send_email(email)



# def main():
#     old_stdout = sys.stdout
#     sys.stdout = mystdout = StringIO()
#     email = ''
#     settings_config = ConfigParser()
#     settings_config.read('settings.ini')
#     preset_file = settings_config.get('settings', 'preset_setting')
#     handbrake_runstr = 'HandBrakeCLI --json -i "{}" --main-feature -o "{}" --preset-import-file "{}"'
#     cp_runstr = 'cp "{}" "{}"'
#     movie_input_directory = settings_config.get(
#         'directory_settings', 'movie_input_directory')
#     movie_processed_directory = settings_config.get('directory_settings', 'movie_processed_directory')
#     movie_output_directory = settings_config.get(
#         'directory_settings', 'movie_output_directory')
#     file_list = []
#     for root, dirs, files in walklevel(movie_input_directory):
#         file_name = root.replace(movie_input_directory,"")
#         file_list.append((root, file_name))

#     file_list = file_list[1:]

#     while file_list:
#         file_data = file_list.pop()
#         in_file = file_data[0]
#         out_file = os.path.join(movie_output_directory, file_data[1] + ".mkv")
#         move_file = os.path.join(movie_processed_directory, file_data[1])
#         print("Processing: " + in_file + "\n")
#         subproc_handbrake_call = subprocess.Popen(handbrake_runstr.format(
#             in_file, out_file, preset_file), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#         out, err = subproc_handbrake_call.communicate()
#         errcode = subproc_handbrake_call.returncode

#         if errcode is not 0:
#             print("-------------------OUTPUT-------------------" + "\n")
#             print(out.decode('utf-8') + "\n")
#             print("-------------------ERRORS-------------------" + "\n")
#             print(err.decode('utf-8') + "\n")
#             print("-------------------ERCODE-------------------" + "\n")
#             print(str(errcode) + "\n")
#         else:
#             print("Processed: " + out_file + " successfully" + "\n")
#         print("Moving {} to {}".format(in_file, move_file) + "\n")
#         subproc_copy_call = subprocess.Popen(cp_runstr.format(
#             in_file, move_file), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#         out, err = subproc_copy_call.communicate()
#         errcode = subproc_copy_call.returncode
#         if errcode is not 0:
#             print("-------------------OUTPUT-------------------" + "\n")
#             print(out.decode('utf-8'))
#             print("-------------------ERRORS-------------------" + "\n")
#             print(err.decode('utf-8'))
#             print("-------------------ERRCOD-------------------" + "\n")
#             print(str(errcode))
#         else:
#             print("Moved: " + move_file + " successfully" + "\n")
        
#         # print(out_file)

#     sys.stdout = old_stdout
#     email = mystdout.getvalue()
#     print(email)
#     if settings_config.get('mail_settings', 'send_mail') == "True":
#         send_email(email)

# # runstr = 'HandBrakeCLI -i "{in_dir}" -o "{out_file}" --preset-import-file "plex_preset.json"'

# def send_email(body):
#     settings_config = ConfigParser()
#     settings_config.read('settings.ini')
#     sg_api = settings_config.get('mail_settings', 'sendgrid_API')
#     sg = sendgrid.SendGridAPIClient(apikey=sg_api)

#     from_email = Email(settings_config.get('mail_settings', 'from_email'))
#     to_email = Email(settings_config.get('mail_settings', 'to_email'))
#     subject = "PLEX Processing Result"
#     content = Content("text/plain", body)
#     mail = Mail(from_email, subject, to_email, content)
#     sg.client.mail.send.post(request_body=mail.get())



if __name__ == "__main__":
    main()
