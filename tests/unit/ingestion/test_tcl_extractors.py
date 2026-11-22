"""Unit tests for Tcl AST extraction: procs, source / package imports, calls."""

from __future__ import annotations

from datetime import datetime

import pytest

from repowise.core.ingestion.models import EXTENSION_TO_LANGUAGE, FileInfo
from repowise.core.ingestion.parser import ASTParser


def _file(path: str = "scripts/flow.tcl") -> FileInfo:
    return FileInfo(
        path=path,
        abs_path=f"/tmp/{path}",
        language="tcl",
        size_bytes=100,
        git_hash="",
        last_modified=datetime.now(),
        is_test=False,
        is_config=False,
        is_api_contract=False,
        is_entry_point=False,
    )


@pytest.fixture(scope="module")
def parser() -> ASTParser:
    return ASTParser()


def test_extension_routes_to_tcl() -> None:
    assert EXTENSION_TO_LANGUAGE[".tcl"] == "tcl"


class TestTclSymbols:
    @pytest.mark.parametrize(
        "arguments", [b'"x y"', b'"x {y 1}"', b'"$args"', b'"[list x y]"', b"$args", b"[list x y]"]
    )
    def test_proc_argument_words_do_not_hide_following_procs(
        self, parser: ASTParser, arguments: bytes
    ) -> None:
        src = b"proc f " + arguments + b" { helper }\nproc g {} { other }\n"
        result = parser.parse_file(_file(), src)
        assert [s.name for s in result.symbols] == ["f", "g"]
        assert result.parse_errors == []

    def test_procs_named_by_last_segment(self, parser: ASTParser) -> None:
        src = (
            b"namespace eval ::ns {\n"
            b"  proc ::ns::run {a} { return $a }\n"
            b"  proc check {} {\n    return 1\n  }\n"
            b"}\n"
            b"proc top {} {}\n"
        )
        result = parser.parse_file(_file(), src)
        assert [(s.name, s.kind, s.start_line, s.end_line) for s in result.symbols] == [
            ("run", "method", 2, 2),
            ("check", "method", 3, 5),
            ("top", "function", 7, 7),
        ]

    def test_proc_switch_pattern_is_not_a_symbol(self, parser: ASTParser) -> None:
        src = b"proc d {c} {\n  switch $c {\n    proc { helper }\n    other { go }\n  }\n}\n"
        result = parser.parse_file(_file(), src)
        assert [s.name for s in result.symbols] == ["d"]


class TestTclImports:
    def test_source_and_package_require(self, parser: ASTParser) -> None:
        src = (
            b"package require Tcl 8.6\n"
            b"package require myutil 1.0\n"
            b"source $script_dir/lib/helpers.tcl\n"
            b'source -echo -verbose "scripts/setup.tcl"\n'
            b"package provide mine 1.0\n"
        )
        result = parser.parse_file(_file(), src)
        assert [i.module_path for i in result.imports] == [
            "Tcl",
            "myutil",
            "$script_dir/lib/helpers.tcl",
            '-echo -verbose "scripts/setup.tcl',
        ]

    def test_package_require_exact_names_the_package(self, parser: ASTParser) -> None:
        result = parser.parse_file(_file(), b"package require -exact myutil 1.0\n")
        assert [i.module_path for i in result.imports] == ["myutil"]

    @pytest.mark.parametrize("option", ["", "-exact "])
    @pytest.mark.parametrize("separator", [" ", "\t"])
    def test_braced_package_name(self, parser: ASTParser, option: str, separator: str) -> None:
        result = parser.parse_file(
            _file(), f"package{separator}require {option}{{myutil}} 1.0\n".encode()
        )
        assert [i.module_path for i in result.imports] == ["myutil"]

    @pytest.mark.parametrize("option", ["", "-exact "])
    def test_quoted_package_name(self, parser: ASTParser, option: str) -> None:
        result = parser.parse_file(_file(), f'package require {option}"myutil" 1.0\n'.encode())
        assert [i.module_path for i in result.imports] == ["myutil"]

    def test_interpolated_package_name_is_not_a_literal_import(self, parser: ASTParser) -> None:
        result = parser.parse_file(_file(), b'package require "my$version" 1.0\n')
        assert result.imports == []


class TestTclCalls:
    def test_semicolon_separates_commands_and_preserves_their_caller(self, parser: ASTParser) -> None:
        src = b"proc f {} { helper; other; }\n"
        result = parser.parse_file(_file(), src)
        assert result.parse_errors == []
        assert {c.target_name for c in result.calls} == {"helper", "other"}
        assert all(c.caller_symbol_id == "scripts/flow.tcl::f" and c.line == 1 for c in result.calls)

    def test_array_substitution_does_not_hide_following_calls(self, parser: ASTParser) -> None:
        src = b"proc f {name} { set x $pending($name); helper $x }\n"
        result = parser.parse_file(_file(), src)
        assert result.parse_errors == []
        assert [(c.target_name, c.caller_symbol_id) for c in result.calls] == [
            ("helper", "scripts/flow.tcl::f")
        ]

    def test_commands_builtins_and_qualified_names(self, parser: ASTParser) -> None:
        src = (
            b"proc f {x} {\n"
            b"  helper $x\n"
            b"  ::ns::check $x\n"
            b"  set_app_var foo bar\n"
            b"  puts [string length $x]\n"
            b"  lappend out $x\n"
            b"}\n"
        )
        result = parser.parse_file(_file(), src)
        assert {c.target_name for c in result.calls} == {"helper", "check", "set_app_var"}

    def test_switch_arm_patterns_are_not_calls(self, parser: ASTParser) -> None:
        src = (
            b"proc f {m} {\n"
            b"  switch -- $m {\n"
            b"    fast { run_fast }\n"
            b"    default { run_slow }\n"
            b"  }\n"
            b"}\n"
        )
        result = parser.parse_file(_file(), src)
        assert {c.target_name for c in result.calls} == {"run_fast", "run_slow"}

    def test_separate_word_switch_arms_are_calls(self, parser: ASTParser) -> None:
        src = b"proc f {m} {\n  switch $m fast {run_fast} default {run_slow}\n}\n"
        result = parser.parse_file(_file(), src)
        assert {c.target_name for c in result.calls} == {"run_fast", "run_slow"}

    @pytest.mark.parametrize(
        "arms", ["fast run_fast default run_slow", "{fast run_fast default run_slow}"]
    )
    def test_bare_switch_bodies_are_calls(self, parser: ASTParser, arms: str) -> None:
        result = parser.parse_file(_file(), f"proc f {{m}} {{ switch $m {arms} }}\n".encode())
        assert {c.target_name for c in result.calls} == {"run_fast", "run_slow"}
        assert all(c.caller_symbol_id == "scripts/flow.tcl::f" for c in result.calls)

    def test_dynamic_switch_body_is_not_a_literal_call(self, parser: ASTParser) -> None:
        result = parser.parse_file(_file(), b"proc f {m script} { switch $m fast $script }\n")
        assert result.calls == []

    def test_nested_switch_fallthrough_and_qualified_bodies(self, parser: ASTParser) -> None:
        src = (
            b"proc f {m n} {\n"
            b"  switch $m {\n"
            b"    first -\n"
            b"    second { switch $n { fast ::ns::run default other } }\n"
            b"    default puts\n"
            b"  }\n"
            b"}\n"
        )
        result = parser.parse_file(_file(), src)
        assert {c.target_name for c in result.calls} == {"run", "other"}
        assert all(c.caller_symbol_id == "scripts/flow.tcl::f" for c in result.calls)

    def test_a_switch_arm_named_source_is_not_an_import(self, parser: ASTParser) -> None:
        src = (
            b"proc f {m} {\n"
            b"  switch -- $m {\n"
            b"    source {run_fast}\n"
            b"    fast { source lib/x.tcl }\n"
            b"  }\n"
            b"}\n"
        )
        result = parser.parse_file(_file(), src)
        assert [i.module_path for i in result.imports] == ["lib/x.tcl"]


def test_a_tcltest_file_is_tcl_and_other_dot_test_files_are_not() -> None:
    from pathlib import Path

    from repowise.core.ingestion.traverser import _detect_language

    tcltest = (
        b"package require tcltest\nnamespace import ::tcltest::*\ntest p-1 {} -body { parse x }\n"
    )
    assert _detect_language(Path("tests/parser.test"), tcltest) == "tcl"
    assert _detect_language(Path("tests/b.test"), b"::tcltest::test b-1 {} { go }\n") == "tcl"
    assert _detect_language(
        Path("tests/exact.test"), b"package require -exact tcltest 2.5\ntcltest::test x {} {}\n"
    ) == "tcl"
    assert _detect_language(Path("tests/quoted.test"), b'package require "tcltest"\n') == "tcl"
    assert _detect_language(Path("tests/braced.test"), b"package require -exact {tcltest}\n") == "tcl"
    assert _detect_language(Path("tests/dynamic.test"), b'package require "tcltest$version"\n') != "tcl"
    lit = b"; RUN: llvm-objdump -d %s | FileCheck %s\n"
    assert _detect_language(Path("llvm/test/x.test"), lit) != "tcl"
