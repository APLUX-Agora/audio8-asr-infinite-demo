"""Environment checks use sourced parameters; no board installation or NPU required."""
import contextlib,importlib.util,io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preflight',ROOT/'tools/check-environment.py')
preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
class EnvironmentTests(unittest.TestCase):
 def test_check_reads_sourced_parameters(self):
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'AGORA_WORKSPACE':folder,'AGORA_SOC':'QCS8550','AGORA_OS':'ubuntu','AGORA_OS_VERSION':'22.04'}),patch('sys.argv',['check']),patch.object(preflight,'inspect_device',return_value=[]) as inspect,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(preflight.main(),0);inspect.assert_called_once_with(Path(folder),'QCS8550','22.04','ubuntu')
 def test_failed_check_returns_failure(self):
  results=[{'status':'FAILED','check':'architecture','expected':'aarch64','actual':'x86_64'}]
  with patch('sys.argv',['check','--soc','QCS8550','--ubuntu','22.04']),patch.object(preflight,'inspect_device',return_value=results),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),1)
 def test_pending_dependencies_have_distinct_status(self):
  results=[{'status':'NEEDS_SETUP','check':'ffmpeg','expected':'installed','actual':'missing'}]
  with patch('sys.argv',['check','--soc','QCS8550','--ubuntu','22.04']),patch.object(preflight,'inspect_device',return_value=results),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),2)
 def test_global_template_contains_only_common_parameters(self):
  import subprocess
  script='source "$1"; env'
  output=subprocess.check_output(['bash','-c',script,'bash',str(ROOT/'agora/agora.env.example')],text=True,env={'PATH':os.environ['PATH'],'HOME':str(Path.home())})
  values=dict(line.split('=',1) for line in output.splitlines() if '=' in line)
  expected={'AGORA_WORKSPACE','AGORA_CONTENT_ID','AGORA_CODE_REPO','AGORA_CODE_REF','AGORA_RESOURCE_REPO','AGORA_RESOURCE_REF','AGORA_SOC','AGORA_OS','AGORA_OS_VERSION'}
  self.assertEqual({key for key in values if key.startswith('AGORA_')},expected)
  self.assertFalse(any(key.startswith('A8_') for key in values))
 def test_project_resource_selection_excludes_other_soc_graphs(self):
  import subprocess
  targets={'QCS8550':'qcs8550_qnn248','QCS8625':'qcs8625_qnn248','IQ8':'qcs8275_qnn248','IQ9':'qcs9075_qnn248'}
  for soc,target in targets.items():
   with self.subTest(soc=soc):
    script='source "$1"; printf "%s\\n" "${AUDIO8_DOWNLOAD_PATTERNS[@]}"'
    patterns=subprocess.check_output(['bash','-c',script,'bash',str(ROOT/'agora/resources.env')],text=True,env={'PATH':os.environ['PATH'],'AGORA_SOC':soc}).splitlines()
    self.assertEqual([p for p in patterns if p.startswith('targets/')],['targets/'+target+'/*'])
    self.assertIn('models.json',patterns);self.assertIn('embedding.bin',patterns)
 def test_unknown_soc_cannot_select_all_graphs(self):
  import subprocess
  run=subprocess.run(['bash','-c','source "$1"','bash',str(ROOT/'agora/resources.env')],env={'PATH':os.environ['PATH'],'AGORA_SOC':'unknown'},capture_output=True,text=True)
  self.assertNotEqual(run.returncode,0);self.assertIn('no resource target',run.stderr)
 def test_unknown_soc_clears_a_previous_target_selection(self):
  import subprocess
  script='AGORA_SOC=QCS8550; source "$1"; AGORA_SOC=unknown; source "$1"; printf "%s\\n" "${AUDIO8_DOWNLOAD_PATTERNS[@]}"'
  run=subprocess.run(['bash','-c',script,'bash',str(ROOT/'agora/resources.env')],env={'PATH':os.environ['PATH']},capture_output=True,text=True)
  self.assertEqual(run.stdout.strip(),'__unsupported_soc__')
if __name__=='__main__':unittest.main()
