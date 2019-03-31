import os
import subprocess
import sys
import datetime
import time
from configparser import ConfigParser
from io import StringIO

import click
import sendgrid
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
        self.process_movies = settings_config.get(
            'directory_settings', 'process_movies')
        self.movie_input_directory = settings_config.get(
            'directory_settings', 'movie_input_directory')
        self.movie_processed_directory = settings_config.get(
            'directory_settings', 'movie_processed_directory')
        self.movie_output_directory = settings_config.get(
            'directory_settings', 'movie_output_directory')
        # TV Show Directory Settings #TODO: Write TV Processing
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
        # self.movie_file_dir_list = [("1", "1")]

    def proc_movies(self):
        ''' Processes Movies in given input directory and moves them to processed directory '''
        for folder in self.movie_file_dir_list:
            print("\n##########################################")
            in_file = folder[0]
            out_file = os.path.join(
                self.movie_output_directory, folder[1] + ".mkv")
            preset_file = os.path.join(self.current_directory, self.preset_settings_location)
            move_file = os.path.join(self.movie_processed_directory, folder[1])
            # Subprocess call for handbrake encode
            # Select main feature track
            # Import pre-selected preset file
            subproc_handbrake_call = 'HandBrakeCLI -i "{}" --main-feature -o "{}" --preset-import-file "{}"'.format(
                in_file, out_file, preset_file)
            handbrake_err = command_proc(subproc_handbrake_call)
            if handbrake_err == 0:
                subproc_du_call = 'du -h "{}"'.format(out_file)
                print("Checking File Size")
                command_proc(subproc_du_call, True)
                subproc_mv_call = 'mv "{}" "{}"'.format(in_file, move_file)
                command_proc(subproc_mv_call)
            else:
                print("Skipping move due to prior errors.")


    def send_email(self, body):
        sg = sendgrid.SendGridAPIClient(apikey=self.sendgrid_API)
        from_email = Email(self.from_email)
        to_email = Email(self.to_email)
        subject = "PLEX Processing Result"
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


def logger():
    pass


def command_proc(runstr, show_output = False):
    
    print("Processing Command: {}\n".format(runstr))
    start_time = time.time()
    subproc_call = subprocess.Popen(
        runstr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = subproc_call.communicate()
    errcode = subproc_call.returncode
    end_time = time.time()
    time_delta = end_time - start_time
    human_time_delta = datetime.timedelta(seconds=time_delta).__str__()
    if show_output is True:
        print("OUTPUT: {}".format(out.decode('utf-8')))
    if errcode is not 0:
        print("ERROR\nOUTPUT SHOWN BELOW")
        print("-------------------OUTPUT-------------------")
        print(out.decode('utf-8'))
        print("-------------------ERRORS-------------------")
        print(err.decode('utf-8'))
        print("-------------------ERCODE-------------------")
        print(str(errcode))
    else:
        print("Processed Command successfully.")
    print("Total Time: {}".format(human_time_delta))
    return errcode

def list_dir():
    raise NotImplementedError

@click.command()
@click.option('--setting', default='settings.ini', help='Settings.ini file location')
def main(setting=''):
    vProc = VideoProcessor(setting)
    if vProc.send_mail:
        old_stdout = sys.stdout
        sys.stdout = proc_stdout = StringIO()
        print("<pre>")
    print("Processing {} movies".format(len(vProc.movie_file_dir_list)))
    print("-------------------")
    for directory in vProc.movie_file_dir_list:
        print("In Queue: {}".format(directory[1]))
    if len(vProc.movie_file_dir_list) != 0:
        vProc.proc_movies()
    else:
        print("No Files Processed.")
    if vProc.send_mail:
        print("</pre>")
        sys.stdout = old_stdout
        email = proc_stdout.getvalue()
        print(email)
        vProc.send_email(email)


if __name__ == "__main__":
    main()
