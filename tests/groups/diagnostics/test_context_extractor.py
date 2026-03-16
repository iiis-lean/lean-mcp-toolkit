from lean_mcp_toolkit.contracts.diagnostics import Position
from lean_mcp_toolkit.groups.diagnostics.parsing import ContextExtractor



def test_extract_context_window() -> None:
    src = "line1\nline2\nline3\nline4\nline5"
    extractor = ContextExtractor()
    snippet = extractor.extract(
        source_text=src,
        start_pos=Position(line=3, column=0),
        end_pos=Position(line=3, column=2),
        context_lines=1,
    )
    assert snippet == "line2\nline3\nline4"
