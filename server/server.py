import os
import sys
from io import StringIO

from celery import Celery
from flask import Flask, render_template, request, Response, stream_with_context

sys.path.append(os.path.dirname(os.getcwd()))
import handbrake_util.handbrake_plex_encode


app = Flask(__name__)
app.debug = True

celery = Celery(app.name, broker='amqp://localhost')


@app.route('/')
def index():
    links = ''
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            links += "<a href='{0}{1}'>{0}{1}</a><br>".format(request.base_url,rule)
    return("<pre>The following are valid rules. Either click the one below or navigate to the URL directly.</pre><br>" + links)
    # return("Please navigate to the script URL provided to you.")

@app.route('/test')
def test():
    return "<h1>Hello World</h1>"

@app.route('/handbrake-util')
def handbrake_process():
    ''' Checks if lockfile exists, and if it does, exits. Otherwise, the handbrake processing script will be called to handle final procesing of video '''
    # return("<b><pre>Due to excessive server load, this script cannot be run at this time. Please try again later.</pre></b>")
    handbrake_proc_dir = os.path.join(os.path.dirname(
        os.getcwd()), "handbrake_util")
    processStatus = request.args.get('process')
    if processStatus == True:
        if os.path.isfile(os.path.join(handbrake_proc_dir, ".lockfile")):
            return("<pre>The Video Processing Script has been assigned to a runner.\nOn completion, the script will finish and an email will be sent to the recipients in the configuration file.</pre>")
        else:
            open(os.path.join(handbrake_proc_dir, ".lockfile"), "w")
            handbrake_proc_runner.apply_async()
            return ("<pre>You may now close this window. On completion, the script will finish and an email will be sent to the recipients in the configuration file.</pre>")
    vProc = handbrake_util.handbrake_plex_encode.VideoProcessor(
        os.path.join(handbrake_proc_dir, "settings.ini"))
    returnString = "<pre>"
    for directory in vProc.movie_file_dir_list:
            returnString += "In Queue: {}\n".format(directory[1])
    returnString += "</pre>"
    returnString += "<a href='{0}'>{0}</a><br>".format(request.base_url)
    return returnString


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


if __name__ == "__main__":
    ''' For debug purposes only. Set host to 0.0.0.0 to allow access on all NICs.'''
    app.run(host='0.0.0.0', debug=True)
