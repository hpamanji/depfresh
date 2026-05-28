"""Editors for .NET (NuGet) manifests."""

from __future__ import annotations

from depfresh_pro.editors.base import EditResult, Editor, replace_dotnet_dependency


class ProjectFileEditor(Editor):
    ecosystem = "dotnet"
    patterns = ("*.csproj", "*.fsproj", "*.vbproj")

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_dotnet_dependency(text, name, latest)


class DirectoryPackagesPropsEditor(Editor):
    ecosystem = "dotnet"
    filenames = ("Directory.Packages.props",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_dotnet_dependency(text, name, latest)


class PackagesConfigEditor(Editor):
    ecosystem = "dotnet"
    filenames = ("packages.config",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_dotnet_dependency(text, name, latest)
