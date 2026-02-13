from pathlib import Path

import pytest

from solidlsp import SolidLanguageServer
from solidlsp.ls_config import Language


@pytest.mark.qml
class TestQmlLanguageServer:
    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.QML], indirect=True)
    def test_ls_is_running(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that the QML language server starts and stops successfully."""
        assert language_server.is_running()
        assert Path(language_server.language_server.repository_root_path).resolve() == repo_path.resolve()

    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    def test_find_symbols(self, language_server: SolidLanguageServer) -> None:
        """Test that document symbols can be found in QML files."""
        symbols = language_server.request_full_symbol_tree()
        assert len(symbols) > 0, "Expected at least some symbols from QML files"

    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.QML], indirect=True)
    def test_document_symbols_main(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that document symbols are returned for Main.qml."""
        doc_symbols = language_server.request_document_symbols("Main.qml")
        all_symbols = doc_symbols.get_all_symbols_and_roots()
        symbol_names = [s.get("name", "") for s in all_symbols[0]]
        assert len(symbol_names) > 0, "Expected symbols in Main.qml but got none"

    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.QML], indirect=True)
    def test_document_symbols_helper(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test that document symbols are returned for Helper.qml."""
        doc_symbols = language_server.request_document_symbols("Helper.qml")
        all_symbols = doc_symbols.get_all_symbols_and_roots()
        symbol_names = [s.get("name", "") for s in all_symbols[0]]
        assert len(symbol_names) > 0, "Expected symbols in Helper.qml but got none"

    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.QML], indirect=True)
    def test_find_definition_within_file(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test finding the definition of a property usage within the same file."""
        # In Main.qml (0-indexed lines):
        # Line 8: property string greeting: "Hello, QML!"
        # Line 18: text: root.greeting
        # "greeting" at line 18, character 19 (8 spaces + "text: root." = 19)
        definition_location_list = language_server.request_definition("Main.qml", 18, 19)

        assert definition_location_list, f"Expected definition for 'greeting' but got {definition_location_list=}"
        assert len(definition_location_list) >= 1
        definition_location = definition_location_list[0]
        assert definition_location["uri"].endswith("Main.qml")
        # The property declaration is on line 8 (0-indexed)
        assert definition_location["range"]["start"]["line"] == 8

    @pytest.mark.parametrize("language_server", [Language.QML], indirect=True)
    @pytest.mark.parametrize("repo_path", [Language.QML], indirect=True)
    def test_find_references_within_file(self, language_server: SolidLanguageServer, repo_path: Path) -> None:
        """Test finding references to a property within the same file."""
        # In Main.qml (0-indexed lines):
        # Line 9: property int counter: 0
        # "counter" starts at character 17 (4 spaces + "property int " = 17)
        references = language_server.request_references("Main.qml", 9, 17)

        assert references, f"Expected references for 'counter' but got {references=}"

        ref_lines = [ref["range"]["start"]["line"] for ref in references]
        # counter is used in increment() on line 12 and in onClicked on line 25
        # At minimum we expect more than one reference location
        assert len(ref_lines) >= 2, f"Expected at least 2 references for 'counter', got {ref_lines}"
