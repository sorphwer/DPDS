# pip install sparqlwrapper
# https://rdflib.github.io/sparqlwrapper/

import sys
from SPARQLWrapper import SPARQLWrapper, JSON

endpoint_url = "https://query.wikidata.org/sparql"

query = """prefix neo: <neo4j://voc#> 
#Cats
#SELECT ?item ?label 
CONSTRUCT {
?item a neo:Category ; neo:subCatOf ?parentItem .  
  ?item neo:name ?label .
  ?parentItem a neo:Category; neo:name ?parentLabel .
  ?article a neo:WikipediaPage; neo:about ?item ;
           
}
WHERE 
{
  ?item (wdt:P31|wdt:P279)* wd:Q2429814 .
  ?item wdt:P31|wdt:P279 ?parentItem .
  ?item rdfs:label ?label .
  filter(lang(?label) = "en")
  ?parentItem rdfs:label ?parentLabel .
  filter(lang(?parentLabel) = "en")
  
  OPTIONAL {
      ?article schema:about ?item ;
            schema:inLanguage "en" ;
            schema:isPartOf <https://en.wikipedia.org/> .
    }
  
}"""


def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


results = get_results(endpoint_url, query)

for result in results["results"]["bindings"]:
    print(result)