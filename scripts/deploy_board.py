"""Build locally and deploy to the existing Raspberry Pi installation over SSH.

Credentials are read from settings.toml and are never printed or packaged.
"""
import argparse
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = (
    'main.py', 'ser.py', 'config.py', 'clock.py', 'weather.py', 'tickertape.py',
    'drawGraphics.py', 'aquarium.py', 'run.sh', 'Templates/index.html', 'weather_conditions.json',
)


def build_package():
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Install Node.js before building.')
    if not (ROOT / 'node_modules' / 'vite').is_dir():
        subprocess.run([npm, 'ci', '--cache', '.npm-cache', '--no-audit', '--no-fund'],
                       cwd=ROOT, check=True)
    subprocess.run([npm, 'run', 'build'], cwd=ROOT, check=True)
    files = [ROOT / name for name in APP_FILES]
    files += sorted((ROOT / 'static' / 'ui').rglob('*'))
    files += sorted((ROOT / 'day').rglob('*'))
    files += sorted(ROOT.glob('*.bdf'))
    files = [path for path in files if path.is_file()]
    if not all((ROOT / name).is_file() for name in APP_FILES):
        raise RuntimeError('An application file is missing.')
    output = ROOT / '.deploy' / 'led-matrix.tar.gz'
    output.parent.mkdir(exist_ok=True)
    with tarfile.open(output, 'w:gz') as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            if path.suffix in ('.py', '.sh', '.html'):
                data = data.replace(b'\r\n', b'\n')
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name == 'run.sh' else 0o644
            archive.addfile(info, io.BytesIO(data))
    print('Built deployment package (application and website; no settings or credentials).', flush=True)
    return output


def connect():
    import paramiko
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    settings = tomllib.loads((ROOT / 'settings.toml').read_text(encoding='utf-8'))
    if not all(settings.get(key) for key in ('PI_IP', 'PI_UN', 'PI_PSW')):
        raise RuntimeError('settings.toml needs PI_IP, PI_UN, and PI_PSW.')
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    known_hosts = ROOT / '.deploy' / 'known_hosts'
    known_hosts.parent.mkdir(exist_ok=True)
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    # Trust the configured board on first connection, then pin its key locally.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(settings['PI_IP'], port=int(settings.get('PI_PORT', 22)),
                       username=settings['PI_UN'], password=settings['PI_PSW'],
                       timeout=15, auth_timeout=15, banner_timeout=15,
                       look_for_keys=False, allow_agent=False)
        client.save_host_keys(str(known_hosts))
    except Exception:
        client.close()
        raise
    return client


def remote_python(client, code, payload=None, sudo=False, timeout=90):
    command = ('sudo -n ' if sudo else '') + 'python3 -c ' + shlex.quote(code)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    stdin.write(json.dumps(payload or {}))
    stdin.flush()
    stdin.channel.shutdown_write()
    output = stdout.read()
    error = stderr.read()  # Never echo remote output: paths can contain SSH usernames.
    status = stdout.channel.recv_exit_status()
    if status != 0:
        raise RuntimeError('Remote step failed; existing settings are preserved.')
    try:
        return json.loads(output)
    except ValueError:
        raise RuntimeError('Board returned an unexpected response.') from None


INSPECT = r'''
import json, os, pathlib, subprocess, sys
options = json.load(sys.stdin)
home = pathlib.Path.home()
specified = options.get('remote_dir')
candidates = [pathlib.Path(specified).expanduser()] if specified else [
    home / 'main/test/test', home / 'test/test', pathlib.Path('/home/main/test/test')]
matches = []
for candidate in candidates:
    try:
        if (candidate / 'main.py').is_file() and candidate.resolve() not in matches:
            matches.append(candidate.resolve())
    except OSError:
        pass
if len(matches) != 1:
    raise RuntimeError('Specify --remote-dir to select the installed project.')
project = matches[0]
sudo = subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0
cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True).stdout
def settings_exists(name):
    return subprocess.run(['sudo', '-n', 'test', '-f', str(project / name)],
                          capture_output=True).returncode == 0
print(json.dumps(dict(project=str(project),
    venv=(project / 'venv/bin/python').is_file(),
    cached=(project / 'cachedArticles.json').is_file(),
    settings=settings_exists('runtime/settings.toml') or settings_exists('settings.toml'),
    sudo=sudo, reboot_cron=any('@reboot' in line and 'run.sh' in line
                              and not line.lstrip().startswith('#') for line in cron.splitlines()))))
'''


INSTALL = r'''
import datetime, hashlib, json, os, pathlib, shutil, signal, subprocess, sys, tarfile, time, urllib.request
options = json.load(sys.stdin)
project = pathlib.Path(options['project']).resolve()
upload = pathlib.Path(options['upload']).resolve()
if not (project / 'main.py').is_file() or not (project / 'venv/bin/python').is_file():
    raise RuntimeError('Installed project not found.')
if upload.parent != pathlib.Path('/tmp') or not upload.name.startswith('led-matrix-'):
    raise RuntimeError('Unexpected upload path.')
stage = upload.with_suffix('.stage')
stage.mkdir(mode=0o700)
files = []
backup = None
absent = []
stopped = False
process = None
phase = 'package validation'
def running(pid):
    try:
        return pathlib.Path('/proc/%s/stat' % pid).read_text().split(') ', 1)[1][0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return False
def app_pids():
    result = []
    for directory in pathlib.Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            args = (directory / 'cmdline').read_bytes().decode().split('\0')
            if not args or 'python' not in pathlib.Path(args[0]).name:
                continue
            absolute_main = str(project / 'main.py') in args[1:]
            relative_main = ('main.py' in args[1:] or './main.py' in args[1:]) and (directory / 'cwd').resolve() == project
            if absolute_main or relative_main:
                result.append(int(directory.name))
        except (OSError, UnicodeError):
            pass
    return result
def start():
    # A detached session survives the SSH connection, as with the reboot cron job.
    with open(project / 'run.log', 'ab') as log:
        return subprocess.Popen(['sh', str(project / 'run.sh')], cwd=str(project),
            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
try:
    with tarfile.open(upload, 'r:gz') as archive:
        for member in archive.getmembers():
            path = pathlib.PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts:
                raise RuntimeError('Unsafe package member.')
            allowed = member.name in options['app_files'] or path.parts[0] in ('day', 'static') or (len(path.parts) == 1 and path.suffix == '.bdf')
            if not allowed or any(part in ('runtime', 'settings.toml', '.git', '.ssh') for part in path.parts):
                raise RuntimeError('Unexpected package member.')
            destination = stage / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, open(destination, 'wb') as target:
                shutil.copyfileobj(source, target)
            destination.chmod(member.mode)
            if path.suffix == '.py':
                compile(destination.read_bytes(), member.name, 'exec')
            files.append(member.name)
    required = list(options['app_files']) + ['static/ui/app.js', 'static/ui/app.css']
    if not all(name in files for name in required):
        raise RuntimeError('Incomplete package.')
    # Confirm required libraries using the board's existing Python environment.
    phase = 'dependency check'
    check = subprocess.run([str(project / 'venv/bin/python'), '-c',
        'import flask, aiohttp, PIL, requests; from rgbmatrix import RGBMatrix'],
        cwd=str(project), capture_output=True)
    if check.returncode:
        raise RuntimeError('Board dependencies are missing.')
    phase = 'backup'
    backup_dir = project / '.deploy-backups'
    backup_dir.mkdir(exist_ok=True, mode=0o700)
    backup = backup_dir / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.tar.gz')
    with tarfile.open(backup, 'w:gz') as archive:
        for name in files:
            destination = project / name
            # Never follow existing symlinks into settings or unrelated directories.
            if destination.is_symlink() or any(p.is_symlink() for p in destination.parents if p != project and project in p.parents):
                raise RuntimeError('Unexpected deployment symlink.')
            if destination.exists():
                archive.add(destination, arcname=name, recursive=False)
            else:
                absent.append(name)
    phase = 'stopping app'
    pids = app_pids()
    stopped = True
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 10
    while any(running(pid) for pid in pids):
        if time.monotonic() > deadline:
            # A native-driver deadlock cannot handle Python's SIGTERM handler.
            for pid in pids:
                if running(pid):
                    os.kill(pid, signal.SIGKILL)
            deadline = time.monotonic() + 5
            while any(running(pid) for pid in pids):
                if time.monotonic() > deadline:
                    raise RuntimeError('Existing app did not stop.')
                time.sleep(.2)
            break
        time.sleep(.2)
    phase = 'installing files'
    for name in files:
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.deploy-tmp')
        shutil.copyfile(stage / name, temporary)
        temporary.chmod(0o755 if name == 'run.sh' else 0o644)
        os.replace(temporary, destination)
    phase = 'starting app'
    process = start()
    expected = {name: hashlib.sha256((stage / name).read_bytes()).digest()
                for name in ('static/ui/app.js', 'static/ui/app.css')}
    phase = 'health check'
    deadline = time.monotonic() + 40
    while True:
        try:
            base = 'http://127.0.0.1:%s/' % options['web_port']
            with urllib.request.urlopen(base + 'health', timeout=2) as response:
                if json.load(response).get('displayRunning') is not True:
                    raise ValueError('Display is not advancing.')
            with urllib.request.urlopen(base + 'ticker-enabled', timeout=2) as response:
                enabled = json.load(response)['enabled']
            if type(enabled) is not bool:
                raise ValueError('Invalid toggle response.')
            with urllib.request.urlopen(base + 'fish-mode', timeout=2) as response:
                if type(json.load(response)['enabled']) is not bool:
                    raise ValueError('Invalid FISH mode response.')
            for name, digest in expected.items():
                with urllib.request.urlopen(base + name, timeout=2) as response:
                    if hashlib.sha256(response.read()).digest() != digest:
                        raise ValueError('Asset verification failed.')
            if not app_pids():
                raise ValueError('App process missing.')
            break
        except Exception:
            if time.monotonic() > deadline:
                raise RuntimeError('Updated app health check failed.')
            time.sleep(1)
    print(json.dumps(dict(deployed=True, website_verified=True, ticker_verified=True, backup_created=True)))
except Exception:
    # Restore only the files included in this deployment, never configuration.
    if stopped:
        for pid in app_pids():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        time.sleep(1)
        if backup:
            with tarfile.open(backup, 'r:gz') as archive:
                for member in archive.getmembers():
                    destination = project / member.name
                    with archive.extractfile(member) as source, open(destination, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    destination.chmod(member.mode)
            for name in absent:
                (project / name).unlink(missing_ok=True)
        start()
    print(json.dumps(dict(deployed=False, rollback_attempted=stopped, phase=phase)))
finally:
    shutil.rmtree(stage)
    upload.unlink(missing_ok=True)
'''


def deploy(client, project, package, web_port):
    upload = '/tmp/led-matrix-%s.tar.gz' % uuid.uuid4().hex
    print('Uploading application and website.', flush=True)
    with client.open_sftp() as sftp:
        sftp.put(str(package), upload)
    print('Backing up installed files, restarting the app, and checking the website.', flush=True)
    result = remote_python(client, INSTALL, dict(project=project, upload=upload,
                           app_files=APP_FILES, web_port=web_port), sudo=True, timeout=120)
    if not result.get('deployed'):
        print('Failed step: %s.' % result.get('phase', 'unknown'), flush=True)
        print('Update failed. Previous files and startup were restored where possible.' if result.get('rollback_attempted')
              else 'Update failed before the installed app was changed.', flush=True)
        raise RuntimeError('Board deployment failed.')
    print('Deployment complete. Display frames, website assets, and control APIs verified. Backup saved on board.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true', help='Build and package without SSH.')
    parser.add_argument('--inspect', action='store_true', help='Check the board without changing it.')
    parser.add_argument('--remote-dir', help='Override automatic detection of the existing project directory.')
    parser.add_argument('--web-port', type=int, default=5000, help='Board web port for health checks (default: 5000).')
    args = parser.parse_args()
    package = None if args.inspect else build_package()
    if args.build_only:
        return
    with connect() as client:
        print('Connected to the configured board.', flush=True)
        info = remote_python(client, INSPECT, {'remote_dir': args.remote_dir})
        print('Found installed project. Virtual environment: %s. Settings: %s. Reboot cron: %s.' %
              (info['venv'], info['settings'], info['reboot_cron']), flush=True)
        if args.inspect:
            print('Passwordless restart permission: %s.' % info['sudo'], flush=True)
            return
        if not all(info[key] for key in ('venv', 'settings', 'cached', 'sudo')):
            raise RuntimeError('Board preflight failed: environment, settings, news cache, and passwordless sudo are required.')
        deploy(client, info['project'], package, args.web_port)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Connection and filesystem exceptions can include credentials or private hostnames.
        print('Deployment failed (%s). No SSH credentials were printed.' % type(error).__name__, file=sys.stderr)
        if isinstance(error, ModuleNotFoundError):
            print('Install local tools: python -m pip install -r requirements-deploy.txt', file=sys.stderr)
        sys.exit(1)
