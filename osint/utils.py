from ddgs import DDGS

def search(query, num_results=10):
    """Perform a web search and return a list of results."""
    try:
        results = []
        ddgs = DDGS()
        for result in ddgs.text(query, max_results=num_results):
            results.append({
                'title': result.get('title', ''),
                'url': result.get('href', ''),
                'description': result.get('body', '')
            })
        print(f"Found {len(results)} results for {query}:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   {result['description']}...\n")
        return results
    except Exception as e:
        print(f"Error performing search: {e}")
        return []

if __name__ == "__main__":
    search_term = str(input("Enter search term: "))
    search(search_term, num_results=5)