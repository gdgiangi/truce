# Tool Contracts for MCP / function-calling (abstract)
- search_web(query:str, time_start?:ISO8601, time_end?:ISO8601, max_results?:int) -> {results:[{title,url,snippet,date}]}
- fetch_page(url:str) -> {url, html, text, metadata:{title,author,published_at}}
- expand_links(url:str, depth?:int, same_domain?:bool) -> {links:[{url,title}]}
- extract_facts(text:str) -> {facts:[{claim,evidence_span,source_url}]}
- deduplicate_sources(urls:[str]) -> {unique_urls:[str], clusters:[[str]]}
- render_replay(trace:json) -> {html, json, assets?}
