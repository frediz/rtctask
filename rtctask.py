#!/usr/bin/env python
# frediz@linux.vnet.ibm.com

import requests
requests.packages.urllib3.disable_warnings()
import json
import pprint
import re
import os, sys
import html2text
import getpass
import argparse
import tempfile, subprocess
import ConfigParser

## color stuff
class cl:
    """
    Colors class:
    reset all colors with colors.reset
    two subclasses fg for foreground and bg for background.
    use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.green
    also, the generic bold, disable, underline, reverse, strikethrough,
    and invisible work with the main class
    i.e. colors.bold
    """
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg:
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg:
        black='\033[40m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'
## end of color


class RTCClient(object):
    HOST = 'https://jazz06.rchland.ibm.com:12443/jazz/' 
    PROJECT = '_zNTKcB3lEeK8Y908RIgA1A'
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.session = requests.Session()
        r = self.get_authed_session()
        self.category='_LqSO0L0qEeSLGNNvkdKuNQ'

    def sget(self, url, **kwargs):
        return self.session.get(RTCClient.HOST + url, allow_redirects=True, verify=False, **kwargs)

    def spost(self, url, **kwargs):
        return self.session.post(RTCClient.HOST + url, allow_redirects=True, verify=False, **kwargs)

    def sput(self, url, **kwargs):
        return self.session.put(RTCClient.HOST + url, allow_redirects=True, verify=False, **kwargs)

    def spatch(self, url, **kwargs):
        return self.session.patch(RTCClient.HOST + url, allow_redirects=True, verify=False, **kwargs)

    def get_authed_session(self):
        self.sget('authenticated/identity', headers={'Accept':'application/xml'})
        return self.spost('j_security_check', data={'j_username':self.user,'j_password':self.password})


class Task():
    NEW = {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/1'}
    INPROGRESS = {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/2'}
    DONE = {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/3'}
    INVALID = {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/com.ibm.team.workitem.taskWorkflow.state.s4'}

    def __init__(self, jclient, taskid = None):
        self.jclient = jclient
        self.taskid = taskid

    def create(self, title, description, owner = None):
        if owner is None:
            owner = { 'dc:title': "{currentUser}" }
        js = {
                'dc:description': description,
                'dc:title': title,
                'dc:type': { 'rdf:resource': RTCClient.HOST + 'oslc/types/%s/task'%(RTCClient.PROJECT) },
                'rtc_cm:filedAgainst': { 'rdf:resource': RTCClient.HOST + 'resource/itemOid/com.ibm.team.workitem.Category/%s'%(self.jclient.category) },
                'rtc_cm:ownedBy': owner,
             }
        return self.jclient.spost('oslc/contexts/'+ RTCClient.PROJECT+'/workitems', json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def get_comments(self):
        r = self.jclient.sget('oslc/workitems/'+ str(self.taskid) +'/rtc_cm:comments.json?oslc_cm.properties=dc:created,dc:description,dc:creator{dc:title}')
        return json.loads(r.text)

    def add_comment(self, comment):
        return self.jclient.spost('oslc/workitems/'+ str(self.taskid) +'/rtc_cm:comments', json={'dc:description':comment}, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def change(self, js):
        return self.jclient.spatch('oslc/workitems/'+ str(self.taskid), json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def startWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.INPROGRESS
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.startWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def stopWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.NEW
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.stopWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def reopen(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        if r['rtc_cm:state'] == Task.INVALID:
            r['rtc_cm:state'] = Task.NEW
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.reopen', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})
        elif r['rtc_cm:state'] == Task.DONE:
            r['rtc_cm:state'] = Task.INPROGRESS
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a1', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def invalidate(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.INVALID
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a2', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def resolve(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.DONE
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.taskid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.resolve', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def get_json(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.taskid) +'.json'+args)
        return json.loads(r.text)
    def get_xml(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.taskid) +'.xml'+args)
        return r.text


# Misc functions to do option's work
def user_search(client, pattern):
    r = client.sget('oslc/users.json?oslc_cm.query=dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def query_search(client, pattern):
    r = client.sget('oslc/queries.json?oslc_cm.query=rtc_cm:projectArea="'+RTCClient.PROJECT+'" and dc:creator="{currentUser}" and dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def print_queries(client, pattern):
    print
    print "Queries matching : "+cl.fg.blue+pattern+cl.reset
    print " Created                 | Name                             | Description"
    print "===================================================================================="
    for u in query_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + cl.fg.green+u['dc:title'].ljust(32)+cl.reset +" | "+u['dc:description']

def print_users(client, pattern):
    print
    print "Users matching : "+cl.fg.blue+pattern+cl.reset
    print " Created                 | Name                             | Email"
    print "===================================================================================="
    for u in user_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + cl.fg.green+u['dc:title'].ljust(32)+cl.reset +" | "+re.sub(r'mailto:([^%]+)%40(.*)',r'\1@\2',u['rtc_cm:emailAddress'])

def color_state(state):
    if state == Task.NEW:
        return cl.fg.purple
    elif state == Task.INPROGRESS:
        return cl.fg.lightred
    elif state == Task.INVALID:
        return cl.fg.lightgrey
    elif state == Task.DONE:
        return cl.fg.green

def task_fromquery(client, pattern):
    query = re.sub(r'.*/([^/]+)',r'\1',query_search(client, pattern)['oslc_cm:results'][0]['rdf:resource'])
    r = client.sget('oslc/queries/'+query+'/rtc_cm:results.json')
    tasks = json.loads(r.text)
    print "  ID  | Title"
    print "=================================================================="
    for t in tasks:
        print color_state(t['rtc_cm:state'])+str(t['dc:identifier'])+cl.reset + " | " + t['dc:title']

def task_ownedbyme(client):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=rtc_cm:ownedBy="{currentUser}" /sort=rtc_cm:state')
    tasks = json.loads(r.text)
    print "  ID  | Title"
    print "=================================================================="
    for t in tasks['oslc_cm:results']:
        print color_state(t['rtc_cm:state'])+str(t['dc:identifier'])+cl.reset + " | " + t['dc:title']

def task_search(client, pattern):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=oslc_cm:searchTerms="'+pattern+'"')
    tasks = json.loads(r.text)
    print
    print "Tasks matching : "+cl.fg.blue+pattern+cl.reset
    print "  ID  | Title"
    print "=================================================================="
    for t in tasks['oslc_cm:results']:
        print color_state(t['rtc_cm:state'])+str(t['dc:identifier'])+cl.reset + " | " + t['dc:title']

def task_bytag(client, tag):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=oslc_cm:searchTerms="'+tag+'"')
    tasks = json.loads(r.text)
    print
    print "Tasks matching : "+cl.fg.blue+tag+cl.reset
    print "  ID  | Title"
    print "=================================================================="
    for t in tasks['oslc_cm:results']:
        print color_state(t['rtc_cm:state']) + str(t['dc:identifier'])+cl.reset + " | " + t['dc:title']

def task_details(client, taskid):
    task = Task(client, taskid)
    js = task.get_json('?oslc_cm.properties=dc:identifier,dc:title,rdf:resource,dc:creator{dc:title},rtc_cm:ownedBy{dc:title},dc:description,rtc_cm:state{dc:title}')
    print
    print "=================================================================="
    print "Task ID : " +cl.fg.green+str(js['dc:identifier'])+cl.reset
    print "Title   : " +cl.fg.red+ js['dc:title']+cl.reset
    print "URL     : " +js['rdf:resource']
    print "State   : " +color_state({ u'rdf:resource': js['rtc_cm:state']['rdf:resource']}) + js['rtc_cm:state']['dc:title'] + cl.reset
    print "Creator : " +js['dc:creator']['dc:title']
    print "Owner   : " +js['rtc_cm:ownedBy']['dc:title']
    print "Description:"
    print html2text.html2text(js['dc:description'])
    comments = task.get_comments()
    print "Comments :"
    i = 0
    for c in comments:
        print str(i) + ": " +cl.fg.green+ c['dc:creator']['dc:title']+cl.reset+" ("+c['dc:created'] + ") :"
        print html2text.html2text(c['dc:description'])
        i = i + 1

def task_comment(client, taskid, comment):
    task = Task(client, taskid)
    return task.add_comment(comment)

def task_create(client, title, description):
    task = Task(client)
    return task.create(title, description)

def task_edit(client, taskid):
    task = Task(client, taskid)
    js = task.get_json('?oslc_cm.properties=dc:identifier,dc:title,dc:description,rtc_cm:ownedBy{dc:title}')
    with tempfile.NamedTemporaryFile(suffix='task') as temp:
        editor = os.environ.get('EDITOR','vim')
        buf = json.dumps(js, indent = 2, separators=(',', ': '))
        temp.write(buf)
        temp.flush()
        subprocess.call([editor, temp.name])
        buf = open(temp.name, 'r').read()
        js = json.loads(buf)
    return task.change(js)

def task_set_owner(client, taskid, owner):
    task = Task(client, taskid)
    users = user_search(client, owner)
    js = { 'rtc_cm:ownedBy': { 'rdf:resource': users['oslc_cm:results'][0]['rdf:resource'] } }
    return task.change(js)

def main():
    conffile = os.environ.get('HOME')+'/.rtctaskrc'
    conf = ConfigParser.RawConfigParser(allow_no_value=True)
    try:
        with open(conffile) as f:
            conf.readfp(f)
    except IOError:
        sample = """[auth]
# Specify your rtc id and password (yes in clear..)
id =
password =
"""
        with open(conffile, "w") as f:
            f.write (sample)
            f.close()
        os.chmod(conffile, 0600)
        print "Config file sample written to "+conffile
    conf.read(conffile)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", help="username id for login", default=conf.get('auth', 'id'))
    parser.add_argument("-s", "--search", help="search pattern", action="store_true")
    parser.add_argument("-c", "--comment", help="additionnal comment")
    parser.add_argument("-e", "--edit", help="edit some field of a task", action="store_true")
    parser.add_argument("-n", "--new", help="title of the new task")
    parser.add_argument("-o", "--owner", help="name, firstname lastname, whatever that can match : 1st result will be used : check with -u")
    parser.add_argument("-d", "--desc", help="description of the new task", default='')
    parser.add_argument("-u", "--user", help="search users for this pattern")
    parser.add_argument("--findquery", help="search queries for this pattern")
    parser.add_argument("-q", "--query", help="run query matching this pattern")
    parser.add_argument("--startworking", help="Change state of task to : In Progress", action="store_true")
    parser.add_argument("--stopworking", help="Change state of task to : New", action="store_true")
    parser.add_argument("--reopen", help="Change state of task to : In Progress", action="store_true")
    parser.add_argument("--invalidate", help="Change state of task to : Invalid", action="store_true")
    parser.add_argument("--resolve", help="Change state of task to : Done", action="store_true")
    parser.add_argument("params", help="List of parameters (task ids, search pattern..)", nargs='*')
    args = parser.parse_args()

    if args.id:
        pw = conf.get('auth', 'password')
        if not pw:
            print "Id      : "+args.id
            pw = getpass.getpass()
        client = RTCClient(args.id, pw)
    else:
        print "Please provide id on command line with --id or in  "+conffile
        sys.exit(1)

    if args.search:
        for s in args.params:
            task_search(client, s)
    elif args.findquery:
        print_queries(client, args.findquery)
    elif args.query:
        task_fromquery(client, args.query)
    elif args.user:
        print_users(client, args.user)
    elif args.owner:
        for s in args.params:
            task_set_owner(client, s, args.owner)
    elif args.edit:
        for s in args.params:
            task_edit(client, s)
    elif args.startworking:
        for s in args.params:
            Task(client, s).startWorking()
    elif args.stopworking:
        for s in args.params:
            Task(client, s).stopWorking()
    elif args.reopen:
        for s in args.params:
            r = Task(client, s).reopen()
    elif args.invalidate:
        for s in args.params:
            Task(client, s).invalidate()
    elif args.resolve:
        for s in args.params:
            Task(client, s).resolve()
    elif args.new:
        task_create(client, args.new, args.desc)
    elif args.comment:
        for t in args.params:
            task_comment(client, t, args.comment)
    elif len(args.params) == 0:
        task_ownedbyme(client)
    else: # there are some parameters provided without options
        for t in args.params:
            task_details(client, t)

    sys.exit(0)

if __name__ == "__main__": main()
