import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reviewer import build_vllm_models_url, split_diff_into_chunks


class TestBuildVllmModelsUrl:
    def test_base_url_with_v1_suffix(self):
        url = build_vllm_models_url("http://192.168.1.87:30000/v1")
        assert url == "http://192.168.1.87:30000/v1/models"

    def test_base_url_without_v1_suffix(self):
        url = build_vllm_models_url("http://192.168.1.87:30000")
        assert url == "http://192.168.1.87:30000/v1/models"

    def test_base_url_with_trailing_slash(self):
        url = build_vllm_models_url("http://192.168.1.87:30000/v1/")
        assert url == "http://192.168.1.87:30000/v1/models"


class TestSplitDiffIntoChunks:
    def test_small_diff_returns_single_chunk(self):
        diff = "line one\nline two\nline three"
        chunks = split_diff_into_chunks(diff, max_tokens=1000)
        assert len(chunks) == 1
        assert chunks[0] == diff

    def test_large_diff_splits_into_multiple_chunks(self):
        # Each word counts as 1 token; 300 words per line × 10 lines = 3000 tokens
        line = " ".join(["word"] * 300)
        diff = "\n".join([line] * 10)
        chunks = split_diff_into_chunks(diff, max_tokens=500)
        assert len(chunks) > 1

    def test_empty_diff_returns_single_empty_chunk(self):
        chunks = split_diff_into_chunks("")
        assert len(chunks) == 1
        assert chunks[0] == ""
