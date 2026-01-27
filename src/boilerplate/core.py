from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class PipelineParameter:
    """Definition of a pipeline parameter for the UI."""
    name: str
    type: str  # text, int, float, bool, select, multiselect, switch, file, textarea
    label: str
    description: str = ""
    default: Any = None
    options: Optional[List[str]] = None  # For select/multiselect
    category: str = "General"
    modes: Optional[List[str]] = None  # Listing modes where this param is visible
    colab_only: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization to widget."""
        d = {
            "name": self.name,
            "type": self.type,
            "label": self.label,
            "desc": self.description,
            "def": self.default,
        }
        if self.options is not None:
            d["options"] = self.options
        if self.category:
            d["category"] = self.category
        if self.modes:
            d["modes"] = self.modes
        if self.colab_only:
            d["colab_only"] = self.colab_only
        return d

@dataclass
class PipelineConfig:
    """Configuration for the pipeline wrapper."""
    name: str = "Pipeline"
    title: str = "Pipeline Launcher"
    subtitle: str = "Generic Pipeline Launcher"
    modes: List[str] = field(default_factory=lambda: ["single"])
    categories: Dict[str, Dict[str, Any]] = field(default_factory=dict) # category_name -> metadata

class Pipeline(ABC):
    """Abstract base class for a pipeline."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.parameters: List[PipelineParameter] = self.define_parameters()
    
    @abstractmethod
    def define_parameters(self) -> List[PipelineParameter]:
        """Define the parameters for this pipeline."""
        pass
    
    @abstractmethod
    def run(self, params: Dict[str, Any], logger) -> bool:
        """Run the pipeline with the given parameters."""
        pass

    def handle_action(self, action_name: str, logger) -> bool:
        """Handle a custom action (e.g., database installation).
        
        Default implementation does nothing. Override in subclasses.
        """
        logger.write(f"Executed action: {action_name} (no handler implemented)\n")
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the full schema to send to the widget."""

        grouped_params = {}
        
        for p in self.parameters:
            cat = p.category
            if cat not in grouped_params:
                grouped_params[cat] = []
            grouped_params[cat].append(p.to_dict())
            
        return {
            "parameters": grouped_params,
            "config": {
                "name": self.config.name,
                "title": self.config.title,
                "subtitle": self.config.subtitle,
                "modes": self.config.modes,
                "category_styles": self.config.categories
            }
        }
