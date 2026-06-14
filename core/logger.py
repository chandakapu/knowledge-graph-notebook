import logging
import sys

def setup_logging(level=logging.INFO):
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root = logging.getLogger("langextract")
    root.setLevel(level)
    
    # Remove existing handlers to avoid double logging in some environments
    for h in list(root.handlers):
        root.removeHandler(h)
        
    root.addHandler(handler)
    root.propagate = False
    return root
