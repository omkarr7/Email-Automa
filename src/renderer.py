from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from .config import ROOT

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render(template, context):
    return env.get_template(template).render(**context)
