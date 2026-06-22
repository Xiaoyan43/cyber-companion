from __future__ import annotations

from backend.app.tts.tag_stats import compute_tag_stats, extract_tags


def test_empty_text_has_no_tags():
    stats = compute_tag_stats("")
    assert stats.total_tags == 0
    assert stats.distinct_tags == 0
    assert stats.max_repeat == 0
    assert stats.distinct_ratio == 0.0
    assert stats.opening_only is False
    assert stats.non_opening_tag_count == 0


def test_plain_text_without_tags():
    stats = compute_tag_stats("你好。今天怎么样？")
    assert stats.total_tags == 0
    assert stats.sentence_count == 2
    assert stats.tagged_sentence_count == 0
    assert stats.tagged_sentence_ratio == 0.0


def test_repeated_same_tag_is_flagged():
    # The core degradation pattern: same tag stamped across the whole reply.
    stats = compute_tag_stats("[sighing]真的吗。[sighing]我不信。")
    assert stats.total_tags == 2
    assert stats.distinct_tags == 1
    assert stats.max_repeat == 2
    assert stats.distinct_ratio == 0.5
    assert stats.tag_counts == {"sighing": 2}


def test_distinct_tags_spread_across_sentences():
    stats = compute_tag_stats("[happy]太好了！[sad]但是我有点难过。")
    assert stats.total_tags == 2
    assert stats.distinct_tags == 2
    assert stats.max_repeat == 1
    assert stats.distinct_ratio == 1.0
    assert stats.non_opening_tag_count == 1
    assert stats.opening_only is False


def test_tags_clustered_at_opening_only():
    # Multi-sentence reply, every tag jammed into the first sentence.
    stats = compute_tag_stats("[excited][happy]太好了！我今天很开心。然后我们去玩吧。")
    assert stats.total_tags == 2
    assert stats.sentence_count == 3
    assert stats.non_opening_tag_count == 0
    assert stats.opening_only is True


def test_single_sentence_is_not_opening_only():
    # One sentence can't have a clustering problem, even with tags up front.
    stats = compute_tag_stats("[happy][excited]太好了！")
    assert stats.sentence_count == 1
    assert stats.opening_only is False


def test_tag_normalization_is_case_insensitive():
    stats = compute_tag_stats("[Happy]今天。[happy]很好。")
    assert stats.distinct_tags == 1
    assert stats.max_repeat == 2
    assert stats.tag_counts == {"happy": 2}


def test_chinese_tags_are_recognized():
    stats = compute_tag_stats("[叹气]真的。[低声说]别走。")
    assert stats.total_tags == 2
    assert stats.distinct_tags == 2
    assert stats.tag_counts == {"叹气": 1, "低声说": 1}


def test_back_to_back_combo_counts_both_tags():
    # The officially-recommended physical+emotion combo still counts as two tags.
    stats = compute_tag_stats("[panting][tired]我跑了二十分钟了。")
    assert stats.total_tags == 2
    assert stats.distinct_tags == 2


def test_rhythm_markers_excluded_from_repeat_signal():
    # Repeating [break] is legitimate prosody, not the same-emotion-tag degradation.
    stats = compute_tag_stats("[break]停一下。[break]再走。[happy]好啦。")
    assert stats.total_tags == 3  # density still counts all three
    assert stats.tag_counts == {"break": 2, "happy": 1}
    assert stats.distinct_tags == 1  # only [happy] is expressive
    assert stats.max_repeat == 1  # NOT 2 — the [break] repeat is ignored
    assert stats.distinct_ratio == 1.0


def test_rhythm_only_text_has_no_expressive_signal():
    stats = compute_tag_stats("[break]嗯。[long-break]算了。")
    assert stats.total_tags == 2
    assert stats.distinct_tags == 0
    assert stats.max_repeat == 0
    assert stats.distinct_ratio == 0.0


def test_extract_tags_preserves_order():
    assert extract_tags("[happy]a。[sad]b。[happy]c。") == ["happy", "sad", "happy"]
