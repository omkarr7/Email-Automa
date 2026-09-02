from ...web_search_adapter import search_company_candidates

def discover(queries):
    candidates=[]
    for query in queries:
        candidates.extend(search_company_candidates(query))
    return candidates
