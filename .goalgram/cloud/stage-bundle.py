#!/usr/bin/env python3
"""Stage Bazel-built bundles into native Xcode signing targets (never a stub release)."""
import os
from pathlib import Path
import plistlib
import shutil
import subprocess


def main():
    if os.environ.get('ACTION') == 'indexbuild':
        return
    root = Path(__file__).resolve().parents[2]
    stage = Path(os.environ.get('GOALGRAM_CLOUD_STAGE', str(root / '.cloud-stage')))
    name = os.environ['FULL_PRODUCT_NAME']
    source = stage / 'Payload/Telegram.app'
    if name != 'Telegram.app':
        source = source / 'PlugIns' / name
    if not (source / 'Info.plist').is_file():
        raise SystemExit('Missing Bazel product. Cloud preparation must finish before native signing; refusing placeholder build.')
    info = plistlib.loads((source / 'Info.plist').read_bytes())
    if info['CFBundleIdentifier'] != os.environ['PRODUCT_BUNDLE_IDENTIFIER']:
        raise SystemExit('Bazel/native bundle identifier mismatch')
    if info['CFBundleVersion'] != os.environ['CURRENT_PROJECT_VERSION']:
        raise SystemExit('Bazel/native build number mismatch')
    destination = Path(os.environ['TARGET_BUILD_DIR']) / name
    destination.mkdir(parents=True, exist_ok=True)
    # The build product is an isolated output, never the source bundle or account data.
    subprocess.run(['/usr/bin/rsync', '-a', '--delete', '--exclude=PlugIns',
                    '--exclude=embedded.mobileprovision', '--exclude=_CodeSignature',
                    str(source) + '/', str(destination) + '/'], check=True)
    # Xcode embeds and signs extension targets itself; copied nested frameworks need signing too.
    identity = os.environ.get('EXPANDED_CODE_SIGN_IDENTITY', '')
    if os.environ.get('CODE_SIGNING_ALLOWED') != 'NO':
        if not identity:
            raise SystemExit('Automatic signing did not supply an identity')
        for framework in sorted(destination.glob('Frameworks/*.framework')):
            subprocess.run(['codesign', '--force', '--sign', identity,
                            '--preserve-metadata=identifier', str(framework)], check=True)
    symbols = stage / 'dSYMs'
    dsym_destination = Path(os.environ.get('DWARF_DSYM_FOLDER_PATH', str(destination.parent)))
    if symbols.is_dir():
        for item in symbols.glob('*.dSYM'):
            if item.name == name + '.dSYM' or (name == 'Telegram.app' and '.framework.' in item.name):
                shutil.copytree(item, dsym_destination / item.name, dirs_exist_ok=True)
    print('Staged verified Bazel product for native signing:', name)


if __name__ == '__main__':
    main()
