#!/usr/bin/env python
# frediz@linux.vnet.ibm.com

import requests
import warnings
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
    colorize = 1
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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
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


class Workitem():
    class Type:
        TASK  = {u'rdf:resource': RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/task'}
        STORY = {u'rdf:resource': RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/com.ibm.team.apt.workItemType.story'}
        EPIC  = {u'rdf:resource': RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/com.ibm.team.apt.workItemType.epic'}
    class Status:
        NEW = [
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/1'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s1'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.idea'},
            ]
        INPROGRESS = [
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/2'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s2'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.defined'},
            ]
        DONE = [
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/3'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s3'},
            {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.verified'},
            ]
        INVALID = [ {u'rdf:resource': RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/com.ibm.team.workitem.taskWorkflow.state.s4'},
            ]

    @classmethod
    def getStateColor(cls, state):
        if state in Workitem.Status.NEW:
            return cl.fg.purple
        elif state in Workitem.Status.INPROGRESS:
            return cl.fg.lightred
        elif state in Workitem.Status.INVALID:
            return cl.fg.lightgrey
        elif state in Workitem.Status.DONE:
            return cl.fg.green

    def __init__(self, jclient, workitemid = None):
        self.jclient = jclient
        self.workitemid = workitemid

    def create(self, title, description, witype, owner = None):
        js = {
                'dc:description': description,
                'dc:title': title,
                'dc:type': witype,
                'rtc_cm:filedAgainst': { 'rdf:resource': RTCClient.HOST + 'resource/itemOid/com.ibm.team.workitem.Category/%s'%(self.jclient.category) },
             }
        if owner is not None:
            js['rtc_cm:ownedBy'] = owner
        return self.jclient.spost('oslc/contexts/'+ RTCClient.PROJECT+'/workitems', json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def get_comments(self):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'/rtc_cm:comments.json?oslc_cm.properties=dc:created,dc:description,dc:creator{dc:title}')
        return json.loads(r.text)

    def add_comment(self, comment):
        return self.jclient.spost('oslc/workitems/'+ str(self.workitemid) +'/rtc_cm:comments', json={'dc:description':comment}, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def change(self, js):
        return self.jclient.spatch('oslc/workitems/'+ str(self.workitemid), json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def startWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.INPROGRESS
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.startWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def stopWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.NEW
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.stopWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def reopen(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        if r['rtc_cm:state'] == Task.INVALID:
            r['rtc_cm:state'] = Task.NEW
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.reopen', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})
        elif r['rtc_cm:state'] == Task.DONE:
            r['rtc_cm:state'] = Task.INPROGRESS
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a1', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def invalidate(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.INVALID
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a2', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def resolve(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state'] = Task.DONE
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.resolve', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def get_json(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'.json'+args)
        return json.loads(r.text)
    def get_xml(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'.xml'+args)
        return r.text


# Misc functions to do option's work
def colorize_str(string, color):
    if cl.colorize:
        return color+string+cl.reset
    return string

def user_search(client, pattern):
    r = client.sget('oslc/users.json?oslc_cm.query=dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def query_search(client, pattern):
    r = client.sget('oslc/queries.json?oslc_cm.query=rtc_cm:projectArea="'+RTCClient.PROJECT+'" and dc:creator="{currentUser}" and dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def print_queries(client, pattern):
    print
    print "Queries matching : "+colorize_str(pattern, cl.fg.blue)
    print " Created                 | Name                             | Description"
    print "===================================================================================="
    for u in query_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + colorize_str(u['dc:title'].ljust(32), cl.fg.green) +" | "+u['dc:description']

def print_users(client, pattern):
    print
    print "Users matching : "+colorize_str(pattern, cl.fg.blue)
    print " Created                 | Name                             | Email"
    print "===================================================================================="
    for u in user_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + colorize_str(u['dc:title'].ljust(32), cl.fg.green) +" | "+re.sub(r'mailto:([^%]+)%40(.*)',r'\1@\2',u['rtc_cm:emailAddress'])


def workitem_fromquery(client, pattern):
    query = re.sub(r'.*/([^/]+)',r'\1',query_search(client, pattern)['oslc_cm:results'][0]['rdf:resource'])
    r = client.sget('oslc/queries/'+query+'/rtc_cm:results.json')
    workitems = json.loads(r.text)
    maxlen = max([len(w['dc:title']) for w in workitems])
    print "  ID  | "+"Title".ljust(maxlen, ' ') +" | Modified"
    print "========"+"".ljust(maxlen, '=')+"======================"
    for w in workitems:
        print colorize_str(str(w['dc:identifier']), Workitem.getStateColor(w['rtc_cm:state'])) +" | "+w['dc:title'].ljust(maxlen,' ')+ " | "+re.sub(r'([^T]+)T([^\.]+).*',r'\1 \2',w['dc:modified'])

def workitem_ownedbyme(client):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=rtc_cm:ownedBy="{currentUser}" /sort=rtc_cm:state')
    workitems = json.loads(r.text)
    print "  ID  | Title"
    print "=================================================================="
    for w in workitems['oslc_cm:results']:
        print colorize_str(str(w['dc:identifier']), Workitem.getStateColor(w['rtc_cm:state'])) + " | " + w['dc:title']

def workitem_search(client, pattern):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=oslc_cm:searchTerms="'+pattern+'"')
    workitems = json.loads(r.text)
    print
    print "Workitems matching : "+colorize_str(pattern, cl.fg.blue)
    print "  ID  | Title"
    print "=================================================================="
    for w in workitems['oslc_cm:results']:
        print colorize_str(str(w['dc:identifier']), Workitem.getStateColor(w['rtc_cm:state'])) + " | " + w['dc:title']

def workitem_bytag(client, tag):
    r = client.sget('oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=oslc_cm:searchTerms="'+tag+'"')
    workitems = json.loads(r.text)
    print
    print "workitems matching : "+colorize_str(tag, cl.fg.blue)
    print "  ID  | Title"
    print "=================================================================="
    for w in workitems['oslc_cm:results']:
        print colorize_str(str(w['dc:identifier']), Workitem.getStateColor(w['rtc_cm:state'])) + " | " + w['dc:title']

def workitem_details(client, workitemid):
    workitem = Workitem(client, workitemid)
    js = workitem.get_json('?oslc_cm.properties=dc:identifier,dc:type{dc:title},dc:title,rdf:resource,dc:creator{dc:title},rtc_cm:ownedBy{dc:title},dc:description,rtc_cm:state{dc:title}')
    #js = workitem.get_json()
    #pprint.pprint(js)
    print
    print "=================================================================="
    print "Workitem ID : " +colorize_str(str(js['dc:identifier']), cl.fg.green)+' ('+js['dc:type']['dc:title']+')'
    print "Title       : " +colorize_str(js['dc:title'], cl.fg.red)
    print "URL         : " +js['rdf:resource']
    print "State       : " +colorize_str(js['rtc_cm:state']['dc:title'], Workitem.getStateColor({ u'rdf:resource': js['rtc_cm:state']['rdf:resource']}))
    print "Creator     : " +js['dc:creator']['dc:title']
    print "Owner       : " +js['rtc_cm:ownedBy']['dc:title']
    print "Description :"
    print html2text.html2text(js['dc:description'])
    comments = workitem.get_comments()
    if len(comments) == 0:
        return
    print "Comments :"
    i = 0
    for c in comments:
        print str(i) + ": " +colorize_str(c['dc:creator']['dc:title'], cl.fg.green)+" ("+c['dc:created'] + ") :"
        print html2text.html2text(c['dc:description'])
        i = i + 1

def workitem_comment(client, workitemid, comment):
    workitem = Workitem(client, workitemid)
    return workitem.add_comment(comment)

def workitem_create(client, title, description):
    workitem = Workitem(client)
    return workitem.create(title, description, Workitem.Type.TASK)

def workitem_edit(client, workitemid):
    workitem = Workitem(client, workitemid)
    js = workitem.get_json('?oslc_cm.properties=dc:identifier,dc:title,dc:description,rtc_cm:ownedBy{dc:title}')
    with tempfile.NamedTemporaryFile(suffix='workitem') as temp:
        editor = os.environ.get('EDITOR','vim')
        buf = json.dumps(js, indent = 2, separators=(',', ': '))
        temp.write(buf)
        temp.flush()
        subprocess.call([editor, temp.name])
        buf = open(temp.name, 'r').read()
        js = json.loads(buf)
    return workitem.change(js)

def workitem_set_owner(client, workitemid, owner):
    workitem = Workitem(client, workitemid)
    users = user_search(client, owner)
    js = { 'rtc_cm:ownedBy': { 'rdf:resource': users['oslc_cm:results'][0]['rdf:resource'] } }
    return workitem.change(js)

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
[query]
default =
"""
        with open(conffile, "w") as f:
            f.write (sample)
            f.close()
        os.chmod(conffile, 0600)
        print "Config file sample written to "+conffile
    conf.read(conffile)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", help="username id for login", default=conf.get('auth', 'id'))
    parser.add_argument("--nocolor", help="turn off color in output", action="store_true")
    parser.add_argument("-s", "--search", help="search pattern", action="store_true")
    parser.add_argument("-c", "--comment", help="additionnal comment")
    parser.add_argument("-e", "--edit", help="edit some field of a workitem", action="store_true")
    parser.add_argument("-n", "--new", help="title of the new workitem")
    parser.add_argument("-o", "--owner", help="name, firstname lastname, whatever that can match : 1st result will be used : check with -u")
    parser.add_argument("-d", "--desc", help="description of the new workitem", default='')
    parser.add_argument("-u", "--user", help="search users for this pattern")
    parser.add_argument("--findquery", help="search queries for this pattern")
    parser.add_argument("-q", "--query", help="run query matching this pattern")
    parser.add_argument("--startworking", help="Change state of workitem to : In Progress", action="store_true")
    parser.add_argument("--stopworking", help="Change state of workitem to : New", action="store_true")
    parser.add_argument("--reopen", help="Change state of workitem to : In Progress", action="store_true")
    parser.add_argument("--invalidate", help="Change state of workitem to : Invalid", action="store_true")
    parser.add_argument("--resolve", help="Change state of workitem to : Done", action="store_true")
    parser.add_argument("params", help="List of parameters (workitem ids, search pattern..)", nargs='*')
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

    if args.nocolor:
        cl.colorize = 0

    if args.search:
        for s in args.params:
            workitem_search(client, s)
    elif args.findquery:
        print_queries(client, args.findquery)
    elif args.query:
        workitem_fromquery(client, args.query)
    elif args.user:
        print_users(client, args.user)
    elif args.owner:
        for s in args.params:
            workitem_set_owner(client, s, args.owner)
    elif args.edit:
        for s in args.params:
            workitem_edit(client, s)
    elif args.startworking:
        for s in args.params:
            Workitem(client, s).startWorking()
    elif args.stopworking:
        for s in args.params:
            Workitem(client, s).stopWorking()
    elif args.reopen:
        for s in args.params:
            r = Workitem(client, s).reopen()
    elif args.invalidate:
        for s in args.params:
            Workitem(client, s).invalidate()
    elif args.resolve:
        for s in args.params:
            Workitem(client, s).resolve()
    elif args.new:
        workitem_create(client, args.new, args.desc)
    elif args.comment:
        for s in args.params:
            workitem_comment(client, s, args.comment)
    elif len(args.params) == 0:
        query = conf.get('query', 'default')
        if query:
            workitem_fromquery(client, query)
        else:
            workitem_ownedbyme(client)
    else: # there are some parameters provided without options
        for s in args.params:
            workitem_details(client, s)

    sys.exit(0)

if __name__ == "__main__": main()
