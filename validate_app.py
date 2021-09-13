import subprocess
import sys
app = sys.argv[1]
import os
import glob


command = f'python3.8 /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/app/lib/smartapps/mslgen.py  /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/2021/09/{app}/original_metadata.json  /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/ {app}.msl'
subprocess.call( command , shell=True)

cmd2  = f'./a.out {app}.msl'
subprocess.call( cmd2 , shell=True)


fix_content_len_command = f'python3.8 fixup_contentlen_all_apps.py {app}'
subprocess.call( fix_content_len_command , shell=True)

CWD = f'/mnt/c/Users/raidu/ubuntu_work/msl_parser/1/2/3/4/5/{app}/'
os.mkdir( CWD )
cmd3 = f'python3.8 generate_substituted_payload.py /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/2021/09/{app}/original_metadata.json  /mnt/c/Users/raidu/ubuntu_work/GitHub/smartapps/applications/  {CWD}/'
subprocess.call( cmd3 , shell=True)

pay_files = glob.glob(f'{app}.*.payload')
for fname in pay_files:
    diff_cmd = f'diff -w {fname} {CWD}/{fname}.target'
    subprocess.call( diff_cmd , shell=True)
