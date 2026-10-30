"""Invoke the pristine upstream build with host-only headless/signing adapters."""
import sys,os,importlib.util
from pathlib import Path
source=Path(__file__).resolve().parents[2]
os.chdir(source);sys.path.insert(0,str(source/'build-system/Make'))
import BuildEnvironment
original_env=BuildEnvironment.get_clean_env
def build_env(use_clean_env=True):
 env=original_env(use_clean_env)
 env['PATH']='/opt/homebrew/opt/rsync/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'
 return env
BuildEnvironment.get_clean_env=build_env
spec=importlib.util.spec_from_file_location('upstream_make',source/'build-system/Make/Make.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_call=m.call_executable
def headless_call(args,*a,**kw):
 if args and args[0] in ('killall','open'):return
 return original_call(args,*a,**kw)
m.call_executable=headless_call
original_init=m.BazelCommandLine.__init__
def init(self,*a,**kw):
 original_init(self,*a,**kw)
 self.common_args += ['--ios_signing_cert_name=-']
m.BazelCommandLine.__init__=init
import textwrap
body=(source/'build-system/Make/Make.py').read_text().split("if __name__ == '__main__':\n",1)[1]
exec(compile(textwrap.dedent(body),str(source/'build-system/Make/Make.py'),'exec'),m.__dict__)
