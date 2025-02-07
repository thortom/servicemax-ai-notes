"""
Script to process motor error codes from Excel and add them to the vectorstore.
"""

import pandas as pd
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document

def process_error_codes(excel_path: str):
    # Read the Excel file
    df = pd.read_excel(excel_path)
    
    # Create documents from the error codes
    documents = []
    for _, row in df.iterrows():
        # Combine the information into a meaningful text
        content = (
            f"Drive Type: {row['Drive type']}\n"
            f"Error Code {row['Error Code']}: {row['Description of error']}\n"
            f"What it means: {row['What it means']}\n"
            f"Troubleshooting: {row['Troubleshooting']}\n"
            f"Category: {row['Category']}"
        )
        
        metadata = {
            "error_code": str(row['Error Code']),
            "drive_type": str(row['Drive type']),
            "category": str(row['Category']),
            "source": "motor_error_codes"
        }
        documents.append(Document(page_content=content, metadata=metadata))

    # # Initialize the vectorstore with the same settings as your existing one
    vectorstore = Chroma(
        persist_directory="my_vectorstore",
        embedding_function=OpenAIEmbeddings(),
        collection_name="manual-collection"
    )
    
    # Add the documents to the vectorstore
    vectorstore.add_documents(documents)
    print(f"Added {len(documents)} error codes to the vectorstore")

if __name__ == "__main__":
    # Replace with your Excel file path
    excel_path = "MS2750 - Error codes - Kollmorgan-Wittenstein.xlsx"
    process_error_codes(excel_path)
