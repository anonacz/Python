from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import urlparse
import cgi
import time
from os import curdir, sep, devnull, setsid
import os
import re
from pymongo import MongoClient
import itertools
import subprocess
import cgitb; cgitb.enable()

HOST_DB = 'localhost'
PORT_DB = 27017

HOST_NAME = 'localhost'
PORT_NUMBER = 8081

prog = re.compile("^/[2-3]$")

import os, base64
def generate_session():
    return base64.b64encode(os.urandom(16))


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        parsed_path = urlparse.urlparse(self.path)

        try:
            parameters = {}
            for couple in parsed_path.query.split('&'):
                k, v = couple.split('=')
                parameters[k] = v

            method = parameters.get('action', 'input')
            picname = parameters.get('filename', 'def')
            if method == 'checkfile':
                file_path = "images/" + picname
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                if os.path.exists(file_path):
                    self.wfile.write("yes")
                else:
                    self.wfile.write("no")
        except:
            message_parts = [
                    'Current_thread=%s' % threading.currentThread().getName(),
                    '',
                    'CLIENT VALUES:',
                    'client_address=%s (%s)' % (self.client_address,
                                                self.address_string()),
                    'command=%s' % self.command,
                    'path=%s' % self.path,
                    'real path=%s' % parsed_path.path,
                    'query=%s' % parsed_path.query,
                    'request_version=%s' % self.request_version,
                    '',
                    'SERVER VALUES:',
                    'server_version=%s' % self.server_version,
                    'sys_version=%s' % self.sys_version,
                    'protocol_version=%s' % self.protocol_version,
                    '',
                    'HEADERS RECEIVED:',
                    ]
            log_parts = {
                    'Current_thread' : threading.currentThread().getName(),
                    'client_address' : self.client_address,
                    'address_string' : self.address_string(),
                    'command' : self.command,
                    'path' : self.path,
                    'real path' : parsed_path.path,
                    'query' : parsed_path.query,
                    'request_version' : self.request_version,
                    'server_version' : self.server_version,
                    'sys_version' : self.sys_version,
                    'protocol_version' : self.protocol_version,
                    }

            for name, value in sorted(self.headers.items()):
                message_parts.append('%s=%s' % (name, value.rstrip()))
                log_parts[name] = value.rstrip()
            message_parts.append('')

            l = MyLogs(log_parts, self.client_address, parsed_path.path)

            message = '\r\n'.join(message_parts)
            c = MyContent(self.path, message)
            c.loadTemplate()
            if c.returncode == 200:
                self.send_response(200)
                self.send_header('Last-Modified',
                        self.date_time_string(time.time()))
                self.send_header('Content-Type', c.mimetype)
                self.end_headers()
                if c.mimetype == 'text/html':
                    l.update()
                    sd = showDatabase("just_ip")
                    ips = sd.show()
                    c.alterTemplate(ips)
                self.wfile.write(c.content)
            elif c.returncode == 404:
                self.send_error(404, c.content)
        return

    def do_POST(self):
        parsed_path = urlparse.urlparse(self.path)
        message_parts = [
                'Current_thread=%s' % threading.currentThread().getName(),
                '',
                'CLIENT VALUES:',
                'client_address=%s (%s)' % (self.client_address,
                                            self.address_string()),
                'command=%s' % self.command,
                'path=%s' % self.path,
                'real path=%s' % parsed_path.path,
                'query=%s' % parsed_path.query,
                'request_version=%s' % self.request_version,
                '',
                'SERVER VALUES:',
                'server_version=%s' % self.server_version,
                'sys_version=%s' % self.sys_version,
                'protocol_version=%s' % self.protocol_version,
                '',
                'HEADERS RECEIVED:',
                ]
        log_parts = {
                'Current_thread' : threading.currentThread().getName(),
                'client_address' : self.client_address,
                'address_string' : self.address_string(),
                'command' : self.command,
                'path' : self.path,
                'real path' : parsed_path.path,
                'query' : parsed_path.query,
                'request_version' : self.request_version,
                'server_version' : self.server_version,
                'sys_version' : self.sys_version,
                'protocol_version' : self.protocol_version,
                }

        for name, value in sorted(self.headers.items()):
            message_parts.append('%s=%s' % (name, value.rstrip()))
            log_parts[name] = value.rstrip()
        message_parts.append('')

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     })
        parameters = {}
        for k in form.keys():
            parameters[str(k)] = form.getvalue(k)
        ip_req = parameters.get('ip', 'all')

        sd = showDatabase(ip_req)
        ips = sd.show()
        sd.generatePDF()



        message = '\r\n'.join(message_parts)
        c = MyContent(self.path, message)
        c.loadTemplate()
        if c.returncode == 200:
            self.send_response(200)
            self.send_header('Last-Modified',
                    self.date_time_string(time.time()))
            self.send_header('Content-Type', c.mimetype)
            self.end_headers()
            if c.mimetype == 'text/html':
                picnote = 'Graph will apear bellow.'
                with open('scripts/myscript.js.base', 'r') as f:
                    f_content = f.read()
                    f_content = f_content.replace("###filename###", "log.png")
                with open('scripts/myscript.js', 'w') as f:
                    f.write(f_content)
                ajax = (
                        '<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.min.js"></script>'
                        '\n<script src="scripts/myscript.js"></script>'
                        )

                c.alterTemplate(ips, "", picnote, ajax, 'log.png')
            self.wfile.write(c.content)
        elif c.returncode == 404:
            self.send_error(404, c.content)

        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class MyContent():

    def __init__(self, path, body):
        self.path = path
        self.body = body
        self.returncode = 0
        self.content = ""
        self.mimetype = ""

    def loadTemplate(self):
        parsed_path = urlparse.urlparse(self.path)
        realpath=self.path
        if parsed_path.path=="/":
            realpath="templates/index.html"
        elif prog.match(parsed_path.path):
            realpath="templates/index.html"
        try:

            sendReply = False
            if realpath.endswith(".html"):
                self.mimetype='text/html'
                sendReply = True
            if realpath.endswith(".jpg"):
                self.mimetype='image/jpg'
                sendReply = True
            if realpath.endswith(".png"):
                self.mimetype='image/png'
                sendReply = True
            if realpath.endswith(".gif"):
                self.mimetype='image/gif'
                sendReply = True
            if realpath.endswith(".js"):
                self.mimetype='application/javascript'
                sendReply = True
            if realpath.endswith(".css"):
                self.mimetype='text/css'
                sendReply = True
            if sendReply:
                f = open(curdir + sep + realpath)
                self.content = f.read()
                f.close()
                self.returncode = 200
            else:
                self.content = 'Page Not Found: %s' % self.path
                self.returncode = 404
        except IOError:
            self.content = 'Page Not Found: %s' % self.path
            self.returncode = 404

    def alterTemplate(self, ips, png='', picnote='', ajax='', fn='log.png'):
        option = ''
        for ip in ips:
            option += '    <option value="{0}">{0}</option>\n'.format(ip)
        self.body = self.body.replace("\n", "<br/ >\n")
        self.content = self.content.replace("###body###", self.body)
        self.content = self.content.replace("###options###", option)
        self.content = self.content.replace("###picture###", png)
        self.content = self.content.replace("###picnote###", picnote)
        self.content = self.content.replace("###ajax###", ajax)
        self.content = self.content.replace("###filename###", fn)

class MyLogs():

    def __init__(self, log_parts, client_address, parsed_path):
        self.log_parts = log_parts
        self.client_address = client_address
        self.parsed_path = parsed_path
        self.returncode = 0
        self.content = ""
        self.mimetype = ""
        self.d = dict()

        client = MongoClient(HOST_DB, PORT_DB, maxPoolSize=None)
        db = client['test-database']
#        # TODO remove from
#        db['test-logs'].drop()
#        db['test-transition'].drop()
#        db['test-changelogs'].drop()
#        # TODO remove to
        self.collection_log = db['test-logs']
        self.collection_changelog = db['test-changelogs']
        self.collection_transition = db['test-transition']

    def update(self):
        self.collection_log.insert_one(self.log_parts)

        try:
            modified = self.log_parts['if-modified-since']
        except KeyError:
            modified = None

        ip = self.client_address[0]

#        # TODO remove from
#        import random
#        r = random.randint(0,9)
#        ip = ip[:-1]+str(r)
#        # TODO remove to

        self.collection_transition.update_one({
                "$and":[
                    {'host' : ip},
                    {'path.'+self.parsed_path : { '$exists': True }}
                ]
            },
            {
                '$set': {
                    'host' : ip,
                    },
                '$inc': {
                    'path.'+self.parsed_path : 1
                    }
            },
                upsert=True
            )

        self.collection_changelog.update_one({
            "$and":[
                {'host' : ip},
                {'changelog' : { '$exists': True }}
                ]
            },
            {
                '$push': {
                    'changelog' : [self.parsed_path, modified]
                    }
            },
                upsert=True
            )

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

class showDatabase():
    def __init__(self, ip_req):
        self.ip_req = ip_req
        client = MongoClient(HOST_DB, PORT_DB, maxPoolSize=None)
        db = client['test-database']
        self.collection_changelog = db['test-changelogs']

    def show(self):
        ips = []
        self.d = {
                (u'/', u'/3') : 0,
                (u'/3', u'/') : 0,
                (u'/2', u'/') : 0,
                (u'/', u'/2') : 0,
                (u'/2', u'/3') : 0,
                (u'/3', u'/2') : 0,
                (u'/', '0') : 0,
                (u'/2', '0') : 0,
                (u'/3', '0') : 0,
                (u'/', u'/') : 0,
                (u'/2', u'/2') : 0,
                (u'/3', u'/3') : 0
        }
        for ip in self.collection_changelog.find():
            ips.append( ip['host'] )
            if self.ip_req == 'all':
                ch = [item[0] for item in ip['changelog']] + ['0']
                pairs = pairwise(ch)
                for pair in pairs:
                    self.d[pair] += 1
            elif self.ip_req == ip['host']:
                ch = [item[0] for item in ip['changelog']] + ['0']
                pairs = pairwise(ch)
                for pair in pairs:
                    self.d[pair] += 1
        return ips

    def generatePDF(self):
        hit_count = 0
        for hit in self.d.values():
            hit_count += hit
        with open('./latex/test.tex', 'r') as f:
            f_content = f.read()
            f_content.replace('###ID1###', str(self.d[(u'/', u'/3')]))
            f_content.replace('###ID2###', str(self.d[(u'/3', u'/')]))
            f_content.replace('###ID3###', str(self.d[(u'/2', u'/')]))
            f_content.replace('###ID4###', str(self.d[(u'/', u'/2')]))
            f_content.replace('###ID5###', str(self.d[(u'/2', u'/3')]))
            f_content.replace('###ID6###', str(self.d[(u'/3', u'/2')]))
            f_content.replace('###ID7###', str(self.d[(u'/', '0')]))
            f_content.replace('###ID8###', str(self.d[(u'/2', '0')]))
            f_content.replace('###ID9###', str(self.d[(u'/3', '0')]))
            f_content.replace('###ID10###', str(self.d[(u'/', u'/')]))
            f_content.replace('###ID11###', str(self.d[(u'/2', u'/2')]))
            f_content.replace('###ID12###', str(self.d[(u'/3', u'/3')]))

        with open('./latex/tmp_test.tex', 'w') as of:
            of.write(f_content)
        fno = open('./pdflatex.out.log', 'w')
        fne = open('./pdflatex.err.log', 'w')
        subprocess.Popen(
                (
                'cd latex && pdflatex tmp_test.tex && convert -density'
                '150 tmp_test.pdf -quality 90 ../images/log.png'
                ), stdout=fno, stderr=fne, shell=True)

if __name__ == '__main__':
    server = ThreadedHTTPServer((HOST_NAME, PORT_NUMBER), Handler)
    print 'Starting server, use <Ctrl-C> to stop: http://%s:%s' % (HOST_NAME,
            PORT_NUMBER)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        server.socket.close()

