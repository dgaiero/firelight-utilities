import os
import sys
from io import StringIO

from celery import Celery
from flask import Flask, render_template

sys.path.append(os.path.dirname(os.getcwd()))
import handbrake_util.handbrake_plex_encode


app = Flask(__name__)
app.debug = True

celery = Celery(app.name, broker='amqp://localhost')


@app.route('/')
def index():
    return("Please navigate to the script URL provided to you.")


@app.route('/handbrake-util')
def handbrake_process():
    ''' Checks if lockfile exists, and if it does, exits. Otherwise, the handbrake processing script will be called to handle final procesing of video '''
    handbrake_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "handbrake_util")
    if os.path.isfile(os.path.join(handbrake_proc_dir, ".lockfile")):
        return("The Video Processing Script has been assigned to a runner.\nOn completion, the script will finish and an email will be sent to the recipients in the configuration file.")
    else:
        open(os.path.join(handbrake_proc_dir, ".lockfile"), "w")
        handbrake_proc_runner.apply_async()
        return ("You may now close this window. On completion, the script will finish and an email will be sent to the recipients in the configuration file.")


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
        print("Processing {} movies".format(len(vProc.movie_file_dir_list)))
        print("-------------------")
        for directory in vProc.movie_file_dir_list:
            print("In Queue: {}".format(directory[1]))
        vProc.proc_movies()
        if vProc.send_mail:
            sys.stdout = old_stdout
            email = proc_stdout.getvalue()
            print(email)
            vProc.send_email(email)
        os.remove(os.path.join(handbrake_proc_dir, ".lockfile"))
    except Exception as e:
        os.remove(os.path.join(handbrake_proc_dir, ".lockfile"))
        raise Exception(e)


if __name__ == "__main__":
    ''' For debug purposes only. '''
    app.run(host='0.0.0.0', debug=True)
