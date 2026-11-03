"""Environment checks use sourced parameters; no board installation or NPU required."""
import contextlib,importlib.util,io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preflight',ROOT/'tools/check-environment.py')
preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
class EnvironmentTests(unittest.TestCase):
 def test_check_reads_sourced_parameters(self):
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'AGORA_WORKSPACE':folder,'AGORA_SOC':'QCS8550','AGORA_UBUNTU':'22.04'}),patch('sys.argv',['check']),patch.object(preflight,'inspect_device',return_value=[]) as inspect,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(preflight.main(),0);inspect.assert_called_once_with(Path(folder),'QCS8550','22.04')
 def test_failed_check_returns_failure(self):
  results=[{'status':'FAILED','check':'architecture','expected':'aarch64','actual':'x86_64'}]
  with patch('sys.argv',['check','--soc','QCS8550','--ubuntu','22.04']),patch.object(preflight,'inspect_device',return_value=results),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),1)
 def test_pending_dependencies_have_distinct_status(self):
  results=[{'status':'NEEDS_SETUP','check':'ffmpeg','expected':'installed','actual':'missing'}]
  with patch('sys.argv',['check','--soc','QCS8550','--ubuntu','22.04']),patch.object(preflight,'inspect_device',return_value=results),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),2)
 def test_example_configuration_has_correct_target_files(self):
  import json,subprocess
  script='source "$1"; printf "%s\\n" "$AGORA_MODEL_REPO" "$AGORA_CODE_REPO" "${AGORA_MODEL_FILES[@]}"'
  output=subprocess.check_output(['bash','-c',script,'bash',str(ROOT/'agora/agora.env.example')],text=True).splitlines()
  self.assertEqual(output[:2],['APLUX-Agora/Audio8-ASR-Infinite-160ms','https://github.com/APLUX-Agora/audio8-asr-infinite-demo.git'])
  self.assertIn('targets/qcs8550_qnn248/*',output)
  self.assertFalse(any('qcs8275' in x for x in output))
if __name__=='__main__':unittest.main()
