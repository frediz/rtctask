RTC cli client
===================

## Install 

rtc.py : attempt to write a python client to RTC. At the moment, it essentially
deals with workitems, can search through users and stored queries.
Needs python-requests >= 2.4.0

In order to install it, you should run:

$ apt-get install python-pip python-html2text
$ pip install requests

## ID file

Here is an example of the ~/.rtcrc file to start with:

```
[auth]
id = user@cc.ibm.com
password = mypasswordincleartext
[query]
default =
[display]
maxtitlelen =
```
