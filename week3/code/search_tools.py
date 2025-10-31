#same code as we've used before (using minsearch)

from minsearch import Index
from typing import Any, Dict, List
import docs

import pickle
from pathlib import Path


class SearchTools:

    def __init__(self, index: Index):
        self.index = index

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the index for documents matching the given query.

        Args:
            query (str): The search query string.

        Returns:
            A list of search results
        """
        return self.index.search(
            query=query,
            num_results=5,
        )

# index preparation code with minsearch
def prepare_index():
    github_data = docs.read_github_data() # get data from GitHub
    parsed_data = docs.parse_data(github_data) # parse the data with frontmatter
    chunks = docs.chunk_documents(parsed_data) # chunk the documents

    index = Index(
        text_fields=["title", "description", "content"]
    )

    index.fit(chunks)
    return index

# add caching for results to avoid re-indexing every time
def prepare_index_cached():
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)

    index_path = cache_dir / "search_index.bin"

    if index_path.exists():
        with open(index_path, "rb") as f:
            index = pickle.load(f)
            return index

    index = prepare_index()

    with open(index_path, "wb") as f:
        pickle.dump(index, f)

    return index

# function to get search tools
def get_search_tools():
    index = prepare_index_cached()
    return SearchTools(index=index)


if __name__ == "__main__":
    search_tools = get_search_tools()
    query = "data quality checks"
    results = search_tools.search("data drift")
    for r in results:
        print(r)