import os
import json
import pandas as pd
import shutil
from typing import List, Dict, Any, Union, Optional
TrieNode = Dict[str, Any]

class TrieManager:
    def __init__(
        self,
        source_csv: str,
        output_json: str,
        id_col: str,
        data_col: str,
        separator: str = ';'
    ) -> None:
        self.source_csv: str = os.path.abspath(source_csv)
        self.output_json: str = os.path.abspath(output_json)
        self.id_col: str = id_col
        self.data_col: str = data_col
        self.separator: str = separator
        self.trie_root: TrieNode = {}
        if not os.path.exists(self.source_csv):
            raise FileNotFoundError(f"Source file does not exist: {self.source_csv}")
        self._generate_trie_if_needed()
        self._load_trie()

    def _get_file_mtime(self, filepath: str) -> float:
        """Safely get file modification time."""
        try:
            return os.path.getmtime(filepath)
        except OSError:
            return 0.0

    def _add_to_trie(self, trie: TrieNode, word: str, doc_id: Union[int, str]) -> None:
        """
        Inserts a word and its associated document ID into the Trie.
        """
        if not isinstance(word, str):
            return

        clean_word = word.lower().strip()
        if not clean_word:
            return

        node = trie
        for char in clean_word:
            if char not in node:
                node[char] = {}
            node = node[char]
        if "__ids__" not in node:
            node["__ids__"] = []
        if doc_id not in node["__ids__"]:
            node["__ids__"].append(doc_id)

    def _generate_trie_if_needed(self) -> None:
        input_mtime = self._get_file_mtime(self.source_csv)
        output_mtime = self._get_file_mtime(self.output_json)

        if output_mtime > input_mtime and output_mtime > 0:
            return

        print(f"Source changed or output missing. Generating Trie from {self.source_csv}...")
        temp_root: TrieNode = {}
        chunk_size = 50000

        try:
            with pd.read_csv(self.source_csv, usecols=[self.id_col, self.data_col], chunksize=chunk_size) as reader:
                for chunk in reader:
                    chunk = chunk.dropna(subset=[self.id_col, self.data_col])
                    for doc_id, data_str in zip(chunk[self.id_col], chunk[self.data_col]):
                        items = str(data_str).split(self.separator)
                        for item in items:
                            self._add_to_trie(temp_root, item, doc_id)

        except (ValueError, KeyError) as e:
            print(f"Error reading CSV structure: {e}")
            raise e
        except Exception as e:
            print(f"Unexpected error during Trie generation: {e}")
            return
        temp_output = self.output_json + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.output_json), exist_ok=True)
            with open(temp_output, 'w', encoding='utf-8') as f:
                json.dump(temp_root, f, separators=(',', ':'))
            shutil.move(temp_output, self.output_json)
            print("Trie generation complete.")
        except OSError as e:
            print(f"Failed to save Trie JSON: {e}")
            if os.path.exists(temp_output):
                os.remove(temp_output)

    def _load_trie(self) -> None:
        try:
            with open(self.output_json, 'r', encoding='utf-8') as f:
                self.trie_root = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Could not load JSON trie ({e}). Initializing empty.")
            self.trie_root = {}

    def search(self, prefix: str) -> List[str]:
        """
        Returns a list of full words starting with 'prefix'.
        """
        if not prefix or not isinstance(prefix, str):
            return []

        clean_prefix = prefix.lower()
        node = self.trie_root
        for char in clean_prefix:
            if char in node:
                node = node[char]
            else:
                return []
        return self._collect_words_iterative(node, clean_prefix)

    def _collect_words_iterative(self, start_node: TrieNode, prefix: str) -> List[str]:
        """
        Hardening: Replaced recursion with an iterative stack approach
        to prevent RecursionError on extremely deep tries.
        """
        results: List[str] = []
        stack = [(start_node, prefix)]
        while stack:
            curr_node, curr_word = stack.pop()
            if "__ids__" in curr_node:
                results.append(curr_word)
            for char, child_node in curr_node.items():
                if char != "__ids__":
                    stack.append((child_node, curr_word + char))
        return results
