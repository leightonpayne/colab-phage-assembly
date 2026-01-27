import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to python path to import pipeline
sys.path.append(str(Path(__file__).parent.parent / "src"))

from pipeline.pipeline import PhagePipeline

@pytest.fixture
def mock_pipeline():
    return PhagePipeline()

@pytest.fixture
def mock_logger():
    class MockLogger:
        def __init__(self):
            self.logs = []
        def write(self, text):
            self.logs.append(text)
    return MockLogger()

def test_pipeline_initialization(mock_pipeline):
    """Test that pipeline initializes with correct default config."""
    assert mock_pipeline.config.name == "PhagePipeline"
    assert "Setup" in mock_pipeline.config.categories
    assert "Data & Output" in mock_pipeline.config.categories

def test_define_parameters(mock_pipeline):
    """Test that parameters are defined correctly."""
    params = mock_pipeline.define_parameters()
    param_names = [p.name for p in params]
    
    assert "install_pharokka_db" in param_names
    assert "output_name" in param_names
    assert "short_r1" in param_names
    assert "short_r2" in param_names
    assert "run_fastqc" in param_names
    assert "run_trimming" in param_names
    assert "unicycler_mode" in param_names

@patch("pipeline.pipeline.subprocess.run")
@patch("pipeline.pipeline.subprocess.Popen")
@patch("pipeline.pipeline.shutil.which")
def test_run_pipeline_basic(mock_which, mock_popen, mock_run, mock_pipeline, mock_logger, tmp_path):
    """Test a basic pipeline run flow with mocked subprocesses."""
    
    # Mock existing tools
    mock_which.side_effect = lambda x: f"/usr/bin/{x}"
    
    # Mock subprocess execution to return success (returncode 0)
    process_mock = MagicMock()
    process_mock.stdout.readline.side_effect = ["Log line 1\n", "Log line 2\n", ""]
    process_mock.wait.return_value = None
    process_mock.returncode = 0
    mock_popen.return_value = process_mock

    # Mock subprocess.run for simple checks (Pharokka DB check)
    run_mock = MagicMock()
    run_mock.returncode = 0
    run_mock.stdout = "database found"
    mock_run.return_value = run_mock


    # Run in a temp directory
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        params = {
            "output_name": "test_project",
            "short_r1": "reads_R1.fastq.gz",
            "short_r2": "reads_R2.fastq.gz",
            "run_fastqc": True,
            "run_trimming": True,
            "unicycler_mode": "normal",
            "run_quast": True,
            "run_pharokka": True
        }
        
        # We need to mock _auto_patch_pharokka to avoid file system writes
        with patch.object(mock_pipeline, "_auto_patch_pharokka", return_value=True):
             # Mock fasta existence check
            with patch("pathlib.Path.exists", return_value=True):
                 success = mock_pipeline.run(params, mock_logger)
    
    assert success is True
    assert "🚀 Starting Phage Pipeline: test_project\n" in mock_logger.logs

@patch("pipeline.pipeline.subprocess.Popen")
def test_pipeline_failure(mock_popen, mock_pipeline, mock_logger, tmp_path):
    """Test pipeline failure when a step fails."""
    
    # Mock subprocess failure
    process_mock = MagicMock()
    process_mock.stdout.readline.return_value = ""
    process_mock.wait.return_value = None
    process_mock.returncode = 1 # Error code
    mock_popen.return_value = process_mock
    
    with patch("pathlib.Path.cwd", return_value=tmp_path):
        params = {
            "output_name": "test_project",
            "short_r1": "reads_R1.fastq.gz",
            "short_r2": "reads_R2.fastq.gz"
        }
        
        # Mocking check for logic flow
        with patch.object(mock_pipeline, "_auto_patch_pharokka", return_value=True):
             success = mock_pipeline.run(params, mock_logger)
             
    # Should fail at FastQC/Trimming or Assembly depending on flow, but definitely fail
    # Note: Logic might fail early if tools not found in real life, but here we mocked Popen returncode
    # Actually, `_run_cmd` returns the returncode. If assembly fails, it returns False.
    
    # Let's verify specific behavior. In current pipeline, if assembly fails (which is the first critical step if QC is skipped or passes), run returns False.
    # If Preprocessing fails (fastqc), it logs but continues? Let's check code.
    # Code says: if self._run_cmd(asm_cmd, logger) != 0: return False.
    
    assert success is False
