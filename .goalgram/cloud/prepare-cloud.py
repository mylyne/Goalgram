#!/usr/bin/env python3
"""Build real Telegram products in Cloud before native Xcode archive/signing."""
import base64
import datetime
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import uuid
import zipfile


def run(*args, **kwargs):
    subprocess.run(list(args), check=True, **kwargs)


def main():
    if os.environ.get('CI') != 'TRUE':
        raise SystemExit('Cloud-only preparation; use the workspace build wrapper for necessary local builds.')
    root = Path(__file__).resolve().parents[2]
    private = root / '.cloud-private'
    private.mkdir(mode=0o700, exist_ok=True)
    encoded = os.environ.get('GOALGRAM_BUILD_CONFIG_BASE64')
    if not encoded:
        raise SystemExit('Set secret GOALGRAM_BUILD_CONFIG_BASE64 in the Goalgram Cloud workflow; do not commit API credentials.')
    config = json.loads(base64.b64decode(encoded, validate=True))
    assert config['bundle_id'] == 'com.haocheng.goalgram'
    config_path = private / 'configuration.json'
    config_path.write_text(json.dumps(config))
    config_path.chmod(0o600)
    number = str(10013 + int(os.environ['CI_BUILD_NUMBER']))
    assert int(number) > 10013
    # Cloud supplies CURRENT_PROJECT_VERSION to native signing via this configuration file.
    (root / '.goalgram/cloud/BuildNumber.xcconfig').write_text('CURRENT_PROJECT_VERSION = ' + number + '\n')
    run('git', 'submodule', 'update', '--init', '--recursive', cwd=root)
    run(sys.executable, '-I', str(root / '.goalgram/test-read-landing.py'))
    bootstrap = private / 'bootstrap'
    profiles = bootstrap / 'profiles'
    profiles.mkdir(parents=True, exist_ok=True)
    (bootstrap / 'certs').mkdir(exist_ok=True)
    # Ephemeral self-signed analysis profiles, never Apple identities or distributable profiles.
    key, cert = private / 'bootstrap.key', private / 'bootstrap.pem'
    run('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
        '-subj', '/CN=UNSIGNED ARCHIVE BOOTSTRAP', '-keyout', str(key), '-out', str(cert),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    now = datetime.datetime.utcnow()
    mappings = {'Telegram':'', 'Intents':'.SiriIntents', 'NotificationContent':'.NotificationContent',
                'NotificationService':'.NotificationService', 'Share':'.Share', 'Widget':'.Widget',
                'BroadcastUpload':'.BroadcastUpload', 'WatchApp':'.watchkitapp',
                'WatchExtension':'.watchkitapp.watchkitextension'}
    for name, suffix in mappings.items():
        identifier = config['bundle_id'] + suffix
        team = config['team_id']
        entitlements = {'application-identifier':team + '.' + identifier,
                        'com.apple.developer.team-identifier':team,
                        'aps-environment':'production','get-task-allow':False,
                        'keychain-access-groups':[team + '.' + config['bundle_id']],
                        'com.apple.security.application-groups':['group.' + config['bundle_id']]}
        profile = {'Name':'UNSIGNED ARCHIVE BOOTSTRAP ' + name,'UUID':str(uuid.uuid4()),
                   'AppIDName':'Goalgram ' + name,'TeamName':'Goalgram Bootstrap',
                   'TimeToLive':2,
                   'TeamIdentifier':[team],'ApplicationIdentifierPrefix':[team],
                   'CreationDate':now,'ExpirationDate':now + datetime.timedelta(days=2),
                   'Platform':['iOS'],'Version':1,'Entitlements':entitlements}
        raw = private / (name + '.plist')
        raw.write_bytes(plistlib.dumps(profile))
        run('openssl','smime','-sign','-binary','-nodetach','-in',str(raw),
            '-signer',str(cert),'-inkey',str(key),'-outform','DER',
            '-out',str(profiles / (name + '.mobileprovision')))
    kind = 'release_arm64' if os.environ.get('CI_XCODEBUILD_ACTION') == 'archive' else 'debug_sim_arm64'
    artifacts = private / 'artifacts'
    run(sys.executable, str(root / '.goalgram/cloud/build-official.py'),
        '--cacheDir=' + str(private / 'bazel-cache'), 'build',
        '--configurationPath=' + str(config_path), '--codesigningInformationPath=' + str(bootstrap),
        '--buildNumber=' + number, '--configuration=' + kind,
        '--outputBuildArtifactsPath=' + str(artifacts), cwd=root)
    stage = root / '.cloud-stage'
    assert not stage.exists(), 'Refusing stale staged products'
    stage.mkdir()
    with zipfile.ZipFile(artifacts / 'Telegram.ipa') as package:
        for item in package.infolist():
            assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
        package.extractall(stage)
    app = stage / 'Payload/Telegram.app'
    extensions = list((app / 'PlugIns').glob('*.appex'))
    assert len(extensions) == 6, 'All six extensions must survive cloud compilation'
    for bundle in [app, *extensions]:
        info = plistlib.loads((bundle / 'Info.plist').read_bytes())
        assert info['CFBundleVersion'] == number
        assert info['CFBundleIdentifier'].startswith(config['bundle_id'])
    if (artifacts / 'DSYMs').is_dir():
        import shutil
        shutil.copytree(artifacts / 'DSYMs', stage / 'dSYMs')
    elif (artifacts / 'Telegram.DSYMs.zip').exists():
        with zipfile.ZipFile(artifacts / 'Telegram.DSYMs.zip') as symbols:
            for entry in symbols.infolist():
                assert entry.filename.startswith('DSYMs/') and '..' not in Path(entry.filename).parts
                relative = entry.filename[len('DSYMs/'):]
                if not relative or entry.is_dir():
                    continue
                output = stage / 'dSYMs' / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(symbols.read(entry))
    print('Real Bazel products prepared for Xcode automatic signing:', number)


if __name__ == '__main__':
    main()
