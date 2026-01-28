from pathlib import Path
import threading
import time

import anywidget
import traitlets
from .core import Pipeline
from .utils import run_with_logs, check_colab, keep_alive_thread
from .logging import PipelineLogger

class PipelineWidget(anywidget.AnyWidget):
    """Generic Pipeline Widget."""
    
    _esm = (Path(__file__).parent / "widget.js").read_text()
    
    # Traits synced with JS
    params_schema = traitlets.Dict().tag(sync=True)
    config = traitlets.Dict().tag(sync=True)
    
    # State synced from JS to Python
    params_values = traitlets.Dict().tag(sync=True)
    
    # Control signals
    run_requested = traitlets.Bool(False).tag(sync=True)
    terminate_requested = traitlets.Bool(False).tag(sync=True)
    action_requested = traitlets.Unicode("").tag(sync=True)
    status_state = traitlets.Unicode("idle").tag(sync=True)
    status_message = traitlets.Unicode("").tag(sync=True)
    logs = traitlets.Unicode("").tag(sync=True)
    html_output = traitlets.Unicode("").tag(sync=True)
    
    # Results
    result_file_name = traitlets.Unicode("").tag(sync=True)
    result_file_data = traitlets.Unicode("").tag(sync=True)
    
    def __init__(self, pipeline: Pipeline, **kwargs):
        self.pipeline = pipeline
        
        # Initialize traits from pipeline definition before super().__init__
        # to ensure they are available for the initial frontend render.
        schema = self.pipeline.get_schema()
        params_schema = schema.get("parameters", {})
        config = schema.get("config", {})
        
        # Populate initial values from defaults
        initial_values = {}
        for cat in params_schema.values():
            for p in cat:
                if p.get("def") is not None:
                    initial_values[p["name"]] = p["def"]
        
        # Merge into kwargs if not already provided
        kwargs.setdefault("params_schema", params_schema)
        kwargs.setdefault("config", config)
        kwargs.setdefault("params_values", initial_values)
        
        # Initialize internal state BEFORE observers or super()
        self._log_history = "" 
        self._log_lock = threading.Lock()
        self._last_sync_time = 0
        self._sync_threshold = 0.2 # 200ms
        
        super().__init__(**kwargs)
        self._setup_observers()
        
        # Start keepalive if in Colab
        if check_colab():
            keep_alive_thread()
            
    def _append_log(self, text: str):
        msg = str(text)
        with self._log_lock:
            self._log_history += msg
            # Note: We no longer sync to the 'logs' traitlet in real-time.
            # Instead, we rely strictly on Polling and the final Finish signal.
            # This prevents race conditions in high-latency environments.
            
        # File debug
        try:
            with open("pipeline_debug.log", "a") as f:
                f.write(msg)
        except:
            pass
        
    def _setup_observers(self):
        self.observe(self._on_run_requested, names=["run_requested"])
        self.observe(self._on_terminate_requested, names=["terminate_requested"])
        self.observe(self._on_action_requested, names=["action_requested"])
        self.on_msg(self._handle_custom_msg)

    def _on_terminate_requested(self, change):
        if not change.new: return
        self.terminate_requested = False
        
        self.logs = (self.logs or "") + "\n❯ Terminating pipeline...\n"
        self.pipeline.terminate()
        self.status_state = "aborted"
        self.status_message = "Terminated by user"
        
    def _on_run_requested(self, change):
        if not change.new: 
            return
        
        # Reset flag
        self.run_requested = False
        
        self.status_state = "running"
        self.status_message = "Pipeline running..."
        
        with self._log_lock:
            self._log_history = ""
            self.logs = "" 
            
        self.result_file_data = "" # Clear previous result
        self.result_file_name = ""
        
        def run_thread():
            # Clear debug file on new run
            with open("pipeline_debug.log", "w") as f:
                f.write("--- NEW RUN ---\n")
                
            try:
                # Use our new professional logger
                logger = PipelineLogger(self._append_log)
                
                from contextlib import redirect_stderr, redirect_stdout
                import base64
                
                with redirect_stdout(logger), redirect_stderr(logger):
                    logger.stage("Starting Pipeline")
                    success = self.pipeline.run(self.params_values, logger)
                
                if success:
                    logger.success("Completed successfully!")
                    self.status_state = "finished"
                    self.status_message = "Completed successfully"
                elif getattr(self.pipeline, "_stop_requested", False):
                    logger.warning("Pipeline was terminated.")
                    self.status_state = "aborted"
                    self.status_message = "Terminated by user"
                else:
                    logger.error("Pipeline failed.")
                    self.status_state = "error"
                    self.status_message = "Failed"
                    
            except Exception as e:
                import traceback
                trace = traceback.format_exc()
                self._append_log(f"\n✘ Critical Exception: {e}\n{trace}\n")
                self.status_state = "error"
                self.status_message = f"Error: {e}"
            
            finally:
                # 1. Dispatch final logs and status IMMEDIATELY
                with self._log_lock:
                    final_logs = self._log_history
                    self.logs = final_logs # Sync traitlet
                
                self.send({
                    "type": "run_finished", 
                    "status": self.status_state,
                    "logs": final_logs
                })
                
                # 2. Heavy result file processing AFTER the UI is notified of completion
                if self.status_state == "finished":
                    try:
                        project_name = self.params_values.get("output_name", "phage_project")
                        zip_path = Path.cwd() / f"{project_name}_results.zip"
                        if zip_path.exists():
                            size_mb = zip_path.stat().st_size / (1024 * 1024)
                            if size_mb > 50:
                                logger.warning(f"File is too large ({size_mb:.1f}MB) for widget download. Please use file explorer.")
                            else:
                                logger.info(f"Preparing download for {zip_path.name}...")
                                with open(zip_path, "rb") as f:
                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                    self.result_file_name = zip_path.name
                                    self.result_file_data = f"data:application/zip;base64,{b64_data}"
                                
                                # Send explicit message as backup for Colab traitlet lag
                                self.send({
                                    "type": "result_ready",
                                    "name": self.result_file_name,
                                    "data": self.result_file_data
                                })
                                logger.success("Download ready.")
                    except Exception as e:
                        logger.error(f"Error preparing download: {e}")
        
        # Run in thread to not block UI
        threading.Thread(target=run_thread, daemon=True).start()

    def _handle_custom_msg(self, content, buffers):
        """Handle incoming messages from JS (Polling)."""
        if content.get("type") == "poll":
            start_offset = content.get("offset", 0)
            
            with self._log_lock:
                total_len = len(self._log_history)
                
                # Always return current status and total offset
                # This bypasses traitlet sync lag in Colab
                msg = {
                    "type": "log_batch",
                    "content": "",
                    "new_offset": total_len,
                    "status": self.status_state
                }
                
                if start_offset < total_len:
                    msg["content"] = self._log_history[start_offset:]
                
                self.send(msg)


    def _on_action_requested(self, change):
        if not change.new: 
            return
        action_name = change.new
        
        # Reset flag
        self.action_requested = ""
        
        self.status_state = "running"
        with self._log_lock:
            self._log_history = ""
            self.logs = ""
            
        def _target(action_name):
            logger = PipelineLogger(self._append_log)
            logger.stage(f"Executing action: {action_name}")
            try:
                success = self.pipeline.handle_action(action_name, logger)
                self.status_state = "idle" if success else "error"
            except Exception as e:
                logger.error(f"Action error: {str(e)}")
                self.status_state = "error"
            finally:
                # Wrap up
                import time
                time.sleep(0.1)
                with self._log_lock:
                    final_logs = self._log_history
                    self.logs = final_logs
                    
                self.send({
                    "type": "run_finished", 
                    "status": self.status_state,
                    "logs": final_logs,
                    "result_file_name": self.result_file_name,
                    "result_file_data": self.result_file_data
                })

        threading.Thread(target=_target, args=(action_name,), daemon=True).start()

def create_launcher(pipeline: Pipeline) -> PipelineWidget:
    """Helper to create the widget."""
    return PipelineWidget(pipeline)
