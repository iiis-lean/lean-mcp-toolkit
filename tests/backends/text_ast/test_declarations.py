from lean_mcp_toolkit.backends.text_ast import parse_declarations


def test_parse_declarations_supports_attributes_and_modifiers() -> None:
    parsed = parse_declarations(
        text="""import Mathlib

namespace Demo
/-- A documented theorem. -/
@[simp,
  grind]
private theorem hidden : True := by
  trivial

@[inline] protected noncomputable def Box.value : Nat := 1
unsafe def risky : Nat := 2
partial
def repeat (n : Nat) : Nat := repeat n
end Demo
""",
        module_dot="Demo",
    )

    assert [decl.name for decl in parsed.declarations] == [
        "Demo.hidden",
        "Demo.Box.value",
        "Demo.risky",
        "Demo.repeat",
    ]
    hidden = parsed.declarations[0]
    assert hidden.docstring == "/-- A documented theorem. -/"
    assert hidden.decl_start_pos is not None
    assert hidden.decl_start_pos.line == 4
    assert hidden.full_declaration is not None
    assert "@[simp," in hidden.full_declaration
    assert "private theorem hidden" in hidden.full_declaration
    assert parsed.declarations[-1].full_declaration is not None
    assert parsed.declarations[-1].full_declaration.startswith("partial\ndef repeat")
    assert parsed.coverage.unrecognized_commands == tuple()
    assert parsed.coverage.classification_ratio == 1.0


def test_parse_declarations_extracts_mutual_members_and_keeps_continuations() -> None:
    parsed = parse_declarations(
        text="""namespace Demo
mutual
  def even : Nat → Bool
    | 0 => true
    | n + 1 => odd n
  /-- The odd half. -/
  protected def odd : Nat → Bool
    | 0 => false
    | n + 1 => even n
end

def countdown (n : Nat) : Nat :=
  n
termination_by n
decreasing_by omega

theorem done : True := by
  trivial
end Demo
""",
        module_dot="Demo",
    )

    assert [decl.name for decl in parsed.declarations] == [
        "Demo.even",
        "Demo.odd",
        "Demo.countdown",
        "Demo.done",
    ]
    even, odd, countdown, _ = parsed.declarations
    assert even.decl_end_pos is not None and even.decl_end_pos.line == 5
    assert odd.docstring == "  /-- The odd half. -/"
    assert countdown.full_declaration is not None
    assert "termination_by n" in countdown.full_declaration
    assert "decreasing_by omega" in countdown.full_declaration
    assert parsed.coverage.unrecognized_commands == tuple()


def test_parse_declarations_reports_unrecognized_top_level_commands() -> None:
    parsed = parse_declarations(
        text="""import Mathlib
namespace Demo
custom_command payload
theorem ok : True := by
  trivial
end Demo
""",
        module_dot="Demo",
    )

    assert [decl.name for decl in parsed.declarations] == ["Demo.ok"]
    assert parsed.coverage.total_top_level_commands == 5
    assert parsed.coverage.classified_top_level_commands == 4
    assert parsed.coverage.classification_ratio == 0.8
    assert len(parsed.coverage.unrecognized_commands) == 1
    issue = parsed.coverage.unrecognized_commands[0]
    assert issue.line == 3
    assert issue.head == "custom_command"
    assert issue.source == "custom_command payload"


def test_parse_declarations_keeps_unindented_delimiter_continuations() -> None:
    parsed = parse_declarations(
        text="""lemma first : True :=
(by trivial)

def pair : Nat × Nat :=
{ fst := 1
  snd := 2 }

theorem last : True := by trivial
""",
        module_dot="Demo",
    )

    assert [decl.name for decl in parsed.declarations] == ["first", "pair", "last"]
    assert parsed.declarations[0].full_declaration is not None
    assert "(by trivial)" in parsed.declarations[0].full_declaration
    assert parsed.declarations[1].full_declaration is not None
    assert "{ fst := 1" in parsed.declarations[1].full_declaration
    assert parsed.coverage.unrecognized_commands == tuple()


def test_parse_declarations_supports_unicode_and_quoted_names() -> None:
    parsed = parse_declarations(
        text="""namespace Δ
def αβ : Nat := 1
theorem «name with spaces» : True := by trivial
end Δ
""",
        module_dot="Unicode",
    )

    assert [decl.name for decl in parsed.declarations] == [
        "Δ.αβ",
        "Δ.«name with spaces»",
    ]
