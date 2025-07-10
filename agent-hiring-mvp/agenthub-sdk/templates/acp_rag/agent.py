from collections.abc import AsyncGenerator

from acp_sdk import Message, MessagePart
from acp_sdk.server import Server
import os

from llama_index.core import Settings, VectorStoreIndex, node_parser, Document
from llama_index.core.agent.workflow import FunctionAgent, AgentStream
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

## Load document
document_content = """# Docling Framework Overview        
Docling is a framework designed to simplify the process of building and deploying AI agents. It provides a set of tools and libraries that allow developers to create agents that can interact with users, process natural language, and perform various tasks.
## Key Features
- **Modular Design**: Docling is built with a modular architecture, allowing developers to easily extend and customize the framework to suit their needs.

- **Natural Language Processing**: The framework includes built-in support for natural language processing, enabling agents to understand and respond to user queries effectively.
- **Integration with LLMs**: Docling can be integrated with various large language models (LLMs) to enhance the capabilities of agents, allowing them to generate human-like responses and perform complex tasks.
- **Scalability**: The framework is designed to handle large-scale deployments, making it suitable for building enterprise-level AI applications.
- **Community Support**: Docling has an active community of developers who contribute to the framework, providing support and sharing best practices.
## Getting Started
To get started with Docling, you can follow these steps:

1. **Installation**: Install the Docling framework using pip:
```bash
pip install docling 
```  
2. **Creating an Agent**: Use the provided templates and examples to create your first agent. The framework includes a variety of pre-built agents that you can customize.
3. **Training the Agent**: Train your agent using the provided training data and configurations. You can use the built-in tools to fine-tune the agent's performance.
4. **Deployment**: Deploy your agent to a server or cloud platform. Docling provides tools for easy deployment and scaling.
5. **Testing and Iteration**: Test your agent with real users and iterate on its design and functionality based on feedback.
"""

## Create RAG query engine
Settings.llm = OpenAI(model='gpt-4.1',
                      temperature=0,
                      api_key=api_key)

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-ada-002",
    api_key=api_key
    # With the `text-embedding-3` class
    # of models, you can specify the size
    # of the embeddings you want returned.
    # dimensions=1024
)

document = Document(text=document_content)

index = VectorStoreIndex.from_documents(documents=[document], transformations=[MarkdownNodeParser()])
query_engine = index.as_query_engine()

## Create the agent
tools = [
    QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="Docling_Knowledge_Base",
            description="Use this tool to answer any questions related to the Docling framework",
        ),
    )
]
agent = FunctionAgent(tools=tools, llm=Settings.llm)

server = Server()


@server.agent()
async def llamaindex_rag_agent(message: Message) -> AsyncGenerator[Message, None]:
    """LlamaIndex agent that answers questions using the Docling
    knowledge base. The agent answers questions in streaming mode."""

    try:
        # Extract query from message
        query = message[0].parts[0].content if message[0].parts else str(message)

        # Run the agent
        handler = agent.run(query)

        # Get final response
        response = await handler
        yield Message(parts=[MessagePart(text=str(response.response.content))])

    except Exception as e:
        yield Message(parts=[MessagePart(text=f"Error: {str(e)}")])


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))

    server.run(host=host, port=port)
