import re
import os
import sys
from json import load
from json import dumps,dump
import logging
from pprint import pprint
sys.path.append(os.path.dirname(__file__))
import commonUtils as cutils
import itertools
import argparse
import traceback
import time
from logging.handlers import RotatingFileHandler


def get_application_dir( app, root_dir,  transJson):
    try:
        return os.path.join(root_dir, transJson['path'])
    except KeyError: #this exception case is added for testing and debugging
        return os.path.join(root_dir, transJson['version'], app)

def create_app_instance(appname, appid, act, trans, fulljson, attachdir, application_dir, payload_file):
    app = appname.lower()
    upperappname = app[0].upper() + app[1:]
    clname = 'SmartApp' +  upperappname
    modname = 'impl' + upperappname

    #app_path = get_application_dir( app, payload_dir, trans )
    sys.path.append(application_dir)
    module = __import__( modname)
    class_ = getattr(module, clname)
    inst = class_( appid, application_dir, act, trans, fulljson, attachdir, payload_file)
    return inst

class AppAction:
    def __init__(self,appobj, payloadFile, mslw, ismusess , sockName, actionid ):
        self.appobj = appobj
        self.payloadFile  = payloadFile
        self.mslw  = mslw
        self.ismusess = ismusess
        self.sockName = sockName
        self.actionIdx = actionid

    def setJsons(self, actionJson, transJson, fullJson, connJson):
        self.actionJson  = actionJson
        self.transJson  = transJson
        self.fullJson = fullJson
        self.connJson  = connJson
        self.isreq   = (actionJson['source'] == 'client')
        self.transParams     = transJson['transactionParameters']
        self.transName = transJson['transaction']

    def generate_msl(self):
        try:
            h = self.appobj.apply_action_modification(
                self.transName,
                self.isreq,
                self.transParams,
                self.payloadFile,
                self.mslw,
                self.ismusess ,
                self.sockName
            )
            return h
        except Exception as e:
            print(f'\nException processing {os.path.basename(self.payloadFile)} \nException:{e}\n')
            raise e

    def msl_done(self):
        self.appobj = None

class Transaction:
    def __init__(self, tjs, trid=0):
        self.tid = trid
        self.tjson = tjs['transactionParameters']
        self.actions = []
        self.fillsz = 0
        try:
            self.fillsz  = int(self.tjson['fillParameters']['payloadSize'])
            units = str(self.tjson['fillParameters']['fillUnit'])
            if units == 'KB':
                self.fillsz *= 1024
            elif units == 'MB':
                self.fillsz *= 1024*1024
        except  Exception:
            pass

    def add_action(self, act):
        if self.fillsz <= 0: #no need to add anything there is no fill
            return
        if act.appobj.get_fillable_len() > 0 :
            self.actions.append( act )

    def get_json(self):
        return self.tjson

    def distribute_fill_across_all_actions( self ):
        if len(self.actions) <= 0:
            return
        fillsz  =  self.fillsz

        if fillsz <= 0:
            return

        nactions = len(self.actions)
        if fillsz <= nactions:
            lastapp = self.actions[-1]
            self.actions = [ lastapp ]

        fill_per_action = int (fillsz /  len(self.actions) )

        for  act in self.actions:
            f = cutils.FillPayload( self.tjson['fillParameters'], fill_per_action )
            act.appobj.set_fill(f)

class MslGenerator:
    def __init__(self, target_dir):
        self.attachMents = None
        self.actions = []
        self.target_dir = target_dir

    def get_item_repeat_count(self, iJson):
        return iJson['repeat']

    def generate_msl_from_actions(self):
        for act in self.actions:
            h = act.generate_msl()
            #sz = h.get_modified_size()
            #print(f"{os.path.basename(act.payloadFile)}:{sz}")
            h.write_the_payload( os.path.join(self.target_dir, os.path.basename(act.payloadFile) )+'.target') 
            act.msl_done()

    def process_action(self,appname, payloadFile, actionJson, transJson, fullJson, transaction, application_dir):
        actionIdx = self.actionCount
        appobj = create_app_instance(appname, actionIdx, actionJson, transJson,
                                     fullJson, self.attachMents, application_dir, payloadFile)


        actobj = AppAction( appobj,  payloadFile, None, "True" , "abcd" , actionIdx)
        actobj.setJsons(actionJson, transJson, fullJson, None)
        self.actions.append(actobj)
        transaction.add_action( actobj )


    """
        currently we need to support payload as {name, content} ie action[payload][name]
        but changes are not complete, until the changes are complete we need to support
        old scheeme as well ie action[payload]
        so in the below function both scheemes work.
    """
    #TODO once the all scheemas are changed remove the try and exception code
    def get_file_name(self, actionJson):
        try:
            return actionJson['payload']['name']
        except TypeError:
            return actionJson['payload']


    def parse_action(self, actionJson, transJson, fullJson, nthLoop, transaction):
        if not actionJson['run']:
            return
        self.actionCount += 1
        isreq   = (actionJson['source'] == 'client')
        filename =  self.get_file_name(actionJson)

        appname             = ''.join(transJson['application'].split()).lower()

        app_dir =  get_application_dir( appname, self.rootDir,  transJson)
        payload_dir = app_dir
        if 'path' in actionJson['payload']:
            payload_dir = actionJson['payload']['path']

        payloadFile  = os.path.join(payload_dir, filename)

        self.process_action(appname, payloadFile, actionJson, transJson, fullJson, transaction,app_dir)


    '''
        return pair weather actionloop , if yes count of actions loop
    '''
    def get_action_type(self, aItems):
        rCount = 0
        aType = aItems['itemType']
        if aType == 'action':
            return 'action',0
        else:
            print("Unknown action type loop")
            sys.exit(-1)

    def run_enabled(self,item):
        try:
            return  item['run']
        except Exception as e:
            return True
        return True

    def parse_items_transaction(self, itemJson, parentJson, fullJson, loopEnabled,nthLoop):
        iType = itemJson['itemType']
        if not self.run_enabled(itemJson):
            return
        transaction = Transaction( itemJson )
        for tItem in itemJson['items']:
            actionType,loopCount = self.get_action_type( tItem)
            if actionType == 'action':
                self.parse_action( tItem, itemJson, fullJson, 0, transaction)
            else:
                print("Unknown item in transaction")
                pprint(tItem,indent=2)
                sys.exit(-1)

    def parse_items_0(self, itemsJson, fullJson):
        for item in itemsJson:
            iType = item['itemType']
            if iType == 'transaction':
                self.parse_items_transaction( item, itemsJson, fullJson, False, 0)
            else:
                logging.critical('Unknown Item in scenarion JSON: {self.json_file}')
                pprint(item, indent=2)
                raise 'Unknown item in top level processing'
                sys.exit(-1)

    def generate_msl_from_instance_json_throws_exception(self, fname, pay_dir):
        start_time = time.time()
        self.rootDir = pay_dir #constant
        self.actionCount = 0
        self.json_name = fname
        self.scen = cutils.Scenario( fname )
        itemJson = self.scen.json_data['items']
        parentJson = None
        transJson = None

        self.parse_items_0(itemJson, self.scen.json_data)

        self.generate_msl_from_actions()

    def generate_msl_from_instance_json(self, fname, pay_dir):
        try:
            self.generate_msl_from_instance_json_throws_exception( fname, pay_dir)
        except Exception as e:
            logging.info(f'\nException processing msl generation \nException:{e}\n')
            tb = traceback.format_exc()
            logging.critical(tb)
            #s  = dumps(self.scen.full_json_data, indent=2)
            #logging.critical(s)
            raise

def usage():
    print("python mslgen.py Instance.json <DIR of smartapps> target_file")

#logging.basicConfig(level=logging.DEBUG)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('json')
    parser.add_argument('appsDir')
    parser.add_argument('mslFileName')
    parser.add_argument('--attachmentsDir')
    parser.add_argument('--writeSize')
    args = parser.parse_args()
    attachDir = args.attachmentsDir
    msl = MslGenerator( sys.argv[3] )
    msl.generate_msl_from_instance_json( sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
