import os
import re
import pandas as pd
import gradio as gr
from typing import Optional
from google.cloud import documentai_v1beta3 as documentai
from google.api_core.client_options import ClientOptions
import json
from tqdm import tqdm
from datetime import datetime

# Define the PDF types and their identification patterns
pdf_patterns = {
    'ISO': r'ISO',
    'GMP': r'GMP',
    'GDP': r'GDP',
    'Control Drug': r'(Control Drug|CD)',
    'API': r'API',
    'WC': r'WC',
    'TSE': r'TSE',
    'MSDS': r'MSDS',
    'CEP': r'CEP',
    'Ele': r'Ele',
    'RS': r'RS',
    'Genotoxic': r'Genotoxic',
    'Nitrosamine': r'Nitrosamine'
}

# Initialize Document AI client
# credential_path = r"C:\Users\admroot\Desktop\STAGAI\subtle-odyssey-400507-0b24c38d6538.json"
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

def process_document_sample(
   project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
    field_mask: Optional[str] = None,
    processor_version_id: Optional[str] = None,
) -> Optional[str]:
    
    try:
        # Initialize the Document AI client
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)

        if processor_version_id:
            # The full resource name of the processor version
            name = client.processor_version_path(
                project_id, location, processor_id, processor_version_id
            )
        else:
            # The full resource name of the processor
            name = client.processor_path(project_id, location, processor_id)

        # Read the file into memory
        with open(file_path, "rb") as image:
            image_content = image.read()

        # Load binary data
        raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

        # Configure the process request without specifying field_mask
        request = documentai.ProcessRequest(
            name=name,
            raw_document=raw_document,
        )

        result = client.process_document(request=request)
        
        validity_date = None
        signed_at = None

        # Iterate through entities and properties
        for entity in result.document.entities:
            if entity.type_ == "validity":
                # Initialize properties to None
                signed_at = None
                validity_date = None

                # Iterate through properties of this entity
                for property in entity.properties:
                    if property.type == "signed_at":
                        signed_at = property.mention_text
                    elif property.type == "validity_date":
                        validity_date = property.mention_text

        if validity_date is None or validity_date == "":
            validity_date = None

        return validity_date
    
    except Exception as e:
        print(e)
        return None

# Function to scan directories and find relevant PDFs
def scan_directories(directories, patterns):
    data = []
    total_files = 0
    for directory in directories:
        for root, subdirs, files in os.walk(directory):
            if root == directory:
                continue  # Skip the main directory itself
            total_files += len([file for file in files if file.lower().endswith('.pdf')])

    with tqdm(total=total_files, desc="Processing PDFs") as pbar:
        for directory in directories:
            for root, subdirs, files in os.walk(directory):
                if root == directory:
                    continue  # Skip the main directory itself

                # Dictionary to track the most recent file for each pattern
                most_recent_files = {key: {'file_path': None, 'timestamp': None} for key in patterns.keys()}
                for file in files:
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(root, file)
                        file_timestamp = os.path.getmtime(file_path) if os.path.exists(file_path) else None
                        for key, pattern in patterns.items():
                            if re.search(pattern, file, re.IGNORECASE):
                                if (most_recent_files[key]['timestamp'] is None or 
                                    file_timestamp > most_recent_files[key]['timestamp']):
                                    most_recent_files[key] = {'file_path': file_path, 'timestamp': file_timestamp}
                        pbar.update(1)
                # Process the most recent files for the current subdirectory (product)
                product = os.path.basename(root)
                created_at = datetime.fromtimestamp(os.path.getctime(root)).strftime("%Y-%m-%d %H:%M:%S")
                row = {'Product': product, 'Created_At': created_at}
                for key, file_info in most_recent_files.items():
                    file_path = file_info['file_path']
                    if file_path:
                        if key in ['ISO', 'GMP', 'GDP', 'Control Drug', 'API', 'WC', 'TSE']:
                            row[key] = process_document_sample(
                                            project_id="1011010917669",
                                            location="eu",
                                            processor_id="51b6ccf5a4eecb2",
                                            file_path = file_path,
                                            mime_type="application/pdf",
                                            processor_version_id="c6dd0d7cd5fb9b38"
                                        )
                        else:
                            row[key] = True
                    else:
                        row[key] = False if key in ['MSDS', 'CEP', 'Ele', 'RS', 'Genotoxic', 'Nitrosamine'] else ''
                data.append(row)
    return data

def main(directory):
    main_directories = [directory]
    try:
        # Scan directories and gather data
        data = scan_directories(main_directories, pdf_patterns)

        # Create a DataFrame
        df = pd.DataFrame(data)

        # Ensure all columns are present
        for key in pdf_patterns.keys():
            if key not in df.columns:
                df[key] = False

        # Fill missing values for T/F columns and ensure empty cells for expiration dates are represented correctly
        for key in ['MSDS', 'CEP', 'Ele', 'RS', 'Genotoxic', 'Nitrosamine']:
            df[key] = df[key].fillna(False)
        for key in ['ISO', 'GMP', 'GDP', 'Control Drug', 'API', 'WC', 'TSE']:
            df[key] = df[key].fillna('')

        # Save the DataFrame to a CSV file
        output_csv = 'pdf_info.csv'
        df.to_csv(output_csv, index=False)

        # Additional summary information
        total_files = df.shape[0]

        summary = {
            "directory_path": directory,
            "total_files": total_files,
        }

        return summary, output_csv

    except Exception as e:
        return f"An error occurred: {e}", None

# Custom CSS for Gradio interface
custom_css = """

.svelte-1gfkn6j {
    display: inline-block;
    position: relative;
    z-index: var(--layer-4);
    border: solid var(--block-title-border-width) var(--block-title-border-color);
    border-radius: var(--block-title-radius);
    background: var(--block-title-background-fill);
    padding: var(--block-title-padding);
    font-weight: var(--block-title-text-weight);
    font-size: var(--block-title-text-size);
    line-height: var(--line-sm);
    color: #fff; /* Set text color to white */
}

/* Hide Gradio footer elements */
footer.svelte-1rjryqp {
    display: none !important;
}


body {
    background: #2b2b2b;
    color: #fff;
    font-family: 'Arial', sans-serif;
}

h1 {
    text-align: center;
    color: #E51A1A;
    margin-bottom: 20px;
}

label, input[type="text"] {
    color: #fff;
    background: #333;
    border: 1px solid #555;
    padding: 10px;
    border-radius: 5px;
    width: 100%;
    box-sizing: border-box;
}

textarea {
    background: #333;
    border: 1px solid #555;
    color: #fff;
    padding: 10px;
    border-radius: 5px;
    width: 100%;
    box-sizing: border-box;
}

.output {
    margin-top: 20px;
    padding: 10px;
    border-radius: 5px;
    background: #333;
}


.gradio-container-4-36-1 .prose p {
    color: #186de4;
    text-align: center; /* Center align text 
}


.svelte-1gfkn6j {
    display: inline-block;
    position: relative;
    z-index: var(--layer-4);
    border: solid var(--block-title-border-width) var(--block-title-border-color);
    border-radius: var(--block-title-radius);
    background: var(--block-title-background-fill);
    padding: var(--block-title-padding);
    font-weight: var(--block-title-text-weight);
    font-size: var(--block-title-text-size);
    line-height: var(--line-sm);
}


"""
# Create the Gradio interface
iface = gr.Interface(
    fn=main,
    inputs=gr.Textbox(label="Directory Path", placeholder="Enter the directory path to scan"),
    outputs=[gr.JSON(label="Summary"), gr.File(label="Output CSV")],
    title="PDF Scanner and Processor",
    description="Scan directories for PDFs and extract information using Document AI.",
    css=custom_css
)

# Launch the interface
iface.launch(server_name='0.0.0.0',share=True)
