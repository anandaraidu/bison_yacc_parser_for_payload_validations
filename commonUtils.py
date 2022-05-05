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
CONTENT_REGEX = re.compile(b"Content-Length: \d+\\r\\n")
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
        self.body_changed = False

        self.original_hdr, self.original_body = hdr, body
        if hdr == None:
            self.payload_bytes = read_payload_as_bytes( self.filename)
            self.original_hdr, self.original_body = re.split( b'\r\n\r\n', self.payload_bytes, 1 )
        self.original_size = len( self.original_hdr) +  4 + len( self.original_body )


    def set_parsed_and_apply_fill_hex_encodings(self, hdr, body):
        self.hdr = hdr
        self.body =  body
        if len(body) > 0:
            self.body_present = True
            self.body_len = len(self.body)
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
            self.body_changed = True
        if self.bodyEnc == APPLY_BROTLI_ENCODE:
            return brotli.compress(body)
        return body

    def apply_http_header_modification(self, hdr):
        for hm in self.hdrMods:
            hdr = hm.apply_pattern_substitution( hdr )
        return hdr
    def get_sizes(self):
        return self.original_size, len(self.hdr) + 4 + self.body_len
    def write_the_payload_unused( self, fname ):
        self.hdr = self.hdr + b'\r\n\r\n'
        if self.body_changed:
            bodylen = len(self.body)
            line = f'Content-Length: {str(bodylen)}\r\n'.encode()
            #print(f"MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM {self.filename} {bodylen} {line}")
            self.hdr = CONTENT_REGEX.sub(line, self.hdr)
        if self.body is None or len(self.body) <= 0:
            buff = self.hdr 
        else:
            buff = self.hdr + self.body
        with open(fname, 'wb') as f:
            f.write(buff)

    #only write body we only want to diff body
    def write_the_payload( self, fname ):
        if self.body is None or len(self.body) <= 0:
            buff = self.hdr + b'\r\n\r\n'
        else:
            buff = self.body
        with open(fname, 'wb') as f:
            f.write( buff)

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

    def get_sizes(self):
        return self.original_size, self.modidied_size
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
def get_filetype(file_name):
    fext = file_name.split(".")
    # print (fext[-1])
    filetype = {
    "evy":"application/envoy",
    "fif":"application/fractals",
    "spl":"application/futuresplash",
    "hta":"application/hta",
    "acx":"application/internet-property-stream",
    "hqx":"application/mac-binhex40",
    "doc":"application/msword",
    "dot":"application/msword",
    "bin":"application/octet-stream",
    "class":"application/octet-stream",
    "dms":"application/octet-stream",
    "exe":"application/octet-stream",
    "lha":"application/octet-stream",
    "lzh":"application/octet-stream",
    "oda":"application/oda",
    "axs":"application/olescript",
    "pdf":"application/pdf",
    "prf":"application/pics-rules",
    "p10":"application/pkcs10",
    "crl":"application/pkix-crl",
    "ai":"application/postscript",
    "eps":"application/postscript",
    "ps":"application/postscript",
    "rtf":"application/rtf",
    "setpay":"application/set-payment-initiation",
    "setreg":"application/set-registration-initiation",
    "xla":"application/vnd.ms-excel",
    "xlc":"application/vnd.ms-excel",
    "xlm":"application/vnd.ms-excel",
    "xls":"application/vnd.ms-excel",
    "xlt":"application/vnd.ms-excel",
    "xlw":"application/vnd.ms-excel",
    "msg":"application/vnd.ms-outlook",
    "sst":"application/vnd.ms-pkicertstore",
    "cat":"application/vnd.ms-pkiseccat",
    "stl":"application/vnd.ms-pkistl",
    "pot":"application/vnd.ms-powerpoint",
    "pps":"application/vnd.ms-powerpoint",
    "ppt":"application/vnd.ms-powerpoint",
    "mpp":"application/vnd.ms-project",
    "wcm":"application/vnd.ms-works",
    "wdb":"application/vnd.ms-works",
    "wks":"application/vnd.ms-works",
    "wps":"application/vnd.ms-works",
    "hlp":"application/winhlp",
    "bcpio":"application/x-bcpio",
    "cdf":"application/x-cdf",
    "z":"application/x-compress",
    "tgz":"application/x-compressed",
    "cpio":"application/x-cpio",
    "csh":"application/x-csh",
    "dcr":"application/x-director",
    "dir":"application/x-director",
    "dxr":"application/x-director",
    "dvi":"application/x-dvi",
    "gtar":"application/x-gtar",
    "gz":"application/x-gzip",
    "hdf":"application/x-hdf",
    "ins":"application/x-internet-signup",
    "isp":"application/x-internet-signup",
    "iii":"application/x-iphone",
    "js":"application/x-javascript",
    "latex":"application/x-latex",
    "mdb":"application/x-msaccess",
    "crd":"application/x-mscardfile",
    "clp":"application/x-msclip",
    "dll":"application/x-msdownload",
    "m13":"application/x-msmediaview",
    "m14":"application/x-msmediaview",
    "mvb":"application/x-msmediaview",
    "wmf":"application/x-msmetafile",
    "mny":"application/x-msmoney",
    "pub":"application/x-mspublisher",
    "scd":"application/x-msschedule",
    "trm":"application/x-msterminal",
    "wri":"application/x-mswrite",
    "cdf":"application/x-netcdf",
    "nc":"application/x-netcdf",
    "pma":"application/x-perfmon",
    "pmc":"application/x-perfmon",
    "pml":"application/x-perfmon",
    "pmr":"application/x-perfmon",
    "pmw":"application/x-perfmon",
    "p12":"application/x-pkcs12",
    "pfx":"application/x-pkcs12",
    "p7b":"application/x-pkcs7-certificates",
    "spc":"application/x-pkcs7-certificates",
    "p7r":"application/x-pkcs7-certreqresp",
    "p7c":"application/x-pkcs7-mime",
    "p7m":"application/x-pkcs7-mime",
    "p7s":"application/x-pkcs7-signature",
    "sh":"application/x-sh",
    "shar":"application/x-shar",
    "swf":"application/x-shockwave-flash",
    "sit":"application/x-stuffit",
    "sv4cpio":"application/x-sv4cpio",
    "sv4crc":"application/x-sv4crc",
    "tar":"application/x-tar",
    "tcl":"application/x-tcl",
    "tex":"application/x-tex",
    "texi":"application/x-texinfo",
    "texinfo":"application/x-texinfo",
    "roff":"application/x-troff",
    "t":"application/x-troff",
    "tr":"application/x-troff",
    "man":"application/x-troff-man",
    "me":"application/x-troff-me",
    "ms":"application/x-troff-ms",
    "ustar":"application/x-ustar",
    "src":"application/x-wais-source",
    "cer":"application/x-x509-ca-cert",
    "crt":"application/x-x509-ca-cert",
    "der":"application/x-x509-ca-cert",
    "pko":"application/ynd.ms-pkipko",
    "zip":"application/zip",
    "au":"audio/basic",
    "snd":"audio/basic",
    "mid":"audio/mid",
    "rmi":"audio/mid",
    "mp3":"audio/mpeg",
    "aif":"audio/x-aiff",
    "aifc":"audio/x-aiff",
    "aiff":"audio/x-aiff",
    "m3u":"audio/x-mpegurl",
    "ra":"audio/x-pn-realaudio",
    "ram":"audio/x-pn-realaudio",
    "wav":"audio/x-wav",
    "bmp":"image/bmp",
    "cod":"image/cis-cod",
    "gif":"image/gif",
    "ief":"image/ief",
    "jpe":"image/jpeg",
    "jpeg":"image/jpeg",
    "jpg":"image/jpeg",
    "jfif":"image/pipeg",
    "svg":"image/svg+xml",
    "tif":"image/tiff",
    "tiff":"image/tiff",
    "ras":"image/x-cmu-raster",
    "cmx":"image/x-cmx",
    "ico":"image/x-icon",
    "pnm":"image/x-portable-anymap",
    "pbm":"image/x-portable-bitmap",
    "pgm":"image/x-portable-graymap",
    "ppm":"image/x-portable-pixmap",
    "rgb":"image/x-rgb",
    "xbm":"image/x-xbitmap",
    "xpm":"image/x-xpixmap",
    "xwd":"image/x-xwindowdump",
    "css":"text/css",
    "323":"text/h323",
    "htm":"text/html",
    "html":"text/html",
    "stm":"text/html",
    "uls":"text/iuls",
    "bas":"text/plain",
    "c":"text/plain",
    "h":"text/plain",
    "txt":"text/plain",
    "rtx":"text/richtext",
    "sct":"text/scriptlet",
    "tsv":"text/tab-separated-values",
    "htt":"text/webviewhtml",
    "htc":"text/x-component",
    "etx":"text/x-setext",
    "vcf":"text/x-vcard",
    "mp2":"video/mpeg",
    "mpa":"video/mpeg",
    "mpe":"video/mpeg",
    "mpeg":"video/mpeg",
    "mpg":"video/mpeg",
    "mpv2":"video/mpeg",
    "mp4":"video/mp4",
    "mov":"video/quicktime",
    "qt":"video/quicktime",
    "lsf":"video/x-la-asf",
    "lsx":"video/x-la-asf",
    "asf":"video/x-ms-asf",
    "asr":"video/x-ms-asf",
    "asx":"video/x-ms-asf",
    "avi":"video/x-msvideo",
    "movie":"video/x-sgi-movie"
            }
    if fext[-1] in filetype.keys():
        return (filetype[fext[-1]])
    else:
        return "application/octet-stream"

def get_filecontent(filePath):
    with open(filePath, 'rb') as file_:
        return file_.read()

def get_filesize(filePath):
    return str(os.path.getsize(filePath))

