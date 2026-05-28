"""Unit tests for each ecosystem parser."""

from __future__ import annotations

from depfresh.parsers.dotnet import (
    DirectoryPackagesPropsParser,
    PackagesConfigParser,
    PackagesLockJsonParser,
    ProjectFileParser,
)
from depfresh.parsers.golang import GoModParser
from depfresh.parsers.java import GradleParser, PomXmlParser
from depfresh.parsers.node import PackageJsonParser, PackageLockParser
from depfresh.parsers.php import ComposerJsonParser, ComposerLockParser
from depfresh.parsers.python import (
    PipfileParser,
    PoetryLockParser,
    PyprojectParser,
    RequirementsTxtParser,
)
from depfresh.parsers.ruby import GemfileLockParser, GemfileParser
from depfresh.parsers.rust import CargoTomlParser


def as_map(deps):
    return {d.name: d for d in deps}


def test_requirements_txt():
    text = """
# a comment
requests==2.28.1
Django>=3.2,<4
flask
package[extra]~=1.0
uvicorn ; sys_platform == "win32"
-r other.txt
-e .
git+https://example.com/repo.git#egg=thing
"""
    deps = as_map(RequirementsTxtParser().parse(text))
    assert deps["requests"].version == "==2.28.1"
    assert deps["Django"].version == ">=3.2,<4"
    assert deps["flask"].version is None
    assert deps["package"].version == "~=1.0"
    assert deps["uvicorn"].version is None
    assert "thing" not in deps  # URL line skipped
    assert "other.txt" not in deps


def test_pyproject_pep621_and_poetry():
    text = """
[project]
dependencies = ["requests>=2.0", "click"]
[project.optional-dependencies]
dev = ["pytest>=7"]

[tool.poetry.dependencies]
python = "^3.11"
httpx = "^0.27"
[tool.poetry.group.dev.dependencies]
mypy = "1.10"
"""
    deps = PyprojectParser().parse(text)
    m = as_map(deps)
    assert m["requests"].version == ">=2.0"
    assert m["click"].version is None
    assert m["pytest"].scope == "optional"
    assert m["httpx"].version == "^0.27"
    assert "python" not in m  # poetry python constraint excluded
    assert m["mypy"].scope == "dev"


def test_pipfile():
    text = """
[packages]
requests = "*"
flask = {version = ">=2.0"}
[dev-packages]
pytest = "==7.4.0"
"""
    m = as_map(PipfileParser().parse(text))
    assert m["requests"].version is None  # "*" normalized to None
    assert m["flask"].version == ">=2.0"
    assert m["pytest"].scope == "dev"


def test_poetry_lock():
    text = """
[[package]]
name = "requests"
version = "2.28.1"

[[package]]
name = "pytest"
version = "7.4.0"
category = "dev"
"""
    m = as_map(PoetryLockParser().parse(text))
    assert m["requests"].version == "2.28.1"
    assert m["pytest"].scope == "dev"


def test_package_json():
    text = """
{
  "dependencies": {"react": "^18.2.0", "lodash": "4.17.21"},
  "devDependencies": {"jest": "^29.0.0"},
  "peerDependencies": {"react-dom": "^18.0.0"}
}
"""
    m = as_map(PackageJsonParser().parse(text))
    assert m["react"].version == "^18.2.0"
    assert m["jest"].scope == "dev"
    assert m["react-dom"].scope == "peer"


def test_package_lock_v3():
    text = """
{
  "lockfileVersion": 3,
  "packages": {
    "": {"name": "root"},
    "node_modules/react": {"version": "18.2.0"},
    "node_modules/jest": {"version": "29.0.0", "dev": true}
  }
}
"""
    m = as_map(PackageLockParser().parse(text))
    assert m["react"].version == "18.2.0"
    assert m["jest"].scope == "dev"
    assert "root" not in m


def test_go_mod():
    text = """
module example.com/foo

go 1.21

require github.com/single/dep v1.0.0

require (
    github.com/gin-gonic/gin v1.9.1
    golang.org/x/sys v0.10.0 // indirect
)
"""
    m = as_map(GoModParser().parse(text))
    assert m["github.com/single/dep"].version == "v1.0.0"
    assert m["github.com/gin-gonic/gin"].version == "v1.9.1"
    assert m["golang.org/x/sys"].scope == "indirect"


def test_cargo_toml():
    text = """
[dependencies]
serde = "1.0"
tokio = {version = "1.28", features = ["full"]}
[dev-dependencies]
criterion = "0.5"
"""
    m = as_map(CargoTomlParser().parse(text))
    assert m["serde"].version == "1.0"
    assert m["tokio"].version == "1.28"
    assert m["criterion"].scope == "dev"


def test_pom_xml():
    text = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>6.0.0</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""
    m = as_map(PomXmlParser().parse(text))
    assert m["org.springframework:spring-core"].version == "6.0.0"
    assert m["junit:junit"].scope == "test"


def test_gradle():
    text = """
dependencies {
    implementation 'com.google.guava:guava:31.1-jre'
    testImplementation("org.junit.jupiter:junit-jupiter:5.9.0")
    api 'org.apache.commons:commons-lang3'
}
"""
    m = as_map(GradleParser().parse(text))
    assert m["com.google.guava:guava"].version == "31.1-jre"
    assert m["org.junit.jupiter:junit-jupiter"].scope == "test"
    assert m["org.apache.commons:commons-lang3"].version is None


def test_gemfile():
    text = """
source "https://rubygems.org"
gem "rails", "~> 7.0.4"
gem "puma", ">= 5.0"
gem "pg"
group :development, :test do
  gem "rspec-rails", "6.0.0"
end
"""
    m = as_map(GemfileParser().parse(text))
    assert m["rails"].version == "~> 7.0.4"
    assert m["pg"].version is None
    assert m["rspec-rails"].scope == "test"


def test_gemfile_nested_block_keeps_group_scope():
    # A non-group do...end block (platforms) nested inside a group must not
    # leak its 'end' onto the group stack and drop the surrounding scope.
    text = """
group :test do
  gem "rspec"
  platforms :mri do
    gem "byebug"
  end
  gem "factory_bot"
end
gem "rails"
"""
    m = as_map(GemfileParser().parse(text))
    assert m["rspec"].scope == "test"
    assert m["byebug"].scope == "test"
    assert m["factory_bot"].scope == "test"
    assert m["rails"].scope == "runtime"


def test_requirements_txt_inline_hash_options():
    text = """
requests==2.28.1 --hash=sha256:deadbeef
flask==2.0  --hash=sha256:cafe --hash=sha256:f00d
"""
    m = as_map(RequirementsTxtParser().parse(text))
    assert m["requests"].version == "==2.28.1"
    assert m["flask"].version == "==2.0"


def test_gemfile_lock():
    text = """
GEM
  remote: https://rubygems.org/
  specs:
    actionpack (7.0.4)
      actionview (= 7.0.4)
    rake (13.0.6)

PLATFORMS
  ruby
"""
    m = as_map(GemfileLockParser().parse(text))
    assert m["actionpack"].version == "7.0.4"
    assert m["rake"].version == "13.0.6"
    assert "actionview" not in m  # nested transitive dep (6-space indent)


def test_composer_json():
    text = """
{
  "require": {"php": ">=8.1", "monolog/monolog": "^3.0", "ext-json": "*"},
  "require-dev": {"phpunit/phpunit": "^10.0"}
}
"""
    m = as_map(ComposerJsonParser().parse(text))
    assert m["monolog/monolog"].version == "^3.0"
    assert m["phpunit/phpunit"].scope == "dev"
    assert "php" not in m
    assert "ext-json" not in m


def test_csproj_sdk_style():
    text = """<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageReference Include="Serilog">
      <Version>2.10.0</Version>
    </PackageReference>
    <PackageReference Include="Microsoft.Extensions.Logging" />
    <ProjectReference Include="../Other/Other.csproj" />
  </ItemGroup>
</Project>
"""
    m = as_map(ProjectFileParser().parse(text))
    assert m["Newtonsoft.Json"].version == "13.0.1"
    assert m["Serilog"].version == "2.10.0"  # child <Version> element
    assert m["Microsoft.Extensions.Logging"].version is None  # CPM-managed
    assert "../Other/Other.csproj" not in m  # ProjectReference ignored


def test_csproj_legacy_namespace():
    text = """<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup>
    <PackageReference Include="NUnit" Version="3.13.2" />
  </ItemGroup>
</Project>
"""
    m = as_map(ProjectFileParser().parse(text))
    assert m["NUnit"].version == "3.13.2"


def test_packages_config():
    text = """<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="13.0.1" targetFramework="net472" />
  <package id="NUnit" version="3.13.2" developmentDependency="true" />
</packages>
"""
    m = as_map(PackagesConfigParser().parse(text))
    assert m["Newtonsoft.Json"].version == "13.0.1"
    assert m["NUnit"].scope == "dev"


def test_directory_packages_props():
    text = """<Project>
  <ItemGroup>
    <PackageVersion Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageVersion Include="Serilog" Version="2.10.0" />
  </ItemGroup>
</Project>
"""
    m = as_map(DirectoryPackagesPropsParser().parse(text))
    assert m["Newtonsoft.Json"].version == "13.0.1"
    assert m["Serilog"].version == "2.10.0"


def test_packages_lock_json():
    text = """
{
  "version": 1,
  "dependencies": {
    "net6.0": {
      "Newtonsoft.Json": {"type": "Direct", "requested": "[13.0.1, )", "resolved": "13.0.1"},
      "System.Buffers": {"type": "Transitive", "resolved": "4.5.1"}
    }
  }
}
"""
    m = as_map(PackagesLockJsonParser().parse(text))
    assert m["Newtonsoft.Json"].version == "13.0.1"
    assert m["System.Buffers"].scope == "indirect"


def test_composer_lock():
    text = """
{
  "packages": [{"name": "monolog/monolog", "version": "3.5.0"}],
  "packages-dev": [{"name": "phpunit/phpunit", "version": "10.5.0"}]
}
"""
    m = as_map(ComposerLockParser().parse(text))
    assert m["monolog/monolog"].version == "3.5.0"
    assert m["phpunit/phpunit"].scope == "dev"
