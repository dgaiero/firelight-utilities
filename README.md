# Installing and configuring the Server

In this guide:

* [Installing and configuring the Server](#installing-and-configuring-the-server)
  * [Use](#use)
  * [Notes](#notes)
  * [Downloading and configuring the server from GitHub](#downloading-and-configuring-the-server-from-github)
  * [Installing server dependecies](#installing-server-dependecies)
  * [Configuring IIS to server wsgi application](#configuring-iis-to-server-wsgi-application)
  * [Final Configuration Steps](#final-configuration-steps)

## Use

As of right now, this server handles processing of handbrake scripts.

## Notes

This guide assumes the following:

1. This guide uses python 3.6.5, windows server 2016 and IIS 10
2. Make sure you have virturalenv installed.

## Downloading and configuring the server from GitHub

1. `git clone https://github.com/dgaiero/firelight-utilities.git`
2. `cd server`
3. `python -m venv script_server`
4. `script_server/Scripts/activate` - All work should be done in the virtural environment.
5. pip install -r requirements.txt

## Installing server dependecies

The script server uses celery to make asynchronous calls alowing commands to be run in the background and the webpage to be closed. This also deals with timeout issues. To setup the distributed task queue handler, you must install celery and RabbitMq.

To install celery, run `pip install celery=3.1.24`. Please note, celery > v4 does not support windows. Once celery is installed, you must also install RabbitMq. Rabbit Mq handles message brokering. To install RabbitMq, visit https://www.rabbitmq.com/. RabbitMq has a dependicy of Erlang, available from: https://www.erlang.org/.

## Configuring IIS to serve wsgi application

IIS must be configured to run a wsgi application.

First, `pip install wfastcgi`. This allows the cgi application to be handled by IIS. Wfastcgi is maintained by Microsoft.

After `wfastcgi` is installed, make sure to run `wfastcgi-enable`.

Follow the below steps to configure a new IIS site.

1. In IIS, under the server, select FastCGI Settings
    1. Right click on the setting that was created from the `wfastcgi-enable` command. Select `Edit`
    2. Click on `Environmental Variables`.
    3. Make sure there are two enviromental variables:
        * Name|Value
           ---|---
           **PYTHONPATH**|Location to server directory (the one with `server.py`)
           **WSGI_HANDLER**|`app.app`
2. Make a new site, none of the settings matter.
    1. Click on `Handler Mappings` in the new site settings.
        1. Click `Add Module Mapping`.
            * Settings|Value
                ---|---
                Request Path|\*
                Module|FastCgiModule
                Executable|(Location to Python in venv)\|(Location to wsgi in venv)<br>Example: `C:\Admin_Utilities\adminScripts\firelight-utilities\server\script_server\Scripts\python.exe\|C:\Admin_Utilities\adminScripts\firelight-utilities\server\script_server\Lib\site-packages\wfastcgi.py`
                Name|Doesn't matter
    2. Click on `Application Settings` in the new site settings.
        * Settings|Value
           ---|---
           **PYTHONPATH**|Location to server directory (the one with `server.py`)
           **WSGI_HANDLER**|`app.app`
           **WSGI_RESTART_FILE_REGEX**|`.*((\.py)\|(\.config))$`
3. Make sure whatever account is being used to authenticate the website has `RWX` access to all directories necessary (server directory, all directories specified in handbrake_util `settings.ini`, etc.). Also, make sure the `DOMAIN\IIS_ISURS` and `.\ISUR` has the same access.

A Sample `web.config` file is shown below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <appSettings>
    <add key="PYTHONPATH" value="C:\Admin_Utilities\adminScripts\firelight-utilities\server" />
    <add key="WSGI_HANDLER" value="server.app" />
    <add key="WSGI_RESTART_FILE_REGEX" value=".*((\.py)|(\.config))$" />
  </appSettings>
  <system.web>
    <compilation debug="false" targetFramework="4.0" />
  </system.web>
  <system.webServer>
    <modules runAllManagedModulesForAllRequests="true" />
        <httpErrors errorMode="Custom" />
        <handlers>
            <add name="Script Server Python FastCgi Handler" path="*" verb="*" modules="FastCgiModule" scriptProcessor="C:\Admin_Utilities\adminScripts\firelight-utilities\server\script_server\Scripts\python.exe|C:\Admin_Utilities\adminScripts\firelight-utilities\server\script_server\Lib\site-packages\wfastcgi.py" resourceType="Unspecified" />
        </handlers>
  </system.webServer>
</configuration>
```


## Final Configuration Steps

1. Celery needs to be started in dameon mode. The `service_worker.bat` activates the `virturalenv` and then starts `celery` to listen to incomming requests. You may install this however you wish, but one method is to use task scheduler to automatically start the task at startup.
