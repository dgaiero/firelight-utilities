import os
import sys
from io import StringIO

from celery import Celery
from celery.signals import worker_process_init
from multiprocessing import current_process

from flask import Flask, render_template, request, Response, stream_with_context
import time

sys.path.append(os.path.dirname(os.getcwd()))
import handbrake_util.handbrake_plex_encode
import movie_concat.concatClips


app = Flask(__name__)
app.debug = True

celery = Celery(app.name, broker='amqp://localhost')


@app.route('/')
def index():
    links = ""
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            links += "<a href='{0}{1}'>{0}{1}</a>\n".format(request.base_url[0:-1], rule)
    links += "</pre>"
    return("<pre>The following are valid rules. Either click the one below or navigate to the URL directly.\n\n" + links)
    # return("Please navigate to the script URL provided to you.")

@app.route('/handbrake-util')
def handbrake_process():
    ''' Checks if lockfile exists, and if it does, exits. Otherwise, the handbrake processing script will be called to handle final procesing of video '''
    # return("<b><pre>Due to excessive server load, this script cannot be run at this time. Please try again later.</pre></b>")
    handbrake_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "handbrake_util")
    processStatus = request.args.get('process')
    if processStatus == "True":
        if os.path.isfile(os.path.join(handbrake_proc_dir, ".lockfile")):
            return("<pre>The Video Processing Script has been assigned to a runner.\nOn completion, the script will finish and an email will be sent to the recipients in the configuration file.</pre>")
        else:
            open(os.path.join(handbrake_proc_dir, ".lockfile"), "w")
            handbrake_proc_runner.apply_async()
            return ("<pre>You may now close this window. On completion, the script will finish and an email will be sent to the recipients in the configuration file.</pre>")
    vProc = handbrake_util.handbrake_plex_encode.VideoProcessor(
        os.path.join(handbrake_proc_dir, "settings.ini"))
    if vProc.movie_file_dir_list != []:
        returnString = "<pre><b>Movies to be processed:</b>\n"
        for directory in vProc.movie_file_dir_list:
                returnString += "* {}\n".format(directory[1])
        returnString += "\n<em>Click the following link to process the movies:</em>\n<b>Please Note:</b> If you wish to change your settings or movies to be processed, please modify the folder directly in the share.</pre>"
        returnString += "<pre><a href='{0}?process=True'>{0}?process=True</a><br></pre>".format(
            request.base_url)
        return returnString
    return "<pre><b>No movies in the MovieFolder.</b></pre>"

@celery.task
def handbrake_proc_runner():
    ''' Handles processing of moves and handoff to handbrake-util script.
        Redirects stdout if email flag is set to true in vProc. Returns plain text to display to end user on webpage '''
    handbrake_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "handbrake_util")
    try:
        vProc = handbrake_util.handbrake_plex_encode.VideoProcessor(
            os.path.join(handbrake_proc_dir, "settings.ini"))
        if vProc.send_mail:
            old_stdout = sys.stdout
            sys.stdout = proc_stdout = StringIO()
        print("<pre>")
        print("Processing {} movies".format(len(vProc.movie_file_dir_list)))
        print("-------------------")
        for directory in vProc.movie_file_dir_list:
            print("In Queue: {}".format(directory[1]))
        vProc.proc_movies()
        if vProc.send_mail:
            print("</pre>")
            sys.stdout = old_stdout
            email = proc_stdout.getvalue()
            print(email)
            vProc.send_email(email)
        os.remove(os.path.join(handbrake_proc_dir, ".lockfile"))
    except Exception as e:
        os.remove(os.path.join(handbrake_proc_dir, ".lockfile"))
        raise Exception(e)

@app.route('/movie-proc')
def movie_processor():
    movie_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "movie_concat")
    vProc = movie_concat.concatClips.VideoProcessor(
        os.path.join(movie_proc_dir, "settings.ini"))
    

    movie_dirs = "<pre><b>Chose a directory below:</b>\n"
    folder = request.args.get('dir')
    print(request.args)
    if folder:
        if request.args.get('start'):
            if os.path.isfile(os.path.join(movie_proc_dir, ".lockfile")):
                return("<pre>A video is being processed. You must wait for it to finish before submitting a new job.</pre>")
            else:
                open(os.path.join(movie_proc_dir, ".lockfile"), "w")
                movie_proc_runner.delay(folder)
                return ("<pre>You may now close this window. On completion, the script will finish and an email will be sent to the recipients in the configuration file.</pre>")

        else:
            if vProc.get_files(folder) == []:
                return f"<pre>It appears that there are no files which match the file type criteria ({vProc.movie_file_extensions}). Double check that you have the right files.</pre>"
            else:
                returnStr = f"<pre>Current directory <b>{vProc.movie_input_directory}{folder}</b> (<a href='{request.base_url}'>Go back to directory selection</a>).\n"
                returnStr += f"The output file will be located in {vProc.movie_input_directory}{folder}.mp4\n"
                if vProc.copy_to_plex:
                    returnStr += f"Copy to plex is enabled, so the output file will be copied to the plex home videos directory.\n"
                returnStr += f"Only the following extensions will be processed: {vProc.movie_file_extensions}. To change this, edit the settings.ini file.\n"
                returnStr += "\n<em>The following files will be processed:</em>\n"
                for file in vProc.get_files(folder):
                    returnStr += f"* {file[0]} ({time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(file[1]))})\n"
                returnStr += f"<b>To continue, click <a href='{request.base_url}?dir={folder}&start=true'>here</a></b>"
                return returnStr + "</pre>"

    else:
        for folder in vProc.list_dirs():
            movie_dirs += "* <a href='{0}?dir={1}'>{1}</a> ({2})\n".format(
                request.base_url, folder[1], folder[0])
        return movie_dirs + "</pre>"


@worker_process_init.connect
def fix_multiprocessing(**kwargs):
    try:
        current_process()._config
    except AttributeError:
        current_process()._config = {'semprefix': '/mp'}

@celery.task
def movie_proc_runner(folder):
    ''' Handles processing of moves and handoff to handbrake-util script.
        Redirects stdout if email flag is set to true in vProc. Returns plain text to display to end user on webpage '''
    movie_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "movie_concat")
    try:
        vProc = movie_concat.concatClips.VideoProcessor(
        os.path.join(movie_proc_dir, "settings.ini"))
        if vProc.send_mail:
            old_stdout = sys.stdout
            sys.stdout = proc_stdout = StringIO()
        print("<pre>")
        print(f"Processing folder: {vProc.movie_input_directory}{folder}")
        print("\n<em>The following files will be processed:</em>")
        for file in vProc.get_files(folder):
            print(f"* {file[0]} ({time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(file[1]))})")
        print(f"The output file will be located in {vProc.movie_input_directory}{folder}.mp4")
        vProc.concat(folder)
        if vProc.copy_to_plex:
            print(f"Copy to plex is enabled, the output file will be copied to the plex home videos directory.")
            vProc.copyOutputFile(folder)
        else:
            print(f"Copy to plex is disabled, the output file will not be copied to the plex home videos directory.")
        if vProc.send_mail:
            print("</pre>")
            sys.stdout = old_stdout
            email = proc_stdout.getvalue()
            print(email)
            vProc.send_email(email, f"{vProc.movie_input_directory}{folder}.mp4 finished processing")
        os.remove(os.path.join(movie_proc_dir, ".lockfile"))
    except Exception as e:
        os.remove(os.path.join(movie_proc_dir, ".lockfile"))
        raise Exception(e)

if __name__ == "__main__":
    ''' For debug purposes only. Set host to 0.0.0.0 to allow access on all NICs.'''
    app.run(host='0.0.0.0', debug=True)
