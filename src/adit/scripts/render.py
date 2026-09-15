
from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined

from adit import lang
from adit import __version__
from adit.config import Profile
from adit.spec import CalculationSpec

_env = Environment(
    loader=PackageLoader("adit.scripts", "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

TEMPLATE_OF_KIND = {"direct": "direct.sh.j2", "pbs": "pbs.sh.j2", "slurm": "slurm.sh.j2"}


def render_submit(spec: CalculationSpec, profile: Profile, run_command: str) -> str:
    tmpl = _env.get_template(TEMPLATE_OF_KIND[profile.kind])
    return tmpl.render(
        runtime=spec.runtime, profile=profile, run_command=run_command,
        modules=profile.modules_for(spec.method.code), env=profile.env,
        app_version=__version__, created=spec.meta.created, lang=lang.LANGUAGE,
    )
