import urllib.parse
import re
import os
import brotli
from json import load,dumps
from pprint import pprint
import logging
import sys
import random
import string
import binascii
CONTENT_UNKNOWN =    0
CONTENT_TEXT =       1
CONTENT_JAVASCRIPT = 2
CONTENT_GZIP =       3
CONTENT_URL_ENCODED =4

FILL_BY_GENERATOR = 1
FILL_BY_ENGINE = 2
APPLY_NO_FILL = 3
APPLY_URL_ENCODE = 1
APPLY_BROTLI_ENCODE = 2
print("Adding customized commonLib")
def into_bytes(buff):
    try:
        return buff.encode()
    except AttributeError:
        return buff

def transform_into_hexcode_as_bytes(buffs):
    res = b'0h'
    for buff in buffs:
        res += binascii.hexlify(buff)
    return res

def url_decode(r):
    return (urllib.parse.unquote(r))
def url_encode(r):
    return (urllib.parse.quote(r))
def url_encode_as_bytes(r):
    return (urllib.parse.quote(r)).encode()
def get_method(m):
    return m.split(' ')[0]

def get_content_type(ct):
    j  = ct.split(':')[1]
    for j in ct.split(':')[1].split('/'):
        t = j.strip()
        if 'javascript' in t:
            return CONTENT_JAVASCRIPT
        elif 'urlencoded' in t:
            return CONTENT_URL_ENCODED
    return CONTENT_UNKNOWN

class ReplacePattern:
    def __init__(self, patToReplace, replaceWith, enc):
        self.pat  = patToReplace
        self.replace = replaceWith
        self.replaceEncode = enc

    def get_encoded_replacing_value_as_bytes(self):
        if self.replaceEncode == APPLY_URL_ENCODE:
            return url_encode(self.replace).encode()
        return self.replace.encode()

    def apply_pattern_substitution(self, buff):
        if len(buff) <= 0:
            logging.error(' Applying substitution on 0 lenBuff')
        ucoded = self.get_encoded_replacing_value_as_bytes()
        modified = re.sub(self.pat, ucoded, buff)
        return modified

def read_payload_as_bytes( fname):
    with open(fname, 'rb') as f:
        return f.read()
    return None


class CommonSmartApp:
    def __init__(self , apid, adir, act, trans, scen, attachDir, payload_file):
        self.v = 2
        self.appid = apid
        self.appdir = adir
        self.sendEnc = None
        self.action = act
        self.transaction = trans
        self.scenerio = scen
        self.attachmentDir = attachDir
        self.originalSz = 0
        self.modifiedSz  = 0
        self.fill = None
        self.payload_file = payload_file

        self.payload_bytes = None
        self.hdr = None
        self.body = None
        self.fillable_size = None
        #self.read_payload()

    def set_fill(self, fillDetails):
        self.fill = fillDetails

    def apply_action_modification(self, transType, isreq, params, payl , mslw, musess, sockname):
        h = HttpParserWriter( sockname, isreq, payl, mslw, self.appid, musess,self.sendEnc, self.fill, self.hdr, self.body)
        self.start_smart(isreq, transType, params, payl,h)
        h.apply_http_modification()
        #self.originalSz, self.modifiedSz  = h.get_sizes()
        return h

    def read_payload(self):
        self.payload_bytes = read_payload_as_bytes( self.payload_file)
        self.body = self.payload_bytes
        if self.action['protocol'] == 'http':
            self.hdr, self.body = re.split( b'\r\n\r\n', self.payload_bytes, 1 )
        self.fillablle_size = len(self.body)

    #make all references None
    def clear_buffered_payload(self):
        self.hdr = None
        self.body = None
        self.payload_bytes = None

    def get_fillable_len(self):
        if self.fillable_size is None:
            self.read_payload()
        return self.fillablle_size

    def get_buffered_payload_len( self ):
        if self.payload_bytes is None:
            return 0
        return len( self.payload_bytes)

    def get_modification_size(self):
        return self.action['size']

    def get_msl_variables(self, transType, isreq, params, payl , mslw, musess, sockname):
        rv = ''
        if self.fill and self.fill.fillby == FILL_BY_ENGINE:
            l = self.fill.get_fillparam()
            r = f'{self.fill.get_jsonstr()}'
            rv = f'{l} = {r}'
        return rv

class Scenario:
    def __init__(self, input):
        random.seed(42)
        if type(input) is dict:
            self.json_data = input
            self.full_json_data = self.json_data
        else:
            with open(input, 'r')  as f:
                self.json_data = load(f)
                self.full_json_data = self.json_data
                if 'metadata' in self.json_data and 'scenario' in self.json_data['metadata']:
                    self.json_data = self.json_data['metadata']['scenario']
        self.servers = {}
        self.varnames = []
        self.connids = {}
        #self.hosts = [Host("host_0", "192.168.1.2") ]
        #self.parse_connections()
        self.transactions = []

    def get_hosts(self):
        return self.hosts
    def get_num_servers(self):
        return len(self.servers)
    def get_varnames(self):
        return self.varnames
    def get_transactions(self):
        return self.transactions

    def handle_connid(self, conn):
        cid = conn.get_id()
        if not (cid in self.connids):
            #print(f"creating a new connection id: {cid}")
            connid = ConnID( conn.get_id(), conn )
            self.connids[cid] = connid
            sockname = connid.get_sock_name()
            self.varnames.append(sockname + '_sid')
            self.hosts.append( Host( conn.hostname, None) )
        else:
            connid = self.connids[cid]
            conn.set_sock_name(connid.get_sock_name() )
            #print(f"NOT creating a new connection id: {cid} already present")

    def parse_connections(self):
        conns = self.json_data['connections']
        for i,c in enumerate(conns):
            conn = Connection(c,i)
            self.servers[ c['server'] ] = conn
            self.handle_connid( conn)

class HttpParserWriter:
    def __init__(self, sockname, isreq, fname, writer, action_count, musess,enc, fill, hdr=None, body=None):
        self.maxsz = 65535
        self.sockname = sockname
        self.isreq = isreq
        self.filename = fname
        self.writer = writer
        self.action_count = action_count
        self.musess = musess
        self.sendEnc = enc
        self.mslVars = []

        #self.payl = read_payload_as_bytes( fname)
        self.hdrMods = []
        self.bodyMods = []
        self.bodyEnc =  None
        self.hexEnc = True
        self.fill = fill

        self.modidied_size = 0
        self.body = None
        self.body_present = False
        self.body_len = 0
        self.set_content_len = False

        self.original_hdr, self.original_body = hdr, body
        if hdr == None:
            self.payload_bytes = read_payload_as_bytes( self.filename)
            self.original_hdr, self.original_body = re.split( b'\r\n\r\n', self.payload_bytes, 1 )
        self.original_size = len( self.original_hdr) +  4 + len( self.original_body )


    def get_original_body_len(self):
        return len(self.original_body)

    """
        continous: (Always calculate and populate actual length)
            engine filling:
            no engine filling
        non-continous:
            engine filling:
            no engine filling: [only time we need to leave content-len to engine is]

    """
    def add_hdrmod(self, hm):
        self.hdrMods.append( hm )

    def add_bodymod(self, bm):
        self.bodyMods.append( bm )

    def add_header_sub(self, repPat, repVal, enc):
        self.add_hdrmod( ReplacePattern(repPat, repVal, enc) )

    def add_body_sub(self, repPat, repVal, enc):
        self.add_bodymod( ReplacePattern(repPat, repVal, enc) )

    def apply_body_modification(self, body):
        if len(body) <= 0:
            if len(self.bodyMods) > 0:
                print("Attempting to apply modification on emptyBody")
            return None
        for bm in self.bodyMods:
            body = bm.apply_pattern_substitution( body)
        if self.bodyEnc == APPLY_BROTLI_ENCODE:
            return brotli.compress(body)
        return body

    def apply_http_header_modification(self, hdr):
        for hm in self.hdrMods:
            hdr = hm.apply_pattern_substitution( hdr )
        return hdr

    def write_the_payload( self, fname ):
        if self.body is None or len(self.body) <= 0:
            buff = self.hdr + b'\r\n\r\n'
        else:
            buff = self.hdr + b'\r\n\r\n' + self.body
        with open(fname, 'wb') as f:
            f.write(buff)

    def apply_http_modification(self):
        hdr, body = self.original_hdr, self.original_body
        self.hdr = self.apply_http_header_modification( hdr)

        if len(body) <= 0:
            return self.hdr

        self.body_present = True

        self.body = self.apply_body_modification( body )
        self.body_len = len(self.body)


        modified = self.hdr  + self.body
        return modified



class RawParserWriter:
    def __init__(self, sockname, isreq, fname, writer, action_count, musess,enc, fill, payload_bytes):
        self.maxsz = 65535
        self.sockname = sockname
        self.isreq = isreq
        self.filename = fname
        self.writer = writer
        self.action_count = action_count
        self.musess = musess
        self.sendEnc = enc
        self.mslVars = []
        self.subs = []

        self.payl = payload_bytes
        if self.payl is None:
            self.payl = read_payload_as_bytes( self.filename)
        self.hexEnc = True
        self.fill = fill

        self.original_size = len(self.payl)
        self.modidied_size = 0

    def get_original_body_len(self):
        return self.original_size

    def set_application(self,application):
        self.app = app
    def set_app_transport(self, transp):
        self.transport = transp

    def add_pattern_substitution( self,pat, username):
        self.subs.append( ReplacePattern(pat, username, APPLY_URL_ENCODE) )

    def set_parsed(self, rawpayl):
        self.payl = rawpayl

    def get_payload(self):
        return self.payl

    def apply_all_raw_modifications(self):
        self.payl = self.apply_raw_pattern_modification(self.payl)
        self.modidied_size = len(self.payl)
        return self.payl

    def apply_raw_pattern_modification(self, rawpayl):
        modified = rawpayl
        for hm in self.subs:
            modified = hm.apply_pattern_substitution( modified )
        return modified

    def get_modified_size(self):
        return self.modidied_size

    def write_the_payload( self, fname ):
        buff = self.payl
        with open(fname, 'wb') as f:
            f.write(buff)
