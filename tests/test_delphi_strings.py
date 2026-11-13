"""String comparison and sorting of the Delphi runtime under Wine."""

from pathlib import Path

from psi_gw.body.island.delphi_strings import (ansi_compare_text, compare_text, equal_part,
                                               string_list_sort)

DATA = Path(__file__).parent / "data"


def test_ansi_compare_text_matches_wine_on_all_world_strings():
    strings = (DATA / "wine_compare_strings.txt").read_bytes().decode("cp1252").split("\n")
    matrix = (DATA / "wine_compare_matrix.txt").read_text().split("\n")
    sign = {"<": -1, "=": 0, ">": 1}
    wrong = [(a, b) for i, a in enumerate(strings) for j, b in enumerate(strings)
             if ansi_compare_text(a, b) != sign[matrix[i][j]]]
    assert len(strings) == 453 and not wrong


def test_examples():
    assert ansi_compare_text("Säen", "Saugen") < 0
    assert ansi_compare_text("Hasel", "Hasel-") < 0 and ansi_compare_text("HASEL", "hasel") == 0
    assert compare_text("Ä", "ä") != 0  # CompareText folds ASCII only
    assert equal_part("SituationChanged\nfoo", "situationchanged")


def test_sort_is_delphi_quicksort():
    words = ["Zuenden", "Säen", "Blubb", "Saugen", "Hämmern", "Nehmen", "Schütteln"]
    assert string_list_sort(words) == ["Blubb", "Hämmern", "Nehmen", "Säen", "Saugen", "Schütteln", "Zuenden"]
