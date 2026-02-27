import os
from neo4j import GraphDatabase
from langchain_google_vertexai import VertexAIEmbeddings

from google.adk import Agent
from ...config import MODEL

from . import prompt

# Load environment
from dotenv import load_dotenv
from pathlib import Path

_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_URI = os.getenv("NEO4J_URI")

def search_knowledge_base(query: str) -> str:
    """
    Search the embedded knowledge base (The Intelligent Investor book) 
    for principles and guidance related to the provided query.
    """
    try:
        embeddings_model = VertexAIEmbeddings(model_name="text-embedding-005")
        query_embedding = embeddings_model.embed_query(query)

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        
        with driver.session() as session:
            # We use the vector index 'chunk_embeddings' to find the top 5 matches
            cypher_query = """
            CALL db.index.vector.queryNodes('chunk_embeddings', 5, $embedding)
            YIELD node, score
            RETURN node.text AS text, score
            ORDER BY score DESC
            """
            result = session.run(cypher_query, embedding=query_embedding)
            
            snippets = []
            for record in result:
                snippets.append(record["text"])
                
        driver.close()
        
        if not snippets:
            return "No relevant information found in the knowledge base for this query."
            
        return "Knowledge Base Excerpts:\n\n" + "\n\n---\n\n".join(snippets)
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"

rag_analyst_agent = Agent(
    model=MODEL,
    name="rag_analyst_agent",
    instruction=prompt.RAG_ANALYST_PROMPT,
    tools=[search_knowledge_base],
    output_key="rag_analysis_output",
)
