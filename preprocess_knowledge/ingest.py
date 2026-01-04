import os
from neo4j import GraphDatabase
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_URI = os.getenv("NEO4J_URI")

GCLOUD_PROJECT = os.getenv("GOOGLE_PROJECT_ID")


def load_and_split_document(file_path):
    """Loads a text file and splits it into manageable chunks."""
    print(f"Loading document from {file_path}...")
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return text_splitter.split_documents(documents)


def setup_graph_schema(driver):
    """Sets up the Neo4j database constraints and vector index."""
    print("Setting up database schema...")
    with driver.session() as session:
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;")
        session.run("""
        CREATE VECTOR INDEX `chunk_embeddings` IF NOT EXISTS
        FOR (c:Chunk) ON (c.embedding)
        OPTIONS { indexConfig: {
            `vector.dimensions`: 768,
            `vector.similarity_function`: 'cosine'
        }}
        """)
    print("Schema setup complete.")



import time


def ingest_data(driver, docs, embeddings_model):
    """Ingests document chunks and their embeddings into Neo4j using smaller batches."""
    print("Starting data ingestion with smaller batches...")

    batch_size = 200  # A safe batch size below the 250 limit

    with driver.session() as session:
        # Loop through the documents in chunks of 'batch_size'
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i: i + batch_size]
            texts = [doc.page_content for doc in batch_docs]
            print(f"Generating embeddings for batch {i // batch_size + 1}...")
            embeddings = embeddings_model.embed_documents(texts)

            # 3. Ingest this mini-batch into Neo4
            for j, doc in enumerate(batch_docs):
                # Get the global index for the document
                global_index = i + j
                embedding = embeddings[j]
                cypher_query = """
                MERGE (c:Chunk {id: $id})
                SET c.text = $text, c.embedding = $embedding
                """
                session.run(cypher_query, id=global_index, text=doc.page_content, embedding=embedding)
                if global_index > 0:
                    link_query = """
                    MATCH (p:Chunk {id: $prev_id})
                    MATCH (c:Chunk {id: $current_id})
                    MERGE (p)-[:NEXT]->(c)
                    """
                    session.run(link_query, prev_id=global_index - 1, current_id=global_index)

            print(f"  Ingested batch {i // batch_size + 1}")
            time.sleep(1)

    print("Data ingestion complete.")

if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    embeddings = VertexAIEmbeddings(model_name="text-embedding-005")
    setup_graph_schema(driver)
    documents = load_and_split_document("cleaned_book.txt")
    ingest_data(driver, documents, embeddings)
    driver.close()
