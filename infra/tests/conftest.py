"""Helpers for the offline template checks: load a CloudFormation template, pick its resources, run cfn-lint.

The checks pin the design's security, cost and naming rules (no NAT gateway, a private database, the
firewall rules, ...) so a template change that breaks one fails here, before anything reaches AWS.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


class _CfnLoader(yaml.SafeLoader):
    """A safe YAML loader that understands CloudFormation's short-form tags (!Ref, !Sub, !GetAtt, ...)."""


def _long_form(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    if tag_suffix == "Ref":
        return {"Ref": value}
    if tag_suffix == "GetAtt" and isinstance(value, str):
        return {"Fn::GetAtt": value.split(".", 1)}
    return {f"Fn::{tag_suffix}": value}


_CfnLoader.add_multi_constructor("!", _long_form)


def load_template(name: str) -> dict:
    """infra/templates/<name>.yaml as a dict, with short-form tags turned into their long form."""
    with open(TEMPLATES / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.load(f, Loader=_CfnLoader)


def resources(template: dict, type_: str) -> dict[str, dict]:
    """Logical ID -> resource, for every resource of one type."""
    return {lid: res for lid, res in template.get("Resources", {}).items() if res.get("Type") == type_}


_NAME_KEYS = ("Name", "Identifier", "Family")
_REFERENCES = {"Ref", "Fn::GetAtt", "Fn::ImportValue", "Fn::Select"}


def name_properties(template: dict, exempt: frozenset[str] = frozenset()) -> list[tuple[str, str, object]]:
    """(logical ID, property, value) for every name a resource defines: top-level properties ending in
    Name/Identifier/Family, plus CachePolicyConfig.Name and OriginAccessControlConfig.Name. References to
    other resources (Ref, GetAtt, ...) are skipped: they name something defined elsewhere. Nested keys such
    as container or environment-variable names aren't resource names and aren't included."""
    found = []
    for lid, res in template.get("Resources", {}).items():
        props = res.get("Properties", {})
        candidates = [(key, value) for key, value in props.items() if key.endswith(_NAME_KEYS) and key not in exempt]
        for nested in ("CachePolicyConfig", "OriginAccessControlConfig"):
            if "Name" in props.get(nested, {}):
                candidates.append((f"{nested}.Name", props[nested]["Name"]))
        for key, value in candidates:
            if isinstance(value, dict) and set(value) & _REFERENCES:
                continue
            found.append((lid, key, value))
    return found


def sub_text(value: object) -> str:
    """The template string of a Fn::Sub (short or list form), or '' for anything else."""
    if isinstance(value, dict) and "Fn::Sub" in value:
        sub = value["Fn::Sub"]
        return sub if isinstance(sub, str) else sub[0]
    return ""


def cfn_lint(name: str) -> None:
    """cfn-lint must report no errors or warnings (exit code 8 means informational notes only)."""
    path = TEMPLATES / f"{name}.yaml"
    cfn_lint_exe = shutil.which("cfn-lint", path=str(Path(sys.executable).parent))  # the venv's cfn-lint
    assert cfn_lint_exe, "cfn-lint isn't installed: infra/.venv/Scripts/python -m pip install -r infra/requirements-dev.txt"
    # The template goes first: --regions takes several values and would swallow a path after it.
    result = subprocess.run([cfn_lint_exe, str(path), "--regions", "ap-northeast-1"], capture_output=True, text=True)
    assert result.returncode in (0, 8), result.stdout + result.stderr
