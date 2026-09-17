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


def test_value_preserves_newline_term_proof_as_original_suffix() -> None:
    text = 'lemma direct : True :=\n  True.intro\n'
    decl = parse_declarations(text=text, module_dot='M').declarations[0]
    assert decl.value == ':=\n  True.intro'
    assert decl.full_declaration.endswith(decl.value)


def test_value_separator_ignores_defaults_comments_strings_and_nested_terms() -> None:
    text = '''def f (n : Nat := 3) /- := fake -/ : String :=
  ":= where"
lemma t : (let n := 1; n = 1) := by rfl
'''
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.signature == '(n : Nat := 3) /- := fake -/ : String'
    assert first.value == ':=\n  ":= where"'
    assert second.signature == ': (let n := 1; n = 1)'
    assert second.value == ':= by rfl'


def test_where_and_multiline_axiom_preserve_source() -> None:
    text = '''structure S where
  value : Nat
axiom h
  (n : Nat)
  : n = n
'''
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.value == 'where\n  value : Nat'
    assert second.signature == '(n : Nat)\n  : n = n'


def test_quoted_identifier_delimiter_is_not_a_value() -> None:
    decl = parse_declarations(text='def «:= where» : Nat := 1\n', module_dot='M').declarations[0]
    assert decl.value == ':= 1'


def test_equation_body_is_separate_from_multiline_signature() -> None:
    text = "def f\n  : Nat → Nat\n  | 0 => 1\n  | n + 1 => n\n"
    decl = parse_declarations(text=text, module_dot='M').declarations[0]
    assert decl.signature == ': Nat → Nat'
    assert decl.value == '| 0 => 1\n  | n + 1 => n'
    assert decl.value in decl.full_declaration


def test_module_docs_do_not_extend_previous_proof() -> None:
    text = "theorem t : True := by trivial\n\n/-! ## Next section -/\n\ndef n := 1\n"
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.value == ':= by trivial'
    assert first.full_declaration == 'theorem t : True := by trivial'
    assert second.name == 'n'


def test_statement_lets_and_absolute_value_are_not_proof_delimiters() -> None:
    text = """lemma t :
    let x : Nat := 1
    let y : Nat := x
    y = x := by rfl
lemma bound (f : Nat → Int) :
    |f 0| ≤ (fun x => |f x|) 0 := by rfl
"""
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.value == ':= by rfl'
    assert 'let y : Nat := x' in first.signature
    assert second.value == ':= by rfl'
    assert '|f 0|' in second.signature


def test_equation_theorem_and_spaced_absolute_value() -> None:
    text = """theorem eqn : (n : Nat) → n = n
  | 0 => rfl
  | n + 1 => rfl
lemma bound (f : Nat → Int) :
    | f 0 | ≤ (fun x => |f x|) 0 := by rfl
"""
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.value == '| 0 => rfl\n  | n + 1 => rfl'
    assert second.value == ':= by rfl'


def test_trailing_comments_are_not_proof_but_string_values_survive() -> None:
    text = """theorem t : True := by trivial -- explanation
-- Next topic
/- A long reference. -/
def text : String :=
  "-- not a comment /- still text -/" -- comment
/- Next section -/
"""
    first, second = parse_declarations(text=text, module_dot='M').declarations
    assert first.value == ':= by trivial'
    assert second.value == ':=\n  "-- not a comment /- still text -/"'
    assert second.full_declaration.endswith('"')
