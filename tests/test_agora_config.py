"""Declaration validation and shell-safe parameter output; no NPU required."""
import contextlib,importlib.util,io,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('preflight',ROOT/'tools/check-environment.py')
preflight=importlib.util.module_from_spec(spec);spec.loader.exec_module(preflight)
class ConfigurationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
  self.data=json.loads((ROOT/'agora/agora-run.example.json').read_text())
  self.data['workspace']['root']=str(self.folder/'custom workspace')
 def tearDown(self):self.tmp.cleanup()
 def config(self):
  f=self.folder/'agora-run.json';f.write_text(json.dumps(self.data));return f
 def test_declared_paths_are_resolved_in_one_workspace(self):
  workspace,soc,ubuntu,values=preflight.load_configuration(self.config())
  self.assertEqual(values['AGORA_CODE_DIR'],str(workspace/'audio8-asr-infinite-demo'))
  self.assertEqual(values['AGORA_MODELS_DIR'],str(workspace/'models/audio8-160ms'))
  self.assertEqual((soc,ubuntu),('QCS8550','22.04'))
 def test_mismatched_soc_os_and_model_are_rejected(self):
  self.data['target']['soc']='IQ8'
  with self.assertRaises(ValueError):preflight.load_configuration(self.config())
 def test_credentials_are_not_executable_repository_strings(self):
  self.data['source']['repository']='git@github.com:org/repo.git; touch /tmp/unwanted'
  with self.assertRaises(ValueError):preflight.load_configuration(self.config())
 def test_wrong_model_directory_is_rejected(self):
  self.data['model']['directory']='$AGORA_WORKSPACE/models/audio8-80ms'
  with self.assertRaises(ValueError):preflight.load_configuration(self.config())
 def test_shell_output_preserves_spaces_and_metacharacters(self):
  marker=self.folder/'PWNED_TEST'
  self.data['workspace']['root']=str(self.folder/"literal $(touch PWNED_TEST) 'quoted'")
  config=self.config()
  def inspect(workspace,*args):workspace.mkdir(parents=True);return []
  with patch.object(preflight,'inspect_device',side_effect=inspect),patch('sys.argv',['check','--config',str(config)]),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),0)
  envfile=Path(self.data['workspace']['root'])/'agora-env.sh'
  actual=subprocess.check_output(['bash','-c','. "$1"; printf "%s" "$AGORA_WORKSPACE"','bash',str(envfile)],text=True,cwd=self.folder)
  self.assertEqual(actual,str(Path(self.data['workspace']['root']).resolve()));self.assertFalse(marker.exists())
 def test_failed_device_check_does_not_generate_parameters(self):
  workspace=Path(self.data['workspace']['root']);workspace.mkdir()
  results=[{'status':'FAILED','check':'architecture','expected':'aarch64','actual':'x86_64'}]
  with patch.object(preflight,'inspect_device',return_value=results),patch('sys.argv',['check','--config',str(self.config())]),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),1)
  self.assertFalse((workspace/'agora-env.sh').exists())
 def test_setup_needed_still_generates_parameters_for_installation(self):
  workspace=Path(self.data['workspace']['root']);workspace.mkdir()
  results=[{'status':'NEEDS_SETUP','check':'venv','expected':'installed','actual':'missing'}]
  with patch.object(preflight,'inspect_device',return_value=results),patch('sys.argv',['check','--config',str(self.config())]),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(preflight.main(),2)
  self.assertTrue((workspace/'agora-env.sh').exists())
if __name__=='__main__':unittest.main()
