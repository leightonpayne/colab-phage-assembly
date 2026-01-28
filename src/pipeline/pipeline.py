import os
import subprocess
import zipfile
import sys
import platform
import shutil
import site
import time

from pathlib import Path
from typing import Any, Dict, List, Optional

from boilerplate.core import Pipeline, PipelineConfig, PipelineParameter

class PhagePipeline(Pipeline):
    def __init__(self):
        config = PipelineConfig(
            name="PhagePipeline",
            title="Phage Assembly & Annotation",
            subtitle="A basic end-to-end pipeline for phage genome assembly and annotation from short reads",
            modes=["default", "advanced"],
            categories={
                "Setup": {"bg": "#f1f5f9", "text": "#475569", "collapsed": False},
                "Data & Output": {"bg": "#e0e7ff", "text": "#4338ca", "collapsed": False},
                "Preprocessing": {"bg": "#ccfbf1", "text": "#0f766e", "collapsed": True},
                "Assembly": {"bg": "#fef3c7", "text": "#b45309", "collapsed": True},
                "Quality Check": {"bg": "#fce7f3", "text": "#be185d", "collapsed": True},
                "Annotation": {"bg": "#ffedd5", "text": "#c2410c", "collapsed": True},
            }
        )
        super().__init__(config)
        self._current_process = None
        self._stop_requested = False

    def define_parameters(self) -> List[PipelineParameter]:
        return [
            PipelineParameter(name="install_pharokka_db", type="button", label="Install Pharokka DB", description="Download and index Pharokka databases (this can take 10-15 mins, but only needs to be run once per session)", category="Setup"),
            
            PipelineParameter(name="output_name", type="text", label="Project Name", description="Prefix for output files", default="phage_project", category="Data & Output"),
            PipelineParameter(name="short_r1", type="text", label="Short Reads R1", description="Path or upload for FASTQ R1 (Forward)", category="Data & Output"),
            PipelineParameter(name="short_r2", type="text", label="Short Reads R2", description="Path or upload for FASTQ R2 (Reverse)", category="Data & Output"),
            
            PipelineParameter(name="run_fastqc", type="bool", label="Run FastQC", description="Perform quality control check", default=True, category="Preprocessing"),
            PipelineParameter(name="run_trimming", type="bool", label="Run TrimGalore", description="Adapter removal and quality trimming", default=True, category="Preprocessing"),
            
            PipelineParameter(name="unicycler_mode", type="select", label="Assembly Mode", description="Unicycler verbosity/mode", options=["normal", "bold", "conservative"], default="normal", category="Assembly"),
            
            PipelineParameter(name="run_quast", type="bool", label="Run QUAST", description="Evaluate assembly quality", default=True, category="Quality Check"),
            
            PipelineParameter(name="run_pharokka", type="bool", label="Run Pharokka", description="Phage genome annotation", default=True, category="Annotation"),
        ]

    def terminate(self):
        """Terminate the running pipeline."""
        self._stop_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=5)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass
            self._current_process = None

    def _run_cmd(self, cmd: str, logger, cwd: Optional[Path] = None):
        if self._stop_requested:
            logger.warning("Pipeline execution aborted.")
            return -1

        # Diagnostics
        env = os.environ.copy()
        # Force unbuffered IO for Python scripts
        env["PYTHONUNBUFFERED"] = "1"
        
        python_bin = str(Path(sys.executable).parent)
        machine = platform.machine()
        is_apple_silicon = (machine == "arm64") or (platform.system() == "Darwin" and "Apple" in platform.processor())
        
        # Ensure the current Python's bin directory is in PATH
        if python_bin not in env.get("PATH", ""):
            env["PATH"] = python_bin + os.pathsep + env.get("PATH", "")

        logger.command(cmd)
        # Allow time for the widget log to flush to the UI
        time.sleep(0.1)
        
        if is_apple_silicon and platform.system() == "Darwin":
            if not cmd.startswith("arch -arm64"):
                cmd = f"arch -arm64 {cmd}"

        # Use unbuffered binary mode to read output immediately
        self._current_process = subprocess.Popen(
            cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=False, 
            cwd=str(cwd) if cwd else None,
            env=env,
            bufsize=0 # Unbuffered
        )
        
        import codecs
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        
        output_buffer = []
        last_flush = time.time()
        
        try:
            while True:
                # Read byte-by-byte to ensure we capture progress bars etc.
                char = self._current_process.stdout.read(1)
                
                if not char:
                    if self._current_process.poll() is not None:
                        break
                    continue
                    
                decoded_char = decoder.decode(char, final=False)
                if decoded_char:
                    output_buffer.append(decoded_char)
                    
                    # Check flush conditions: Newline, Carriage Return (progress bar), or Time elapsed
                    current_time = time.time()
                    if "\n" in decoded_char or "\r" in decoded_char or (current_time - last_flush > 0.2):
                        if self._stop_requested:
                            self._current_process.terminate()
                            break
                        
                        logger.write("".join(output_buffer))
                        output_buffer = []
                        last_flush = current_time
                        
            # Final flush
            if output_buffer:
                logger.write("".join(output_buffer))
                    
        except Exception as e:
            logger.error(f"Error reading output: {e}")
            
        self._current_process.wait()
        ret = self._current_process.returncode
        self._current_process = None
        
        if self._stop_requested:
            logger.write("❯ Terminated.\n")
            return -1
            
        return ret

    def _find_command(self, commands: List[str]) -> Optional[str]:
        """Find the first available command in PATH."""
        python_bin = str(Path(sys.executable).parent)

        
        for cmd in commands:
            # Check system path
            if shutil.which(cmd):
                return cmd
            # Check python bin dir explicitly
            if (Path(python_bin) / cmd).exists():
                return str(Path(python_bin) / cmd)
        return None

    def _auto_patch_pharokka(self, logger) -> bool:
        """Automatically patch Pharokka's hmm.py to fix pyhmmer string/bytes bug."""

        
        # Calculate script path relative to current python
        python_bin = Path(sys.executable).parent
        hmm_script = python_bin / "hmm.py"
        
        if not hmm_script.exists():
            # Try to find it in site-packages if not in bin
            # Try to find it in site-packages if not in bin
            for sp in site.getsitepackages():
                p = Path(sp) / "pharokka" / "hmm.py"
                if p.exists():
                    hmm_script = p
                    break
        
        if not hmm_script.exists():
            logger.write("❯ Could not find Pharokka hmm.py for auto-patching.\n")
            return False
            
        try:
            content = hmm_script.read_text()
            original = content
            
            # Patch 1: hits.query.name.decode()
            target1 = 'hits.query.name.decode()'
            patch1 = 'hits.query.name.decode() if hasattr(hits.query.name, "decode") else hits.query.name'
            if target1 in content and patch1 not in content:
                content = content.replace(target1, patch1)
                
            # Patch 2: hit.name.decode()
            target2 = 'hit.name.decode()'
            patch2 = 'hit.name.decode() if hasattr(hit.name, "decode") else hit.name'
            if target2 in content and patch2 not in content:
                content = content.replace(target2, patch2)
                
            if content != original:
                logger.write(f"❯ Auto-patching Pharokka script: {hmm_script}\n")
                hmm_script.write_text(content)
                return True
            else:
                logger.write("❯ Pharokka script already patched or compatible.\n")
                return True
                
        except Exception as e:
            logger.write(f"❯ Failed to auto-patch Pharokka: {e}\n")
            return False

    def handle_action(self, action_name: str, logger) -> bool:
        if action_name == "install_pharokka_db":
            logger.step("Starting Pharokka database installation...")
            logger.info("This will download several gigabytes and may take 10-20 minutes.")
            
            # Try newer command first, then fallback to older one
            # -d uses default directory, -f forces re-download
            commands_to_try = [
                "install_databases.py -d", 
                "pharokka_database.py --install -f"
            ]
            
            for cmd_with_args in commands_to_try:
                base_cmd = cmd_with_args.split()[0]
                if self._find_command([base_cmd]):
                    ret = self._run_cmd(cmd_with_args, logger)
                    if ret == 0:
                        logger.success("Pharokka databases installed successfully!")
                        return True
                    else:
                        logger.warning(f"Command {base_cmd} failed (exit code {ret}). Trying next...")
            
            logger.error("All Pharokka database installation commands failed.")
            return False
        return super().handle_action(action_name, logger)

    def run(self, params: Dict[str, Any], logger) -> bool:
        self._stop_requested = False
        
        try:
            project_name = params.get("output_name", "phage_project")
            output_dir = Path.cwd() / project_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Initializing project: {project_name}")
            logger.info(f"Output directory: {output_dir}")
            
            # 1. Inputs
            logger.stage("Input Validation")
            
            r1 = params.get("short_r1")
            r2 = params.get("short_r2")
            
            logger.info(f"R1: {r1}")
            logger.info(f"R2: {r2}")

            if not r1:
                logger.error("R1 input is required. Please provide a path to the first fastq file.")
                return False

            if not Path(r1).exists():
                logger.error(f"R1 file not found at: {r1}")
                return False
                
            if r2 and not Path(r2).exists():
                logger.error(f"R2 file not found at: {r2}")
                return False
                
        except Exception as e:
            logger.error(f"Critical Error during setup: {e}")
            import traceback
            logger.plain(traceback.format_exc())
            return False

        # 2. Preprocessing
        trimmed_r1, trimmed_r2 = r1, r2
        if params.get("run_fastqc"):
            if self._stop_requested: return False
            logger.stage("FastQC")
            fq_cmd = f"fastqc -o {output_dir} {r1} {r2 if r2 else ''}"
            self._run_cmd(fq_cmd, logger)

        if params.get("run_trimming") and (r1 or r2):
            if self._stop_requested: return False
            logger.stage("TrimGalore")
            trim_cmd = f"trim_galore --paired --output_dir {output_dir} {r1} {r2}" if r2 else f"trim_galore --output_dir {output_dir} {r1}"
            if self._run_cmd(trim_cmd, logger) == 0:
                def get_base(filepath):
                    name = Path(filepath).name
                    for ext in [".fastq.gz", ".fq.gz", ".fastq", ".fq"]:
                        if name.endswith(ext):
                            return name[:-len(ext)]
                    return Path(filepath).stem

                # Update paths for assembly
                if r2:
                    trimmed_r1 = str(output_dir / f"{get_base(r1)}_val_1.fq.gz")
                    trimmed_r2 = str(output_dir / f"{get_base(r2)}_val_2.fq.gz")
                else:
                    trimmed_r1 = str(output_dir / f"{get_base(r1)}_trimmed.fq.gz")

        # 3. Assembly
        if self._stop_requested: return False
        logger.stage("Assembly")
        assembly_out = output_dir / "assembly"
        mode = params.get("unicycler_mode", "normal")
        
        if trimmed_r1 and trimmed_r2:
            logger.info("Mode: Paired-end Short-read Assembly")
            asm_cmd = f"unicycler -1 {trimmed_r1} -2 {trimmed_r2} -o {assembly_out} --mode {mode}"
        elif trimmed_r1:
            logger.info("Mode: Single-end Short-read Assembly")
            asm_cmd = f"unicycler -s {trimmed_r1} -o {assembly_out} --mode {mode}"
        else:
            logger.error("No valid short-read inputs for assembly.")
            return False

        if self._run_cmd(asm_cmd, logger) != 0:
            logger.error("Assembly failed.")
            return False

        fasta_out = assembly_out / "assembly.fasta"
        if not fasta_out.exists():
            logger.error(f"Assembly file not found at {fasta_out}")
            return False
            
        logger.success("Assembly completed.")

        # 4. Quality Check
        if params.get("run_quast"):
            if self._stop_requested: return False
            logger.stage("Quality Check")
            quast_out = output_dir / "quast"
            self._run_cmd(f"quast.py {fasta_out} -o {quast_out}", logger)
            logger.success("Quality evaluation finished.")

        # 5. Annotation Chain
        current_fasta = fasta_out
        annotation_success = True

        if params.get("run_pharokka"):
            if self._stop_requested: return False
            logger.stage("Pharokka")
            
            # Automatically apply bug fix to Pharokka scripts in the current environment
            self._auto_patch_pharokka(logger)
            
            # Check for databases first (very basic check)
            db_check = subprocess.run("pharokka.py -h", shell=True, capture_output=True, text=True)
            if "database" in db_check.stdout.lower() or db_check.returncode == 0:
                pharokka_out = output_dir / "pharokka"
                
                # Calculate DB path: python_bin is .../bin, databases are .../databases
                python_bin = Path(sys.executable).parent
                db_dir = python_bin.parent / "databases"
                
                cmd = f"pharokka.py -i {current_fasta} -o {pharokka_out} -t 4 -f -d {db_dir}"
                if self._run_cmd(cmd, logger) == 0:
                     logger.success("Pharokka annotation complete.")
                else:
                    logger.error("Pharokka failed. Check if databases are installed.")
                    annotation_success = False
            else:
                logger.error("Pharokka command not working or databases missing.")
                annotation_success = False

        if not annotation_success:
            logger.warning("Some annotation steps failed. Results will be incomplete.")

        # 6. Output Packaging
        logger.stage("Finalizing Output")
        
        zip_path = Path.cwd() / f"{project_name}_results.zip"
        file_count = 0
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Recursively add all results, excluding large seq files
                for file_path in output_dir.rglob("*"):
                    if file_path.is_file():
                        # Exclude sequencing files
                        if any(file_path.name.endswith(ext) for ext in [".fq.gz", ".fastq.gz", ".fq", ".fastq"]):
                            continue
                            
                        # Use path relative to output_dir in the zip
                        arcname = file_path.relative_to(output_dir)
                        zipf.write(file_path, arcname=arcname)
                        file_count += 1
            
            if file_count > 0:
                logger.success(f"Packaged {file_count} results into {zip_path.name}")
            else:
                logger.warning("No result files found to package.")
                
        except Exception as e:
            logger.error(f"Error during zipping: {e}")
            return False
            
        logger.info(f"Final results zipped at: {zip_path}")
        
        if annotation_success:
            logger.success("Pipeline completed successfully!")
        else:
            logger.warning("Pipeline completed with warnings (some stages failed).")

        # Setup for download in Colab
        try:
            from google.colab import files
            files.download(str(zip_path))
            logger.info("Triggered download of results zip.")
        except ImportError:
            pass

        return True
