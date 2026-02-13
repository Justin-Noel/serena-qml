import logging
import os
import pathlib
import subprocess
from typing import cast

from overrides import override

from solidlsp.ls import SolidLanguageServer
from solidlsp.ls_config import LanguageServerConfig
from solidlsp.lsp_protocol_handler.lsp_types import InitializeParams
from solidlsp.lsp_protocol_handler.server import ProcessLaunchInfo
from solidlsp.settings import SolidLSPSettings

log = logging.getLogger(__name__)


class QmlLanguageServer(SolidLanguageServer):
    """
    Provides QML specific instantiation of the LanguageServer class using qmlls.
    """

    @override
    def is_ignored_dirname(self, dirname: str) -> bool:
        return super().is_ignored_dirname(dirname) or dirname in ["build", "node_modules"]

    @staticmethod
    def _get_qmlls_version() -> str | None:
        """Get the installed qmlls version or None if not found."""
        try:
            result = subprocess.run(["qmlls", "--help"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip() or "qmlls available"
        except FileNotFoundError:
            return None
        return None

    @staticmethod
    def _setup_runtime_dependency() -> bool:
        """
        Check if required QML runtime dependencies are available.
        Raises RuntimeError with helpful message if dependencies are missing.
        """
        qmlls_version = QmlLanguageServer._get_qmlls_version()
        if not qmlls_version:
            raise RuntimeError(
                "qmlls is not installed or not on PATH.\n"
                "qmlls is part of the Qt framework. Please install Qt 6.x and ensure qmlls is on your PATH.\n"
                "It is typically found at <Qt install dir>/<version>/<platform>/bin/qmlls."
            )

        return True

    def __init__(self, config: LanguageServerConfig, repository_root_path: str, solidlsp_settings: SolidLSPSettings) -> None:
        """
        Creates a QmlLanguageServer instance.

        Supported ls_specific_settings for QML:
            build_dir: str - Path to the build directory (passed as --build-dir to qmlls).
                qmlls uses this to find compiled QML type information.
            import_paths: list[str] - Additional QML import paths (each passed as -I to qmlls).
            use_environment_import_paths: bool - If True, passes -E to qmlls so it reads
                import paths from the QML_IMPORT_PATH environment variable.
            no_cmake_calls: bool - If True, passes --no-cmake-calls to disable automatic
                CMake rebuilds when C++ QML types change.
            doc_dir: str - Path to the Qt documentation directory (passed as -d to qmlls)
                for hover documentation support.
        """
        self._setup_runtime_dependency()

        cmd: list[str] = ["qmlls"]

        # Read qml-specific settings
        qml_settings = solidlsp_settings.get_ls_specific_settings(config.code_language)

        build_dir = qml_settings.get("build_dir")
        if build_dir:
            if not os.path.isabs(build_dir):
                build_dir = os.path.join(repository_root_path, build_dir)
            cmd.extend(["--build-dir", build_dir])

        import_paths = qml_settings.get("import_paths")
        if import_paths:
            for import_path in import_paths:
                if not os.path.isabs(import_path):
                    import_path = os.path.join(repository_root_path, import_path)
                cmd.extend(["-I", import_path])

        if qml_settings.get("use_environment_import_paths"):
            cmd.append("-E")

        if qml_settings.get("no_cmake_calls"):
            cmd.append("--no-cmake-calls")

        doc_dir = qml_settings.get("doc_dir")
        if doc_dir:
            if not os.path.isabs(doc_dir):
                doc_dir = os.path.join(repository_root_path, doc_dir)
            cmd.extend(["-d", doc_dir])

        super().__init__(config, repository_root_path, ProcessLaunchInfo(cmd=cmd, cwd=repository_root_path), "qml", solidlsp_settings)
        self.request_id = 0

    def _get_initialize_params(self, repository_absolute_path: str) -> InitializeParams:
        """
        Returns the initialize params for the QML Language Server.
        """
        root_uri = pathlib.Path(repository_absolute_path).as_uri()
        initialize_params: dict = {
            "locale": "en",
            "capabilities": {
                "textDocument": {
                    "synchronization": {"didSave": True, "dynamicRegistration": True},
                    "definition": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "dynamicRegistration": True,
                        "hierarchicalDocumentSymbolSupport": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                },
                "workspace": {"workspaceFolders": True, "didChangeConfiguration": {"dynamicRegistration": True}},
            },
            "processId": os.getpid(),
            "rootPath": repository_absolute_path,
            "rootUri": root_uri,
            "workspaceFolders": [
                {
                    "uri": root_uri,
                    "name": os.path.basename(repository_absolute_path),
                }
            ],
        }

        return cast(InitializeParams, initialize_params)

    def _start_server(self) -> None:
        """Start qmlls server process"""

        def register_capability_handler(params: dict) -> None:
            return

        def window_log_message(msg: dict) -> None:
            log.info(f"LSP: window/logMessage: {msg}")

        def do_nothing(params: dict) -> None:
            return

        self.server.on_request("client/registerCapability", register_capability_handler)
        self.server.on_notification("window/logMessage", window_log_message)
        self.server.on_notification("$/progress", do_nothing)
        self.server.on_notification("textDocument/publishDiagnostics", do_nothing)

        log.info("Starting qmlls server process")
        self.server.start()
        initialize_params = self._get_initialize_params(self.repository_root_path)

        log.info("Sending initialize request from LSP client to LSP server and awaiting response")
        init_response = self.server.send.initialize(initialize_params)

        assert "textDocumentSync" in init_response["capabilities"]

        self.server.notify.initialized({})
