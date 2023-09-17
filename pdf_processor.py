import pickle
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import os,openai

os.environ["OPENAI_API_KEY"] = "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"
openai.api_key = os.getenv('OPENAI_API_KEY')
VectorStore = None

def process_file(file_path):
    global VectorStore

    if VectorStore is None:
        with open(file_path, "rb") as text_file:
            file_extension = os.path.splitext(file_path)[1].lower()

            if file_extension == ".pdf":
                pdf_reader = PdfReader(text_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
            elif file_extension == ".txt":
                text = text_file.read().decode('utf-8')

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            chunks = text_splitter.split_text(text=text)

            store_name = os.path.splitext(os.path.basename(file_path))[0]
            print(store_name, "store name")

            if os.path.exists(f"{store_name}.pkl"):
                with open(f"{store_name}.pkl", "rb") as f:
                    VectorStore = pickle.load(f)
            else:
                embeddings = OpenAIEmbeddings()
                VectorStore = FAISS.from_texts(chunks, embedding=embeddings)
                with open(f"{store_name}.pkl", "wb") as f:
                    pickle.dump(VectorStore, f)

    return VectorStore

# bg_file_path = "D:/stridec/langchain/BreadGarden.txt"

# bg_vectorstore = process_file(bg_file_path)
# print(bg_vectorstore)