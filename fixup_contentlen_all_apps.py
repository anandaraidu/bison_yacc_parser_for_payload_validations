from json import load
from json import dumps,dump
from pprint import pprint
import sys
import re
import urllib.parse
from collections import namedtuple 
import os
import difflib
import glob

APPLY_URL_ENCODE = 1
payloadfile = namedtuple('payloadfile', ['hsubs', 'bsubs'])

#b'#{@transactionParameters.comment}', comment, cutils.APPLY_URL_ENCODE)

def file_to_bytes( fname ):
    with open(fname, 'rb') as f:
        return f.read()

def bytes_to_file( buff,  fname):
    with open(fname, 'wb') as f:
        f.write(buff)

def get_body(buff):
    hdr, body = re.split( b'\r\n\r\n', buff , 1 )
    return hdr,body

def split_body( body ):
    return 0
    try:
        return len( re.split(b'\\r\\n', body) )
    except Exception as e:
        return 0
    return 0
def process_generated_file_unused( gen_file ):
    buff = file_to_bytes( gen_file )
    try:
        hdr, body = get_body(buff)
    except Exception as e:
        print(f"Error Breaking into header and body: {gen_file}")
        return
    blen = len(body)
    num_body_lines = split_body(body)
    #this needs explanation as why this magic addition.  EXPLAIN please
    if num_body_lines > 1:
        blen -= (num_body_lines - 1)
    if len(re.findall( b"Content-Length:xxx",  buff)) > 0:
        print(f"{gen_file} Modifying Content Len {split_body(body)}")
        mbuff = re.sub(b"Content-Length:xxx", (f'Content-Length: {str(blen)}').encode(), buff)
        bytes_to_file( mbuff, gen_file )

def write_body_to_file( gen_file ):
    buff = file_to_bytes( gen_file )
    try:
        hdr, body = get_body(buff)
        if len(body) <= 0:
            body = hdr + b'\r\n\r\n'
    except Exception as e:
        #print(f"Error Breaking into header and body: {gen_file} {buff}")
        body = buff
    bytes_to_file( body, gen_file )

def for_all_files( appname ):
    pay_files = glob.glob(f'{appname}.*.payload')
    for gen_file in pay_files:
        #process_generated_file( gen_file ) 
        write_body_to_file( gen_file ) 

for_all_files( sys.argv[1] )
