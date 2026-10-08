"""Trusted local module configuration, independent of Flask or network access."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SCHEMA_FILES = (
    "core-schema.ttl", "mv-schema.ttl", "agent-schema.ttl", "devops-schema.ttl",
    "ecommerce-schema.ttl", "healthcare-schema.ttl", "academic-schema.ttl", "controlled-vocabularies.ttl",
)
DEFAULT_EXTERNAL_IMPORTS = ("http://www.w3.org/ns/prov-o#",)


def local_path(root, filename):
    root = Path(root).resolve()
    candidate = Path(filename)
    path = (root / candidate).resolve()
    if candidate.is_absolute() or not path.is_relative_to(root) or path == root:
        raise ValueError("Module paths must remain inside the configured root")
    return path


def read_registry(root=ROOT):
    root = Path(root).resolve()
    path = root / "ontology_modules.json"
    if path.exists():
        if not path.resolve().is_relative_to(root):
            raise ValueError("Module registry escapes its root")
        registry = json.loads(path.read_text(encoding="utf-8"))
        if registry.get("format_version") != 1 or not isinstance(registry.get("modules"), list):
            raise ValueError("Unsupported ontology module registry")
        from ontology_catalog import custom_modules
        registry['modules'].extend(custom_modules(root))
        names = [module["schema"] for module in registry["modules"]]
        if len(names) != len(set(names)):
            raise ValueError("Module schema paths must be unique")
        for module in registry["modules"]:
            local_path(root, module["schema"])
            for key in ('example', 'questions', 'questions_fixture', 'question_answers', 'compatibility_cases'):
                if module.get(key):
                    local_path(root, module[key])
            for name in module.get("shapes", []):
                local_path(root, name)
        for name in registry.get("shared_shapes", []):
            local_path(root, name)
        return registry
    # Minimal standalone/test roots can supply only their own local modules.
    names = sorted({path.name for path in root.glob("*-schema.ttl")} |
                   ({"controlled-vocabularies.ttl"} if (root / "controlled-vocabularies.ttl").is_file() else set()))
    from ontology_catalog import custom_modules
    return {"format_version": 1, "modules": [{"schema": name, "shapes": []} for name in names] + custom_modules(root),
            "external_imports": list(DEFAULT_EXTERNAL_IMPORTS),
            "shared_shapes": [name for name in ("core-shapes.ttl", "property-contract-shapes.ttl") if (root / name).is_file()],
            "strict_declarations": False}


def schema_files(root=ROOT):
    modules = read_registry(root)['modules']
    return tuple(module['schema'] for module in modules) if modules else DEFAULT_SCHEMA_FILES
