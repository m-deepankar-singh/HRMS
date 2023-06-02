import os
import pickle
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from llama_index import SimpleDirectoryReader, GPTSimpleVectorIndex, Document, LLMPredictor, ServiceContext
from langchain.chat_models import ChatOpenAI


os.environ['OPENAI_API_KEY'] = ""

index = None
stored_docs = {}
lock = Lock()

index_name = "./index.json"
pkl_name = "stored_documents.pkl"


def initialize_index():
    """Create a new global index, or load one from the pre-set path."""
    global index, stored_docs
    with lock:
        if os.path.exists(index_name):
            index = GPTSimpleVectorIndex.load_from_disk(index_name)
        else:
            index = GPTSimpleVectorIndex([])
            index.save_to_disk(index_name)
        


def query_index(query_text):
    """Query the global index."""
    global index
    response = index.query(query_text)
    return response


def insert_into_index(doc_file_path, doc_id=None):
    """Insert new document into global index."""
    global index, stored_docs
    document = SimpleDirectoryReader(input_files=[doc_file_path]).load_data()[0]
    if doc_id is not None:
        document.doc_id = doc_id
    
    # Keep track of stored docs -- llama_index doesn't make this easy
    stored_docs[document.doc_id] = document.text[0:50]  # only take the first 200 chars

    with lock:
        index.insert(document)
        index.save_to_disk(index_name)
        
        with open(pkl_name, "wb") as f:
            pickle.dump(stored_docs, f)

    return

def get_documents_list():
    """Get the list of currently stored documents."""
    global stored_docs
    documents_list = []
    for doc_id, doc_text in stored_docs.items():
        documents_list.append({"id": doc_id, "text": doc_text})

    return documents_list





if __name__ == "__main__":
    # init the global index
    print("initializing index...")
    initialize_index()

    # setup server
    # NOTE: you might want to handle the password in a less hardcoded way
    manager = BaseManager(('127.0.0.1', 5602), b'password')
    manager.register('query_index', query_index)
    manager.register('insert_into_index', insert_into_index)
    manager.register('get_documents_list', get_documents_list)
    server = manager.get_server()

    print("server started...")
    server.serve_forever()
