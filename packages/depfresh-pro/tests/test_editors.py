"""Unit tests for each manifest editor (format-preserving version bumps)."""

from __future__ import annotations

from depfresh_pro.editors.dotnet import (
    DirectoryPackagesPropsEditor,
    PackagesConfigEditor,
    ProjectFileEditor,
)
from depfresh_pro.editors.golang import GoModEditor
from depfresh_pro.editors.java import GradleEditor, PomXmlEditor
from depfresh_pro.editors.node import PackageJsonEditor
from depfresh_pro.editors.php import ComposerJsonEditor
from depfresh_pro.editors.python import PipfileEditor, PyprojectEditor, RequirementsTxtEditor
from depfresh_pro.editors.registry import find_editor
from depfresh_pro.editors.ruby import GemfileEditor
from depfresh_pro.editors.rust import CargoTomlEditor

# Re-parse helpers to confirm the bumped text round-trips to the new version.
from depfresh.parsers.golang import GoModParser
from depfresh.parsers.java import GradleParser, PomXmlParser
from depfresh.parsers.node import PackageJsonParser
from depfresh.parsers.php import ComposerJsonParser
from depfresh.parsers.python import PyprojectParser, RequirementsTxtParser
from depfresh.parsers.ruby import GemfileParser
from depfresh.parsers.rust import CargoTomlParser


def _ver(parser, text, name):
    return {d.name: d.version for d in parser.parse(text)}[name]


def test_requirements_editor_preserves_comment():
    text = "requests==2.28.1  # pinned\nflask>=2.0\n"
    new, changed = RequirementsTxtEditor().apply(text, "requests", "==2.28.1", "2.31.0")
    assert changed
    assert "requests==2.31.0  # pinned" in new
    assert "flask>=2.0" in new  # untouched
    assert _ver(RequirementsTxtParser(), new, "requests") == "==2.31.0"


def test_requirements_editor_case_insensitive_name():
    text = "Flask-SQLAlchemy==1.0\n"
    new, changed = RequirementsTxtEditor().apply(text, "flask-sqlalchemy", "==1.0", "2.0.0")
    assert changed
    assert "Flask-SQLAlchemy==2.0.0" in new


def test_requirements_editor_skips_range_bump_crossing_upper_bound():
    # Bumping the lower bound past the upper one would be unsatisfiable.
    text = "flask>=1.0,<2.0\n"
    new, changed = RequirementsTxtEditor().apply(text, "flask", ">=1.0,<2.0", "2.5.0")
    assert changed is False
    assert new == text
    # In-bounds: the lower bound is raised, the upper bound is preserved.
    new2, changed2 = RequirementsTxtEditor().apply(text, "flask", ">=1.0,<2.0", "1.5.0")
    assert changed2 and new2 == "flask>=1.5.0,<2.0\n"


def test_requirements_editor_preserves_newline_on_non_final_line():
    text = "requests==2.0.0\nflask==1.0.0\n"
    new, changed = RequirementsTxtEditor().apply(text, "requests", "==2.0.0", "2.31.0")
    assert changed
    assert new == "requests==2.31.0\nflask==1.0.0\n"  # lines not merged


def test_pyproject_editor_pep621_and_poetry():
    text = (
        "[project]\n"
        'dependencies = ["requests>=2.0", "click"]\n'
        "[tool.poetry.dependencies]\n"
        'httpx = "^0.27"\n'
        'tokio = { version = "1.0", optional = true }\n'
    )
    new, changed = PyprojectEditor().apply(text, "requests", ">=2.0", "2.31.0")
    assert changed and "requests>=2.31.0" in new
    new2, _ = PyprojectEditor().apply(new, "httpx", "^0.27", "0.28.0")
    assert 'httpx = "^0.28.0"' in new2
    new3, _ = PyprojectEditor().apply(new2, "tokio", "1.0", "1.5.0")
    assert 'version = "1.5.0"' in new3
    assert _ver(PyprojectParser(), new3, "requests") == ">=2.31.0"


def test_pipfile_editor():
    text = "[packages]\nrequests = '>=2.0'\n"
    new, changed = PipfileEditor().apply(text, "requests", ">=2.0", "2.31.0")
    assert changed and "requests = '>=2.31.0'" in new


def test_package_json_editor():
    text = '{\n  "dependencies": {"react": "^18.2.0", "lodash": "4.17.21"}\n}\n'
    new, changed = PackageJsonEditor().apply(text, "react", "^18.2.0", "19.0.0")
    assert changed
    assert '"react": "^19.0.0"' in new
    assert '"lodash": "4.17.21"' in new
    assert _ver(PackageJsonParser(), new, "react") == "^19.0.0"


def test_cargo_editor_string_and_inline_table():
    text = '[dependencies]\nserde = "1.0"\ntokio = {version = "1.28", features = ["full"]}\n'
    new, changed = CargoTomlEditor().apply(text, "serde", "1.0", "1.1.0")
    assert changed and 'serde = "1.1.0"' in new
    new2, changed2 = CargoTomlEditor().apply(new, "tokio", "1.28", "1.35.0")
    assert changed2 and 'version = "1.35.0"' in new2
    assert 'features = ["full"]' in new2
    assert _ver(CargoTomlParser(), new2, "tokio") == "1.35.0"


def test_gomod_editor_keeps_v_prefix_and_comment():
    text = "require (\n\tgithub.com/gin-gonic/gin v1.9.1 // direct\n)\n"
    new, changed = GoModEditor().apply(text, "github.com/gin-gonic/gin", "v1.9.1", "v1.10.0")
    assert changed
    assert "github.com/gin-gonic/gin v1.10.0 // direct" in new
    assert _ver(GoModParser(), new, "github.com/gin-gonic/gin") == "v1.10.0"


def test_pom_editor():
    text = (
        "<project><dependencies>"
        "<dependency><groupId>org.springframework</groupId>"
        "<artifactId>spring-core</artifactId><version>6.0.0</version></dependency>"
        "</dependencies></project>"
    )
    new, changed = PomXmlEditor().apply(text, "org.springframework:spring-core", "6.0.0", "6.1.0")
    assert changed and "<version>6.1.0</version>" in new
    assert _ver(PomXmlParser(), new, "org.springframework:spring-core") == "6.1.0"


def test_gradle_editor():
    text = "dependencies {\n    implementation 'com.google.guava:guava:31.1-jre'\n}\n"
    new, changed = GradleEditor().apply(text, "com.google.guava:guava", "31.1-jre", "33.0.0")
    assert changed and "com.google.guava:guava:33.0.0" in new
    assert _ver(GradleParser(), new, "com.google.guava:guava") == "33.0.0"


def test_csproj_editor_attr_and_child():
    text = (
        "<Project><ItemGroup>"
        '<PackageReference Include="Newtonsoft.Json" Version="13.0.1" />'
        '<PackageReference Include="Serilog"><Version>2.10.0</Version></PackageReference>'
        "</ItemGroup></Project>"
    )
    new, changed = ProjectFileEditor().apply(text, "Newtonsoft.Json", "13.0.1", "13.0.3")
    assert changed and 'Version="13.0.3"' in new
    new2, changed2 = ProjectFileEditor().apply(new, "Serilog", "2.10.0", "3.1.1")
    assert changed2 and "<Version>3.1.1</Version>" in new2


def test_packages_config_and_props_editors():
    cfg = '<packages><package id="NUnit" version="3.13.2" /></packages>'
    new, changed = PackagesConfigEditor().apply(cfg, "NUnit", "3.13.2", "4.0.1")
    assert changed and 'version="4.0.1"' in new

    props = '<Project><ItemGroup><PackageVersion Include="Serilog" Version="2.10.0" /></ItemGroup></Project>'
    new2, changed2 = DirectoryPackagesPropsEditor().apply(props, "Serilog", "2.10.0", "3.1.1")
    assert changed2 and 'Version="3.1.1"' in new2


def test_composer_editor():
    text = '{\n  "require": {"monolog/monolog": "^3.0"}\n}\n'
    new, changed = ComposerJsonEditor().apply(text, "monolog/monolog", "^3.0", "3.5.0")
    assert changed and '"monolog/monolog": "^3.5.0"' in new
    assert _ver(ComposerJsonParser(), new, "monolog/monolog") == "^3.5.0"


def test_gemfile_editor():
    text = 'gem "rails", "~> 7.0.4"\ngem "pg"\n'
    new, changed = GemfileEditor().apply(text, "rails", "~> 7.0.4", "7.1.0")
    assert changed
    assert 'gem "rails", "~> 7.1.0"' in new
    assert 'gem "pg"' in new
    assert _ver(GemfileParser(), new, "rails") == "~> 7.1.0"


def test_gemfile_editor_skips_range_bump_crossing_upper_bound():
    text = 'gem "foo", ">= 1.0", "< 2.0"\n'
    new, changed = GemfileEditor().apply(text, "foo", ">= 1.0", "2.5.0")
    assert changed is False
    assert new == text
    # In-bounds bump raises the lower requirement, leaves the upper one.
    new2, changed2 = GemfileEditor().apply(text, "foo", ">= 1.0", "1.5.0")
    assert changed2 and new2 == 'gem "foo", ">= 1.5.0", "< 2.0"\n'


def test_no_change_returns_false():
    text = '{"dependencies": {"react": "^18.0.0"}}'
    _, changed = PackageJsonEditor().apply(text, "missing-pkg", None, "1.0.0")
    assert changed is False


def test_find_editor_skips_lockfiles():
    assert find_editor("package.json") is not None
    assert find_editor("requirements.txt") is not None
    assert find_editor("pyproject.toml") is not None
    # Lockfiles deliberately have no editor.
    assert find_editor("package-lock.json") is None
    assert find_editor("poetry.lock") is None
    assert find_editor("Cargo.lock") is None
    assert find_editor("Gemfile.lock") is None
