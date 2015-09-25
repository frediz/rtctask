#!/usr/bin/env python
# frediz@linux.vnet.ibm.com

import requests
import warnings
import json
import pprint
import re
import os, sys
import select
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
    colorize = True
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    # return colorized string
    @classmethod
    def str(cls, string, color):
        if cl.colorize:
            return color+string+cl.reset
        return string
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
        try:
            json.loads(r.text)
        except:
            print "Authentication failed."
            sys.exit(1)
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


class Workitem(object):
    def getStateColor(self):
        #should be implemented else :
        return cl.reverse
    def stateColorize(self, string):
        return cl.str(string, self.getStateColor())

    @classmethod
    def __createItem(c, client, json):
        for cls in Workitem.__subclasses__():
            if json['dc:type']['rdf:resource'] == cls.TYPE:
                return cls(client, json['dc:identifier'], json)
        raise ValueError

    @classmethod
    def getOne(cls, client, workitemid, json_query = ""):
        r = client.sget('oslc/workitems/'+ str(workitemid) +'.json'+json_query)
        return Workitem.__createItem(client, json.loads(r.text))

    @classmethod
    def getList(cls, client, json_query = ""):
        r = client.sget(json_query)
        workitems = json.loads(r.text)['oslc_cm:results']
        return map(lambda x: Workitem.__createItem(client, x), workitems)

    @classmethod
    def createOne(cls, client, title, description, witype, owner = None):
        js = {
                'dc:description': description,
                'dc:title': title,
                'dc:type': { 'rdf:resource': witype },
                'rtc_cm:filedAgainst': { 'rdf:resource': RTCClient.HOST + 'resource/itemOid/com.ibm.team.workitem.Category/%s'%(client.category) },
             }
        if owner is not None:
            js['rtc_cm:ownedBy'] = owner
        r = client.spost('oslc/contexts/'+ RTCClient.PROJECT+'/workitems', json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});
        return Workitem.__createItem(client, json.loads(r.text))

    def __init__(self, jclient, workitemid = None, json = {}):
        self.jclient = jclient
        self.workitemid = workitemid
        self.js = json

    def get_comments(self):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'/rtc_cm:comments.json?oslc_cm.properties=dc:created,dc:description,dc:creator{dc:title}')
        return json.loads(r.text)

    def add_comment(self, comment):
        return self.jclient.spost('oslc/workitems/'+ str(self.workitemid) +'/rtc_cm:comments', json={'dc:description':comment}, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def change(self, js):
        return self.jclient.spatch('oslc/workitems/'+ str(self.workitemid), json=js, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'});

    def startWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state']['rdf:resource'] = self.INPROGRESS
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.startWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def stopWorking(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state']['rdf:resource'] = self.NEW
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.stopWorking', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def reopen(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        if r['rtc_cm:state']['rdf:resource'] == self.INVALID:
            r['rtc_cm:state']['rdf:resource'] = self.NEW
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.reopen', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})
        elif r['rtc_cm:state']['rdf:resource'] == self.DONE:
            r['rtc_cm:state']['rdf:resource'] = self.INPROGRESS
            return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a1', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def invalidate(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state']['rdf:resource'] = self.INVALID
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.a2', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def resolve(self):
        r = self.get_json('?oslc_cm.properties=rtc_cm:state{rdf:resource}')
        r['rtc_cm:state']['rdf:resource'] = self.DONE
        return self.jclient.sput('resource/itemName/com.ibm.team.workitem.WorkItem/'+ str(self.workitemid)+'?_action=com.ibm.team.workitem.taskWorkflow.action.resolve', json=r, headers={'Content-Type': 'application/x-oslc-cm-change-request+json', 'Accept': 'text/json'})

    def get_json(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'.json'+args)
        return json.loads(r.text)
    def get_xml(self, args = ""):
        r = self.jclient.sget('oslc/workitems/'+ str(self.workitemid) +'.xml'+args)
        return r.text

class Task(Workitem):
    TYPE = RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/task'

    NEW = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/1'
    INPROGRESS = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/2'
    DONE = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/3'
    INVALID = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.taskWorkflow/com.ibm.team.workitem.taskWorkflow.state.s4'

    def getStateColor(self):
        state = self.js['rtc_cm:state']['rdf:resource']
        if state == self.NEW:
            return cl.fg.purple
        elif state == self.INPROGRESS:
            return cl.fg.lightred
        elif state == self.INVALID:
            return cl.fg.lightgrey
        elif state == self.DONE:
            return cl.fg.green

class Story(Workitem):
    TYPE = RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/com.ibm.team.apt.workItemType.story'

    NEW = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.idea'
    IMPLEMENTED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.tested'
    INPROGRESS = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.defined'
    DONE = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.story.verified'
    INVALID = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.storyWorkflow.state.s2'
    DEFERRED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.storyWorkflow/com.ibm.team.apt.storyWorkflow.state.s1'

    def getStateColor(self):
        state = self.js['rtc_cm:state']['rdf:resource']
        if state == self.NEW:
            return cl.fg.purple
        elif state == self.INPROGRESS:
            return cl.fg.lightred
        elif state == self.IMPLEMENTED:
            return cl.fg.lightred
        elif state == self.INVALID:
            return cl.fg.lightgrey
        elif state == self.DONE:
            return cl.fg.green
        elif state == self.DEFERRED:
            return cl.fg.yellow


class Epic(Workitem):
    TYPE = RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/com.ibm.team.apt.workItemType.epic'

    NEW = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s1'
    INPROGRESS = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s2'
    DONE = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s3'
    INVALID = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s6'
    DEFERRED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.apt.epic.workflow/com.ibm.team.apt.epic.workflow.state.s5'

    def getStateColor(self):
        state = self.js['rtc_cm:state']['rdf:resource']
        if state == self.NEW:
            return cl.fg.purple
        elif state == self.INPROGRESS:
            return cl.fg.lightred
        elif state == self.INVALID:
            return cl.fg.lightgrey
        elif state == self.DONE:
            return cl.fg.green
        elif state == self.DEFERRED:
            return cl.fg.yellow

class Defect(Workitem):
    TYPE = RTCClient.HOST+'oslc/types/'+RTCClient.PROJECT+'/defect'

    NEW = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.defectWorkflow/1'
    INPROGRESS = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.defectWorkflow/2'
    REOPENED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.defectWorkflow/6'
    RESOLVED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.defectWorkflow/3'
    VERIFIED = RTCClient.HOST+'oslc/workflows/'+RTCClient.PROJECT+'/states/com.ibm.team.workitem.defectWorkflow/4'

    def getStateColor(self):
        state = self.js['rtc_cm:state']['rdf:resource']
        if state == self.NEW:
            return cl.fg.purple
        elif state == self.INPROGRESS:
            return cl.fg.lightred
        elif state == self.REOPENED:
            return cl.fg.cyan
        elif state == self.RESOLVED:
            return cl.fg.lightred
        elif state == self.VERIFIED:
            return cl.fg.green


def user_search(client, pattern):
    r = client.sget('oslc/users.json?oslc_cm.query=dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def query_search(client, pattern):
    r = client.sget('oslc/queries.json?oslc_cm.query=rtc_cm:projectArea="'+RTCClient.PROJECT+'" and dc:creator="{currentUser}" and dc:title="*'+pattern+'*"')
    return json.loads(r.text)

def print_queries(client, pattern):
    print
    print "Queries matching : "+cl.str(pattern, cl.fg.blue)
    print " Created                 | Name                             | Description"
    print "===================================================================================="
    for u in query_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + cl.str(u['dc:title'].ljust(32), cl.fg.green) +" | "+u['dc:description']

def print_users(client, pattern):
    print
    print "Users matching : "+cl.str(pattern, cl.fg.blue)
    print " Created                 | Name                             | Email"
    print "===================================================================================="
    for u in user_search(client, pattern)['oslc_cm:results']:
        print u['dc:modified'] + " | " + cl.str(u['dc:title'].ljust(32), cl.fg.green) +" | "+re.sub(r'mailto:([^%]+)%40(.*)',r'\1@\2',u['rtc_cm:emailAddress'])


def workitem_fromquery(client, query_str, isname = True, longdisplay = False, maxtitlelen = 80):
    fields = 'oslc_cm.properties=dc:creator{dc:title},dc:type,rtc_cm:state,dc:identifier,dc:title,dc:modified,rtc_cm:ownedBy{dc:title}'
    if isname:
        query = query_search(client, query_str)['oslc_cm:results'][0]
        queryid = re.sub(r'.*/([^/]+)',r'\1',query['rdf:resource'])
        workitems = Workitem.getList(client, 'oslc/queries/'+queryid+'/rtc_cm:results.json?'+fields)
        print
        print "Workitems for query : "+cl.str(query['dc:title'], cl.fg.blue)
    else:
        workitems = Workitem.getList(client, 'oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query='+query_str+'&'+fields)
        print
        print "Workitems for query : "+cl.str(query_str, cl.fg.blue)
    maxlentitle = max([len(w.js['dc:title']) for w in workitems])
    if maxlentitle > maxtitlelen:
        maxlentitle = maxtitlelen
    legend = "  ID  | "+"Title".ljust(maxlentitle, ' ') +" | Modified"
    if longdisplay:
        maxlencreator = max([len(w.js['dc:creator']['dc:title']) for w in workitems])
        maxlenowner = max([len(w.js['rtc_cm:ownedBy']['dc:title']) for w in workitems])
        legend = legend + "            | "+"Creator".ljust(maxlencreator, ' ')+" | "+"Owner".ljust(maxlenowner, ' ')
    print legend
    separator = "========"+"".ljust(maxlentitle, '=')+"======================"
    if longdisplay:
        separator = separator + "======" + "".ljust(maxlencreator+maxlenowner, '=')
    print separator
    for w in workitems:
        line = w.stateColorize(str(w.js['dc:identifier'])) +" | "+w.js['dc:title'].ljust(maxlentitle,' ')[:maxtitlelen]+ " | "+re.sub(r'([^T]+)T([^\.]+).*',r'\1 \2',w.js['dc:modified'])
        if longdisplay:
            line = line + " | " + w.js['dc:creator']['dc:title'].ljust(maxlencreator,' ') + " | " + w.js['rtc_cm:ownedBy']['dc:title'].ljust(maxlenowner,' ')
        print line

def workitem_bytag(client, tag):
    workitems = Workitem.getList(client, 'oslc/contexts/'+RTCClient.PROJECT+'/workitems.json?oslc_cm.query=oslc_cm:searchTerms="'+tag+'"')
    print
    print "workitems matching : "+cl.str(tag, cl.fg.blue)
    print "  ID  | Title"
    print "=================================================================="
    for w in workitems:
        print w.stateColorize(str(w.js['dc:identifier'])) + " | " + w.js['dc:title']

def workitem_details(client, workitemid):
    wi = Workitem.getOne(client, workitemid, '?oslc_cm.properties=dc:identifier,\
        dc:type{dc:title},dc:title,rdf:resource,dc:creator{dc:title},\
        rtc_cm:ownedBy{dc:title},dc:description,rtc_cm:state{dc:title},\
        rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent{dc:identifier,dc:title},\
        rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.children,\
        rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related')
    print
    print "=================================================================="
    print "Workitem ID : " +cl.str(str(wi.js['dc:identifier']), cl.fg.green)+' ('+wi.js['dc:type']['dc:title']+')'
    print "Title       : " +cl.str(wi.js['dc:title'], cl.fg.red)
    print "URL         : " +wi.js['rdf:resource']
    print "State       : " +wi.stateColorize(wi.js['rtc_cm:state']['dc:title'])
    print "Creator     : " +wi.js['dc:creator']['dc:title']
    print "Owner       : " +wi.js['rtc_cm:ownedBy']['dc:title']
    if len(wi.js['rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent']) != 0:
        par = wi.js['rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent'][0]
        print "Parent      : " + str(par['dc:identifier'])+" ("+par['dc:title']+")"
    if len(wi.js['rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.children']) != 0:
        print "Child(ren)  : " + reduce((lambda a, b: a +", "+ b), map((lambda a: re.sub(r'([^:]+): (.*)', r'\1 (\2)', a['oslc_cm:label'])), wi.js['rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.children']))
    if len(wi.js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related']) != 0:
        print "Related     : " + reduce((lambda a, b: a +", "+ b), map((lambda a: re.sub(r'([^:]+): (.*)', r'\1 (\2)', a['oslc_cm:label'])), wi.js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related']))
    print "Description :"
    print html2text.html2text(wi.js['dc:description'])
    comments = wi.get_comments()
    if len(comments) == 0:
        return
    print "Comments :"
    i = 0
    for c in comments:
        print str(i) + ": " +cl.str(c['dc:creator']['dc:title'], cl.fg.green)+" ("+c['dc:created'] + ") :"
        print html2text.html2text(c['dc:description'])
        i = i + 1

def workitem_comment(client, workitemid, comment):
    workitem = Workitem.getOne(client, workitemid)
    return workitem.add_comment(comment)

def workitem_create(client, title, description):
    return Workitem.createOne(client, title, description, Task.TYPE)

def workitem_edit(client, workitemid):
    workitem = Workitem.getOne(client, workitemid, '?oslc_cm.properties=dc:identifier,dc:type,dc:title,dc:description,rtc_cm:ownedBy{dc:title}')
    with tempfile.NamedTemporaryFile(suffix='workitem') as temp:
        editor = os.environ.get('EDITOR','vim')
        buf = json.dumps(workitem.js, indent = 2, separators=(',', ': '))
        temp.write(buf)
        temp.flush()
        subprocess.call([editor, temp.name])
        buf = open(temp.name, 'r').read()
        js = json.loads(buf)
    return workitem.change(js)

def workitem_set_parent(client, workitemid, parentid):
    workitem = Workitem.getOne(client, workitemid)
    if parentid is None:
        js = { 'rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent': [] }
    else:
        parent = Workitem.getOne(client, parentid)
        js = { 'rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent': [{ 'rdf:resource': parent.js['rdf:resource']}] }
    return workitem.change(js)

def workitem_add_related(client, workitemid, relatedid):
    workitem = Workitem.getOne(client, workitemid)
    related = Workitem.getOne(client, relatedid)
    js = { 'rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related': [{ 'rdf:resource': related.js['rdf:resource'], 'oslc_cm:label': str(relatedid)+': '+related.js['dc:title']}] }
    for e in workitem.js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related']:
        js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related'].append(e)
    return workitem.change(js)

def workitem_remove_related(client, workitemid, relatedid):
    workitem = Workitem.getOne(client, workitemid)
    related = Workitem.getOne(client, relatedid)
    js = { 'rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related': [] }
    for e in workitem.js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related']:
        if e['rdf:resource'] == related.js['rdf:resource']:
            continue
        js['rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem.related'].append({ 'rdf:resource': e['rdf:resource']})
    return workitem.change(js)

def workitem_set_owner(client, workitemid, owner):
    workitem = Workitem.getOne(client, workitemid)
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
[display]
maxtitlelen =
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
    parser.add_argument("-e", "--edit", help="edit some field of a workitem", action="store_true")
    parser.add_argument("-l", "--long", help="activate long display for workitem queries and search", action="store_true")
    parser.add_argument("-n", "--new", help="title of the new workitem")
    parser.add_argument("-o", "--owner", help="name, firstname lastname, whatever that can match : 1st result will be used : check with -u")
    parser.add_argument("-p", "--parent", help="set option parameter to parent of the argument given")
    parser.add_argument("--orphan", help="remove the parent of the workitem", action="store_true")
    parser.add_argument("--related", help="add option parameter to related of the argument given")
    parser.add_argument("--removerelated", help="remove option parameter from related of the argument given")
    parser.add_argument("-d", "--desc", help="description of the new workitem", default='')
    parser.add_argument("-u", "--user", help="search users for this pattern")
    parser.add_argument("--nocolor", help="turn off color in output", action="store_true")
    parser.add_argument("--findquery", help="search queries for this pattern")
    parser.add_argument("-q", "--query", help="run query matching this pattern")
    parser.add_argument("--startworking", help="change state of workitem to : In Progress", action="store_true")
    parser.add_argument("--stopworking", help="change state of workitem to : New", action="store_true")
    parser.add_argument("--reopen", help="change state of workitem to : In Progress", action="store_true")
    parser.add_argument("--invalidate", help="change state of workitem to : Invalid", action="store_true")
    parser.add_argument("--resolve", help="change state of workitem to : Done", action="store_true")
    parser.add_argument("params", help="list of parameters (workitem ids, search pattern..)", nargs='*')
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

    maxtitlelen = int(conf.get('display', 'maxtitlelen'))
    if not maxtitlelen:
        maxtitlelen = 80

    if args.nocolor:
        cl.colorize = False

    if args.search:
        for s in args.params:
            workitem_fromquery(client, 'oslc_cm:searchTerms="'+s+'"', False, args.long, maxtitlelen)
    elif args.orphan:
        for s in args.params:
            workitem_set_parent(client, s, None)
    elif args.parent:
        for s in args.params:
            workitem_set_parent(client, s, args.parent)
    elif args.related:
        for s in args.params:
            workitem_add_related(client, s, args.related)
    elif args.removerelated:
        for s in args.params:
            workitem_remove_related(client, s, args.removerelated)
    elif args.findquery:
        print_queries(client, args.findquery)
    elif args.query:
            workitem_fromquery(client, args.query, True, args.long, maxtitlelen)
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
            Workitem.getOne(client, s).startWorking()
    elif args.stopworking:
        for s in args.params:
            Workitem.getOne(client, s).stopWorking()
    elif args.reopen:
        for s in args.params:
            Workitem.getOne(client, s).reopen()
    elif args.invalidate:
        for s in args.params:
            Workitem.getOne(client, s).invalidate()
    elif args.resolve:
        for s in args.params:
            Workitem.getOne(client, s).resolve()
    elif args.new:
        workitem_create(client, args.new, args.desc)
    elif args.comment:
        if select.select([sys.stdin,],[],[],0.0)[0]:
            comment = ""
            for line in sys.stdin:
                comment += line
            comment = comment.strip()
            workitem_comment(client, args.comment, comment)
        else:
            comment = args.comment
        for s in args.params:
            workitem_comment(client, s, comment)
    elif len(args.params) == 0:
        query = conf.get('query', 'default')
        if query:
            workitem_fromquery(client, query, True, args.long, maxtitlelen)
        else:
            workitem_fromquery(client, 'rtc_cm:ownedBy="{currentUser}" /sort=rtc_cm:state', False, args.long, maxtitlelen)
    else: # there are some parameters provided without options
        for s in args.params:
            workitem_details(client, s)

    sys.exit(0)

if __name__ == "__main__": main()
