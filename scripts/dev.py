"""Start local services with existing dependencies and credentials; never prints secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runtime/local-processes.json'
API_STATE=ROOT/'runtime/api-port.json'

def config():
    values={}
    p=ROOT/'.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1); values[k.strip()]=v.strip()
    return {**os.environ,**values}

def listening(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.5):return True
    except OSError:return False

def wait(port):
    for _ in range(60):
        if listening(port):return
        time.sleep(.5)
    raise RuntimeError(f'Port {port} did not start; inspect runtime/*.log')

def current_api_port():
    try:return int(json.loads(API_STATE.read_text(encoding='utf-8'))['port'])
    except (OSError,ValueError,KeyError):return 8000

def api_ready(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/heritage/version',timeout=3) as response:version=json.load(response)
        expected=hashlib.sha256((ROOT/'data/heritage/records.json').read_bytes()).hexdigest()
        return version.get('schema_version')=='heritage-2' and version.get('catalogue_digest')==expected
    except Exception:return False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','status'])
    args=parser.parse_args();env=config()
    if args.action=='status':
        for name,port in [('MySQL',int(env.get('MYSQL_PORT','13306'))),('API '+str(current_api_port()),current_api_port()),('Web',5173)]:
            print(name+(': listening' if listening(port) else ': stopped'))
        return
    if not (ROOT/'.env').exists():raise RuntimeError('Create .env from .env.example and configure a real MySQL account first.')
    runtime=ROOT/'runtime';runtime.mkdir(exist_ok=True)
    temp=runtime/'tmp';temp.mkdir(exist_ok=True);env.update(TEMP=str(temp),TMP=str(temp),PYTHONIOENCODING='utf-8')
    pids={}
    def launch(name,command,cwd=ROOT):
        with (runtime/(name+'.log')).open('ab') as log:
            child=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
        pids[name]={'pid':child.pid,'command':command}
        STATE.write_text(json.dumps(pids,indent=2),encoding='utf-8')
    port=int(env.get('MYSQL_PORT','13306'))
    if not listening(port):
        base=env.get('MYSQL_BASE_DIR');data=env.get('MYSQL_DATA_DIR');tmp=env.get('MYSQL_TMP_DIR',str(temp))
        if not base or not data:raise RuntimeError('MySQL is stopped. Start your MySQL service or configure MYSQL_BASE_DIR and MYSQL_DATA_DIR.')
        binary=str(Path(base)/'bin'/('mysqld.exe' if os.name=='nt' else 'mysqld'))
        launch('mysql',[binary,'--no-defaults','--basedir='+base,'--datadir='+data,'--tmpdir='+tmp,'--bind-address=127.0.0.1','--port='+str(port),'--mysqlx=OFF'])
        wait(port)
    candidates=list(dict.fromkeys([current_api_port(),*range(8000,8011)]))
    api_port=next((candidate for candidate in candidates if listening(candidate) and api_ready(candidate)),None)
    if api_port is None:
        api_port=next((candidate for candidate in candidates if not listening(candidate)),None)
        if api_port is None:raise RuntimeError('No available local API port from 8000 to 8010. Existing services were preserved.')
        local=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        workspace=ROOT.parent.parent/'work/venv/Scripts/python.exe'
        python=str(local if local.exists() else workspace if workspace.exists() else sys.executable)
        launch('api',[python,'-m','uvicorn','app.main:app','--app-dir',str(ROOT/'backend'),'--host','127.0.0.1','--port',str(api_port),'--reload','--reload-dir',str(ROOT/'backend')])
        wait(api_port)
    if not api_ready(api_port):raise RuntimeError('New API did not report the current catalogue version; inspect runtime/api.log.')
    if not API_STATE.exists() or current_api_port()!=api_port:
        API_STATE.write_text(json.dumps({'port':api_port}),encoding='utf-8')
    if not listening(5173):
        node=shutil.which('node')
        bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pnpm/bin/pnpm.cjs'
        cli=env.get('PNPM_CLI',str(bundled))
        if not node or not Path(cli).is_file():raise RuntimeError('Set PNPM_CLI to pnpm.cjs or start frontend manually with pnpm dev.')
        launch('web',[node,cli,'dev','--host','127.0.0.1','--port','5173'],ROOT/'frontend')
        wait(5173)
    with urlopen(f'http://127.0.0.1:{api_port}/api/health',timeout=10) as response:
        assert json.load(response)['database']=='connected'
    print(f'Ready: http://127.0.0.1:5173/ | API docs: http://127.0.0.1:{api_port}/docs')

if __name__=='__main__':main()
