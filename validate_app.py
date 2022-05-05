import subprocess
import sys
import os
import glob
import filecmp
import filecmp

app = sys.argv[1]
base_dir = '/mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/'
MSL_EXE = '/mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/app/lib/smartapps/mslgen.py'

def get_app_dir( app, base_app_dir):
    for y in os.listdir(base_app_dir):
        year = os.path.join( base_app_dir, y)
        if not os.path.isdir(year):
            continue
        for m in os.listdir(year):
            month = os.path.join( year, m)
            if not os.path.isdir(month):
                continue
            for sapp in os.listdir(month):
                if app == sapp:
                    return os.path.join(month, app )
    return None

app_dir = get_app_dir( app, base_dir)

print(app_dir)
meta_json = os.path.join(app_dir, "original_metadata.json")
command = f'python3.8 {MSL_EXE} {meta_json}  {base_dir} {app}.msl'

#print(command)
#sys.exit(0)

subprocess.call( command , shell=True)

cmd2  = f'./a.out {app}.msl'
subprocess.call( cmd2 , shell=True)


fix_content_len_command = f'python3.8 fixup_contentlen_all_apps.py {app}'
subprocess.call( fix_content_len_command , shell=True)

CWD = f'/mnt/c/Users/raidu/ubuntu_work/msl_parser/1/2/3/4/5/6/{app}/'
os.mkdir( CWD )

cmd3 = f'python3.8 generate_substituted_payload.py  {meta_json} /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/  {CWD}/'
subprocess.call( cmd3 , shell=True)
print("Result in the form of differences will be coming below:\n\n")

def diff_files_using_diff():
    pay_files = glob.glob(f'{app}.*.payload')
    for fname in pay_files:
        diff_cmd = f'diff -w {fname} {CWD}/{fname}.target'
        subprocess.call( diff_cmd , shell=True)
        print(f"Diff for {fname}")
        #x  = input()
def diff_files_using_cmp():
    pay_files = glob.glob(f'{app}.*.payload')
    for fname in pay_files:
        if not filecmp.cmp(f'{fname}', f'{CWD}/{fname}.target'):
            print(f"There is diff in files {fname} {CWD}/{fname}.target")
diff_files_using_cmp()

