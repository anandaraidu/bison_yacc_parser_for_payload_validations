from json import load
from json import dumps,dump
from pprint import pprint
import sys
import re
import urllib.parse
from collections import namedtuple 
import os

APPLY_URL_ENCODE = 1
payloadfile = namedtuple('payloadfile', ['hsubs', 'bsubs'])

def url_encode(r):
    x = urllib.parse.quote(r)
    return urllib.parse.quote(x)

class ReplacePattern:
    def __init__(self, patToReplace, replaceWith, enc):
        self.pat  = patToReplace
        print(f"Replace: {patToReplace} with : {replaceWith}")
        self.replace = replaceWith
        self.replaceEncode = enc

    def get_encoded_replacing_value_as_bytes(self):
        if self.replaceEncode == APPLY_URL_ENCODE:
            return url_encode(self.replace).encode()
        return self.replace.encode()

    def apply_pattern_substitution(self, buff):
        assert(len(buff)  >  0)
        ucoded = self.get_encoded_replacing_value_as_bytes()
        modified = re.sub(self.pat, ucoded, buff)
        return modified


#b'#{@transactionParameters.comment}', comment, cutils.APPLY_URL_ENCODE)
def get_json(input):
    with open(input, 'r')  as f:
        json_data = load(f)
    return json_data

def parse_action(traction, action, gen_file):
    global filedetails
    fname = action['payload']['name']
    #print(fname)
    if not fname in gen_file:
        return None

    hsubs  = action['mslProperties']['headerSubs']
    bsubs  = action['mslProperties']['bodySubs']
  
    hpats = {}
    bpats = {}
    for hs in hsubs: 
        pat = '#{@transactionParameters.' + f'{hs}' +  '}'
        hpats[pat] = ReplacePattern( pat.encode(), traction["transactionParameters"][hs] , APPLY_URL_ENCODE )
    for bs in bsubs: 
        pat = '#{@transactionParameters.' + f'{bs}' +  '}'
        bpats[pat] = ReplacePattern( pat.encode(), traction["transactionParameters"][bs] , APPLY_URL_ENCODE )
    #filedetails[fname] = payloadfile( hpats, bpats )
    return payloadfile( hpats, bpats )

def parse_scenario( scenario_file, gen_file ):
    js = get_json( scenario_file )
    for traction in js['metadata']["scenario"]['items']:
        actions  = traction['items']
        for action in actions:
            rv = parse_action(traction, action, gen_file )
            if rv != None:
                return rv
    return None
                

def file_to_bytes( fname ):
    with open(fname, 'rb') as f:
        return f.read()

def bytes_to_file( buff,  fname):
    with open(fname, 'wb') as f:
        f.write(buff)

def replace_content_len(hdr, bodylen):
    hdrs = re.split(b'\r\n', hdr)
    newhdrs = ''
    #perint(f"xxxx: {hdrs}")
    for h in hdrs:
        line = h
        if h.startswith(b'Content-Length'): 
            line = f'Content-Length: {str(bodylen)}'.encode()
        newhdrs += (f'{line.decode()}\r\n')
    #print(newhdrs)
    return newhdrs

def get_body(buff):
    hdr, body = re.split( b'\r\n\r\n', buff , 1 )
    return hdr,body

def process_generated_file( gen_file ):
    buff = file_to_bytes( gen_file )
    hdr, body = get_body(buff)
    blen = len(body)
    if len(re.findall( b"Content-Length:xxx",  buff)) > 0:
        print(f"{gen_file} Modifying Content Len")
        mbuff = re.sub(b"Content-Length:xxx", (f'Content-Length: {str(blen)}').encode(), buff)
        bytes_to_file( mbuff, gen_file )
    else:
        print(f"{gen_file} NOT Modifying Content Len")

def fixup_buff( buff, subs):
    hdr, body = get_body(buff)
    for  pat, patfunc in subs.bsubs.items():
        body = patfunc.apply_pattern_substitution(body)
    for pat, patfunc in subs.hsubs.items():
        hdr = patfunc.apply_pattern_substitution(hdr)

    if len(body) > 0:
        if len(subs.bsubs) > 0:
            hdr = replace_content_len(hdr, len(body) )
            return hdr.encode() + b'\r\n' + body
        else:
            return hdr + b'\r\n' + body
    return hdr 

def fixup_original_file( gen_file, original_file,  scenario_file,  modified_target_file):
    subs = parse_scenario( scenario_file, gen_file) 

    original_buff = file_to_bytes( original_file)
    mbuff = original_buff 
    if len(subs.bsubs) > 0 or len( subs.hsubs) > 0:
        mbuff = fixup_buff( original_buff, subs)
        #bytes_to_file (mbuff, modified_target_file)
    bytes_to_file (mbuff, modified_target_file)

gen_file = sys.argv[1]
scenario_file = sys.argv[2]
original_file = sys.argv[3]
modified_payload = f'{gen_file}.target'

process_generated_file( gen_file ) #just fix content-len
fixup_original_file( gen_file, original_file,  scenario_file,  modified_payload)

#b = file_to_bytes("inf")
#bytes_to_file("bbbb".encode(), "inf")
