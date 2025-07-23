# Knowledge Base MCP Server

This project implements a "Knowledge Base" server using the `FastMCP` framework. It exposes a tool to search for information within PDF documents stored in a specified directory, identifies the most relevant pages based on a query, and returns them as images.

## Features

- **Knowledge Search**: Searches through a collection of PDF documents to find information relevant to a user's query.
- **Relevance Scoring**: Ranks pages based on the occurrence of query keywords.
- **Image Conversion**: Converts the most relevant PDF pages into PNG images for easy viewing.
- **SSE Communication**: Uses Server-Sent Events (SSE) for communication between the server and clients.

## Project Structure

```
.
├── study_notes/
│   └── *.pdf        # Directory for your PDF knowledge base
├── mcp_images/
│   └── *.png        # Directory where relevant page images are saved
├── tools/
│   ├── mining_data.py # Helper functions for data extraction
│   └── utils.py       # Utility functions for scoring and excerpts
├── server.py        # The main MCP server application
├── client-sse.py    # Example client to interact with the server
└── requirements.txt # Python dependencies
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/willingWill17/Informational-Retrieval-MCP.git
    cd Informational-Retrieval-MCP
    ```

2.  **Create a virtual environment and activate it:**
    ```bash
    python3 -m venv myenv
    source myenv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Add PDF files:**
    Place your PDF documents inside the `study_notes` directory.

## Usage

### Running the Server

To start the MCP server, run the following command:

```bash
python server.py
```

The server will start on `0.0.0.0:8050` and will be ready to accept connections.

### Interacting with the Server

You can use the provided `client-sse.py` to interact with the server. This client demonstrates how to call the `get_knowledge_base` tool and handle the SSE responses.

The `get_knowledge_base` tool accepts a `query` string and returns a JSON object containing a list of relevant images.

**Example interaction:**

A client would call the `get_knowledge_base` tool with a query like `"policy gradients"`. The server will then process the PDFs in `study_notes`, and if it finds relevant pages, it will convert them to images and save them in `mcp_images`. The server then sends back a JSON response with details of these images. 
