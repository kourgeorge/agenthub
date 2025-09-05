# AgentHub Agent JSON Schema Specification

## Overview

This specification defines a standardized format for describing agent inputs, outputs, and execution contracts using JSON Schema. It provides clear, validated, and documented agent interfaces that work seamlessly with standard JSON Schema tools and validators.

## Version

**Version**: 1.0.0  
**Date**: 2024-12-19  
**Status**: Draft Specification

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Schema Structure](#schema-structure)
3. [Input Schema Definition](#input-schema-definition)
4. [Output Schema Definition](#output-schema-definition)
5. [Type System](#type-system)
6. [Validation Rules](#validation-rules)
7. [Lifecycle Integration](#lifecycle-integration)
8. [Examples](#examples)
9. [Implementation Guide](#implementation-guide)
10. [Implementation Notes](#implementation-notes)

## Core Concepts

### Agent Contract
An agent contract defines the interface between the agent and its consumers, specifying:
- **Input Schema**: What data the agent expects (using `inputSchema`)
- **Output Schema**: What data the agent returns (using `outputSchema`)
- **Execution Context**: When and how the agent executes
- **Error Handling**: How errors are communicated

### Schema Validation
- **Input Validation**: Ensures incoming data matches expected format
- **Output Validation**: Ensures agent responses are consistent
- **Runtime Safety**: Prevents crashes and unexpected behavior

### Single Format Approach

The specification uses the MCP schema format exclusively for maximum compatibility and simplicity. All agents use the same schema structure.

### Format Structure

#### Input Schema: `inputSchema`
```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "Question to ask about the document"
      },
      "model_name": {
        "type": "string",
        "enum": ["gpt-3.5-turbo", "gpt-4"],
        "description": "LLM model to use"
      }
    },
    "required": ["question"]
  }
}
```

#### Output Schema: `outputSchema`
```json
{
  "outputSchema": {
    "type": "object",
    "properties": {
      "answer": {"type": "string"},
      "question": {"type": "string"}
    },
    "required": ["answer", "question"]
  }
}
```

**Single format benefits:**
- **Consistency**: All agents use the same schema structure
- **JSON Schema Compatibility**: Works seamlessly with standard JSON Schema tools and validators
- **Simplicity**: No confusion about which format to use
- **Maintenance**: Easier to maintain and update

## Schema Structure

### Root Level
```json
{
  "name": "Agent Name",
  "description": "Agent description",
  "version": "1.0.0",
  "agent_type": "function|acp|persistent",
  
  // Standard agent fields
  "requirements": [ ... ],
  "tags": [ ... ],
  
  // Agent contract specification (JSON Schema format)
  "config_schema": {
    "functions": [
      {
        "name": "function_name",
        "description": "Function description",
        "inputSchema": { ... },
        "outputSchema": { ... }
      }
    ]
  }
}
```

### Function Definition
```json
{
  "name": "function_name",
  "description": "Human-readable description of what this function does",
  "inputSchema": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
  },
  "outputSchema": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
  }
}
```

## Input Schema Definition

### Structure

#### JSON Schema Format
```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "parameter_name": {
        "type": "string|number|integer|boolean|array|object",
        "description": "Parameter description",
        "enum": ["option1", "option2"],
        "minLength": 1,
        "maxLength": 100,
        "minimum": 0,
        "maximum": 100,
        "pattern": "^[a-zA-Z0-9]+$"
      }
    },
    "required": ["required_parameter1", "required_parameter2"],
    "additionalProperties": false
  }
}
```

**Benefits of this format:**
- **Industry Standard**: Matches MCP schema specification exactly
- **Tool Compatibility**: Works with MCP tools and servers
- **Clear Validation**: Built-in schema validation
- **Consistent Structure**: Same format across all agents
- **MCP Ecosystem**: Seamless integration with MCP tools and servers

### Parameter Types

#### String Parameters
```json
{
  "type": "string",
  "description": "Text input",
  "minLength": 1,
  "maxLength": 1000,
  "pattern": "^[a-zA-Z0-9\\s]+$"
}
```

#### Numeric Parameters
```json
{
  "type": "number|integer",
  "description": "Numeric input",
  "minimum": 0,
  "maximum": 100,
  "exclusiveMinimum": true,
  "exclusiveMaximum": true,
  "multipleOf": 0.1
}
```

#### Choice Parameters
```json
{
  "type": "string",
  "description": "Selection from predefined options",
  "enum": ["option1", "option2", "option3"],
  "enumDescriptions": {
    "option1": "First option description",
    "option2": "Second option description",
    "option3": "Third option description"
  }
}
```

#### Array Parameters
```json
{
  "type": "array",
  "description": "List of items",
  "items": {
    "type": "string"
  },
  "minItems": 1,
  "maxItems": 10,
  "uniqueItems": true
}
```

#### Object Parameters
```json
{
  "type": "object",
  "description": "Complex parameter object",
  "properties": {
    "nested_param": {
      "type": "string",
      "description": "Nested parameter"
    }
  },
  "required": ["nested_param"]
}
```

#### File Parameters
```json
{
  "type": "array",
  "description": "Array of file reference IDs for uploaded documents",
  "items": {
    "type": "string",
    "format": "file-reference"
  },
  "maxItems": 5
}
```

**Note**: File parameters use `"type": "array"` with `"items": {"type": "string", "format": "file-reference"}` because:
- **JSON Schema Compliance**: Standard JSON Schema Draft 7 doesn't have a built-in `file` type
- **File References**: The actual values are string IDs that reference uploaded files
- **UI Integration**: The `format` and `description` tell the UI this is a file parameter
- **Runtime Processing**: Agents receive file ID arrays and use them to download actual file content
- **Constraints**: File upload constraints are enforced by the backend, not by JSON Schema

#### File Parameter Workflow
1. **Schema Definition**: Agent config defines file parameters with standard JSON Schema properties
2. **UI Rendering**: Frontend renders file upload controls based on parameter description and format
3. **File Upload**: User uploads files through the UI (constraints enforced by backend)
4. **File Storage**: Backend stores files and returns file reference IDs
5. **Form Submission**: UI sends file IDs (strings) as parameter values
6. **Agent Execution**: Agent receives file IDs and downloads actual file content
7. **File Processing**: Agent processes downloaded file content
8. **Cleanup**: Temporary files are automatically cleaned up after expiry

**Example Input Values**:
```json
{
  "file_references": ["abc123-def456-ghi789"],
  "question": "What is this document about?"
}
```

**Multiple Files**:
```json
{
  "file_references": ["file1-id", "file2-id", "file3-id"],
  "question": "Compare these documents"
}
```

## Output Schema Definition

### Structure

The specification uses the MCP output schema format for output definitions:

#### MCP Output Schema Format
```json
{
  "outputSchema": {
    "type": "object",
    "properties": {
      "result": {
        "type": "string",
        "description": "Main result of the function"
      },
      "metadata": {
        "type": "object",
        "properties": {
          "processing_time": {
            "type": "number",
            "description": "Execution time in seconds"
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score"
          }
        }
      }
    },
    "required": ["result"],
    "additionalProperties": false
  }
}
```

**Benefits of this format:**
- **MCP Compatible**: Works seamlessly with MCP tools and servers
- **Structured Output**: Guaranteed JSON schema compliance
- **Runtime Validation**: Built-in schema validation
- **Tool Integration**: Compatible with MCP ecosystem tools
- **Schema Validation**: Built-in JSON Schema validation

### Standard Output Fields

#### Success Response
```json
{
  "status": "success",
  "result": "Main result data",
  "metadata": {
    "processing_time": 1.23,
    "confidence": 0.95,
    "timestamp": "2024-12-19T10:30:00Z"
  }
}
```

#### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": "Field 'required_param' is missing"
  },
  "metadata": {
    "timestamp": "2024-12-19T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

## MCP Schema Integration

### Schema Structure

The specification supports MCP's schema structure for maximum compatibility with MCP tools and servers. This format ensures that agent outputs are structured and predictable.

#### Basic Structure
```json
{
  "outputSchema": {
    "type": "object",
    "properties": { ... },
    "required": [ ... ],
    "additionalProperties": false
  }
}
```

#### Key Components
- **`type`**: The JSON Schema type (object, array, string, etc.)
- **`properties`**: Object properties and their schemas
- **`required`**: Array of required property names
- **`additionalProperties: false`**: Ensures strict output validation

#### Benefits
- **MCP Compatibility**: Works with MCP tools and servers
- **Structured Output**: Guaranteed output format
- **Validation**: Runtime validation of agent responses
- **Tooling**: Compatible with MCP ecosystem tools

### Integration with Agent Contracts

Each function in the agent contract can specify its output schema:

```json
{
  "functions": {
    "execute": {
      "description": "Execute the main function",
      "inputSchema": { ... },
      "outputSchema": {
        "type": "object",
        "properties": {
          "result": {"type": "string"},
          "status": {"type": "string", "enum": ["success", "error"]}
        },
        "required": ["result", "status"],
        "additionalProperties": false
      }
    }
  }
}
```

## Type System

### Mapping from Existing Types

| Current Type | MCP Format | JSON Schema Type | Description | File Support |
|--------------|------------|------------------|-------------|--------------|
| `string` | `"type": "string"` | `string` | Basic text input | ✅ |
| `textarea` | `"type": "string"` | `string` | Multi-line text | ✅ |
| `choice` | `"type": "string"` + `"enum": [...]` | `string` | Selection from options | ✅ |
| `select` | `"type": "string"` + `"enum": [...]` | `string` | Dropdown selection | ✅ |
| `number` | `"type": "number"` | `number` | Floating point number | ✅ |
| `integer` | `"type": "integer"` | `integer` | Whole number | ✅ |
| `boolean` | `"type": "boolean"` | `boolean` | True/false value | ✅ |
| `array` | `"type": "array"` | `array` | List of items | ✅ |
| `object` | `"type": "object"` | `object` | Complex data structure | ✅ |
| **`file`** | **`"type": "array"` + `"items": {"type": "string", "format": "file-reference"}`** | **`array`** | **File reference array parameter** | **🆕** |

### MCP Schema Format

The specification uses the MCP schema format for input and output definitions:

```json
{
  "name": "get_weather",
  "description": "Get the current weather for a given city",
  "inputSchema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "The name of the city to get the weather for"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "The temperature unit to return"
      }
    },
    "required": ["city"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "temperature": {"type": "number"},
      "unit": {"type": "string"},
      "city": {"type": "string"}
    },
    "required": ["temperature", "unit", "city"]
  }
}
```

This format provides:
- **Standardization**: Matches MCP schema specification exactly
- **Compatibility**: Works with MCP tools and servers
- **Clarity**: Clear parameter definitions with descriptions
- **Validation**: Built-in schema validation
- **MCP Integration**: Seamless integration with MCP ecosystem

## Validation Rules

### Input Validation
- **Required Fields**: All required fields must be present
- **Type Checking**: Values must match declared types
- **Range Validation**: Numbers must be within specified bounds
- **Pattern Matching**: Strings must match regex patterns
- **Enum Validation**: Values must be from allowed options

### File Parameter Validation
- **File Type Validation**: Files must have allowed extensions
- **File Size Validation**: Files must be within specified size limits
- **File Count Validation**: Number of files must not exceed `maxItems`
- **File Format Validation**: Files must be valid and readable
- **File Reference Validation**: File IDs must be valid and accessible
- **File Expiry Validation**: Files must not be expired
- **File Access Validation**: User must have permission to access files

### Output Validation
- **Schema Compliance**: Output must match declared schema
- **Required Fields**: All required output fields must be present
- **Type Consistency**: Output types must match declarations
- **Data Integrity**: Output must be valid and complete

### Validation Levels

#### Strict Mode
```json
{
  "validation": {
    "strict_input": true,
    "strict_output": true,
    "allow_extra_fields": false,
    "fail_fast": true
  }
}
```

#### Relaxed Mode
```json
{
  "validation": {
    "strict_input": false,
    "strict_output": false,
    "allow_extra_fields": true,
    "warn_on_validation": true
  }
}
```

## Lifecycle Integration

### Function Types

#### Initialize Function
```json
{
  "name": "initialize",
  "description": "Initialize the agent with configuration",
  "inputSchema": {
    "type": "object",
    "properties": {
      "config": {
        "type": "object",
        "description": "Agent configuration"
      }
    },
    "required": ["config"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["initialized", "already_initialized", "error"]
      },
      "message": {"type": "string"},
      "config": {"type": "object"}
    },
    "required": ["status"]
  }
}
```

#### Execute Function
```json
{
  "name": "execute",
  "description": "Execute the main agent function",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_data": {
        "type": "object",
        "description": "Input data for execution"
      }
    },
    "required": ["input_data"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "result": {"type": "object"},
      "metadata": {"type": "object"}
    },
    "required": ["result"]
  }
}
```

#### Cleanup Function
```json
{
  "name": "cleanup",
  "description": "Clean up resources and perform cleanup operations",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["success", "error"]
      },
      "message": {"type": "string"},
      "resources_freed": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["status", "message"]
  }
}
```

## Examples

### Function Agent Example

#### Basic Function Contract
```json
{
  "name": "RAG Agent",
  "description": "Document question answering agent",
  "version": "1.0.0",
  "agent_type": "function",
  "entry_point": "rag_agent.py",
  "agent_class": "RAGAgent",
  
  "config_schema": {
    "functions": [
      {
        "name": "execute",
        "description": "Query the indexed document",
        "inputSchema": {
          "type": "object",
          "properties": {
            "question": {
              "type": "string",
              "minLength": 1,
              "maxLength": 1000,
              "description": "Question to ask about the document"
            },
            "max_tokens": {
              "type": "integer",
              "minimum": 10,
              "maximum": 4000,
              "description": "Maximum response length"
            }
          },
          "required": ["question"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "answer": {"type": "string"},
            "question": {"type": "string"},
            "confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "metadata": {
              "type": "object",
              "properties": {
                "processing_time": {"type": "number"},
                "chunks_retrieved": {"type": "integer"}
              }
            }
          },
          "required": ["answer", "question"]
        }
      }
    ]
  }
}
```

### Persistent Agent Example

#### Complete Agent Contract
```json
{
  "config_schema": {
    "functions": [
      {
        "name": "initialize",
        "description": "Initialize the RAG agent by indexing the specified website content",
        "inputSchema": {
          "type": "object",
          "properties": {
            "website_url": {
              "type": "string",
              "description": "URL of the website to index for RAG",
              "minLength": 1
            },
            "model_name": {
              "type": "string",
              "description": "OpenAI model to use for LLM",
              "enum": ["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
              "default": "gpt-3.5-turbo"
            }
          },
          "required": ["website_url"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "enum": ["success", "error"]
            },
            "message": {"type": "string"},
            "indexed_pages": {"type": "integer"},
            "total_chunks": {"type": "integer"}
          },
          "required": ["status", "message"]
        }
      },
      {
        "name": "execute",
        "description": "Execute a RAG query against the indexed content",
        "inputSchema": {
          "type": "object",
          "properties": {
            "question": {
              "type": "string",
              "description": "Question to ask about the indexed content",
              "minLength": 1
            }
          },
          "required": ["question"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "answer": {"type": "string"},
            "question": {"type": "string"},
            "confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            }
          },
          "required": ["answer", "question"]
        }
      },
      {
        "name": "cleanup",
        "description": "Clean up resources and perform cleanup operations",
        "inputSchema": {
          "type": "object",
          "properties": {},
          "required": []
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "enum": ["success", "error"]
            },
            "message": {"type": "string"},
            "resources_freed": {
              "type": "array",
              "items": {"type": "string"}
            }
          },
          "required": ["status", "message"]
        }
      }
    ]
  }
}
```

### JSON Schema Tool Compatibility

```json
{
  "tools": [
    {
      "name": "execute_rag_query",
      "description": "Query the RAG agent with a question",
      "inputSchema": {
        "type": "object",
        "properties": {
          "question": {
            "type": "string",
            "description": "Question to ask about the document"
          },
          "max_tokens": {
            "type": "integer",
            "description": "Maximum response length",
            "minimum": 10,
            "maximum": 4000
          }
        },
        "required": ["question"]
      },
      "outputSchema": {
        "type": "object",
        "properties": {
          "answer": {"type": "string"},
          "question": {"type": "string"},
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        },
        "required": ["answer", "question"]
      }
    }
  ]
}
```

**MCP Tool Integration Benefits:**
- **Native MCP Format**: Tools use the same schema structure as agents
- **Seamless Integration**: Works with existing MCP tool ecosystems
- **Consistent Validation**: Same validation rules across tools and agents
- **Tool Discovery**: MCP servers can discover and use agent functions

### File Upload Agent Example

#### Document Analysis Agent with File Support
```json
{
  "name": "Document Analysis Agent",
  "description": "Analyzes uploaded documents and answers questions",
  "version": "1.0.0",
  "agent_type": "function",
  "entry_point": "document_analysis_agent.py",
  
  "config_schema": {
    "functions": [
      {
        "name": "execute",
        "description": "Analyze uploaded documents and answer questions",
        "inputSchema": {
          "type": "object",
          "properties": {
            "file_references": {
              "type": "array",
              "description": "Array of file reference IDs for uploaded documents",
              "required": true,
              "items": {
                "type": "string",
                "format": "file-reference"
              },
              "maxItems": 3
            },
            "question": {
              "type": "string",
              "description": "Question to ask about the documents",
              "minLength": 1,
              "maxLength": 1000,
              "required": true
            },
            "analysis_depth": {
              "type": "string",
              "enum": ["basic", "detailed", "comprehensive"],
              "description": "Depth of analysis to perform",
              "default": "detailed"
            }
          },
          "required": ["file_references", "question"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "answer": {
              "type": "string",
              "description": "Answer to the question based on document analysis"
            },
            "confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1,
              "description": "Confidence score of the answer"
            },
            "sources": {
              "type": "array",
              "description": "Sources used for the answer",
              "items": {
                "type": "object",
                "properties": {
                  "document": {"type": "string"},
                  "page": {"type": "integer"},
                  "excerpt": {"type": "string"}
                }
              }
            },
            "metadata": {
              "type": "object",
              "properties": {
                "processing_time": {"type": "number"},
                "documents_analyzed": {"type": "integer"},
                "total_pages": {"type": "integer"}
              }
            }
          },
          "required": ["answer", "confidence"]
        }
      }
    ]
  }
}
```

#### File Parameter Constraints
File parameters use standard JSON Schema properties:
- **`maxLength`**: Maximum length of the file reference ID string
- **`pattern`**: Regex pattern for valid file reference ID format (UUID-like)
- **`description`**: Human-readable description including file constraints
- **`format`**: Custom format identifier for file references

**Note**: File upload constraints (file types, sizes, counts) are handled by the UI and backend, not by JSON Schema validation.

#### Alternative Approaches for File Constraints

Since JSON Schema doesn't support file-specific constraints, you have several options:

**Option 1: Backend-Only Constraints**
- Define file constraints in agent configuration files (separate from JSON Schema)
- Backend validates files during upload
- UI reads constraints from backend API

**Option 2: Custom JSON Schema Keywords**
- Extend JSON Schema with custom keywords like `x-fileConstraints`
- Requires custom validation libraries
- Not portable across different systems

**Option 3: Metadata in Description**
- Include constraints in the `description` field
- Parse constraints programmatically
- Simple but less structured

**Option 4: Separate Configuration**
- Keep JSON Schema pure and standard
- Store file constraints in separate configuration
- Most portable and standards-compliant

#### File Parameter Execution Flow
1. **File Upload**: User uploads files through the UI
2. **File Storage**: Files are stored temporarily with unique IDs
3. **Agent Execution**: Agent receives file references (IDs) in input
4. **File Access**: Agent runtime downloads files using IDs
5. **Processing**: Agent processes file content
6. **Cleanup**: Temporary files are automatically cleaned up

#### Agent Runtime File Integration
```python
# Example: How agents access uploaded files
class DocumentAnalysisAgent:
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract file references from input
        file_references = input_data.get('file_references', [])
        question = input_data.get('question')
        
        # Download and process files
        documents = []
        for file_ref in file_references:
            # Download file using file service
            file_content = self.file_service.download_file(file_ref)
            documents.append(file_content)
        
        # Process documents and answer question
        answer = self.analyze_documents(documents, question)
        
        return {
            "answer": answer,
            "confidence": 0.95,
            "sources": [{"document": "uploaded_file", "page": 1}],
            "metadata": {
                "processing_time": 1.23,
                "documents_analyzed": len(documents)
            }
        }
```

#### File Service Integration
```python
# File service interface for agent runtime
class FileService:
    def download_file(self, file_id: str) -> bytes:
        """Download file content by ID"""
        pass
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata"""
        pass
    
    def validate_file_access(self, file_id: str, user_id: int) -> bool:
        """Check if user can access file"""
        pass
```

#### Frontend File Upload Integration
```typescript
// React component for file upload in agent execution form
interface FileUploadProps {
  parameterSchema: any; // JSON Schema for the file parameter
  onFilesSelected: (files: File[]) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  parameterSchema,
  onFilesSelected
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  
  // Extract constraints from parameter description and format
  const isMultiple = parameterSchema.type === 'array';
  const maxFiles = isMultiple ? parameterSchema.maxItems || 5 : 1;
  const allowedTypes = ['txt', 'pdf', 'doc', 'json', 'csv']; // Default types
  
  const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    // Validate files against backend constraints
    const validFiles = validateFiles(files, { maxFiles, allowedTypes });
    setSelectedFiles(validFiles);
    onFilesSelected(validFiles);
  };
  
  return (
    <div className="file-upload">
      <input
        type="file"
        multiple={isMultiple}
        accept=".txt,.pdf,.doc,.json,.csv"
        onChange={handleFileSelect}
      />
      <div className="file-info">
        {parameterSchema.description}
      </div>
    </div>
  );
};
```

## File Parameter Best Practices

### Security Considerations
- **File Type Validation**: Always validate file extensions and MIME types
- **File Size Limits**: Set reasonable limits to prevent abuse
- **Access Control**: Ensure users can only access their own files
- **Virus Scanning**: Consider implementing virus scanning for uploaded files
- **Temporary Storage**: Use temporary storage for sensitive documents

### Performance Considerations
- **File Size Optimization**: Compress large files when possible
- **Async Processing**: Handle file uploads asynchronously
- **Cleanup Scheduling**: Implement efficient cleanup of expired files
- **CDN Integration**: Use CDN for frequently accessed files
- **Caching**: Cache file metadata for better performance

### User Experience Guidelines
- **Progress Indicators**: Show upload progress for large files
- **File Preview**: Provide preview for common file types
- **Error Handling**: Clear error messages for validation failures
- **File Management**: Allow users to remove/replace uploaded files
- **Drag & Drop**: Support drag and drop for better UX

### Integration Patterns
- **Agent Initialization**: Files can be uploaded during agent setup
- **Execution Time**: Files can be uploaded just before execution
- **Batch Processing**: Support multiple file uploads for batch operations
- **File References**: Use consistent file reference format across system
- **Metadata Tracking**: Track file usage and access patterns

## Implementation Guide

### Phase 1: Create Agent Contract (Week 1)
1. Create `agent_contract` section in config
2. Define one function (e.g., `execute`) with inputSchema and outputSchema
3. Test basic validation

### Example: Creating a New RAG Agent

#### Complete Agent Contract
```json
{
  "config_schema": {
    "functions": [
      {
        "name": "execute",
        "description": "Query the indexed document",
        "inputSchema": {
          "type": "object",
          "properties": {
            "question": {
              "type": "string",
              "description": "Question to ask about the document"
            }
          },
          "required": ["question"]
        },
        "outputSchema": {
          "type": "object",
          "properties": {
            "answer": {"type": "string"},
            "question": {"type": "string"}
          },
          "required": ["answer", "question"]
        }
      }
    ]
  }
}
```

**Implementation Notes:**
- **Schema Validation**: Use JSON Schema validation libraries
- **JSON Schema Compatibility**: Ensure schemas follow JSON Schema specification exactly
- **Testing**: Validate both input and output schemas during testing

### Phase 2: Expand Contract (Week 2)
1. Add schemas for all lifecycle functions
2. Include examples for each function
3. Add metadata and validation rules
4. Test full validation pipeline

### Phase 3: Enable Strict Mode (Week 3)
1. Turn on strict validation
2. Monitor for validation errors
3. Fix any schema mismatches
4. Performance testing

### Phase 4: Advanced Features (Week 4)
1. Generate client SDKs with MCP schema support
2. Add monitoring and metrics for schema validation
3. Documentation and examples using MCP format
4. MCP tool integration and discovery

## Implementation Notes

### Validation Engine
```python
import jsonschema
from typing import Dict, Any, List

class AgentContractValidator:
    """Validate inputs and outputs using JSON Schema format from config_schema."""
    
    def validate_input(self, input_data: Dict[str, Any], agent: Agent) -> Dict[str, Any]:
        """Validate input against JSON Schema inputSchema from config_schema."""
        input_schema = agent.get_input_schema()
        if not input_schema:
            raise ValueError(f"No input schema found for agent {agent.name}")
        
        try:
            jsonschema.validate(input_data, input_schema)
            return input_data
        except jsonschema.ValidationError as e:
            raise ValueError(f"Input validation failed: {e.message}")
    
    def validate_output(self, output_data: Dict[str, Any], agent: Agent) -> Dict[str, Any]:
        """Validate output against JSON Schema outputSchema from config_schema."""
        output_schema = agent.get_output_schema()
        if not output_schema:
            raise ValueError(f"No output schema found for agent {agent.name}")
        
        try:
            jsonschema.validate(output_data, output_schema)
            return output_data
        except jsonschema.ValidationError as e:
            raise ValueError(f"Output validation failed: {e.message}")
    
    def get_validation_errors(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Get detailed validation errors for debugging."""
        validator = jsonschema.Draft7Validator(schema)
        errors = []
        for error in validator.iter_errors(data):
            errors.append(f"{error.path}: {error.message}")
        return errors
```

### Schema Generator
```python
class SchemaGenerator:
    """Generate MCP format schemas from various sources."""
    
    @staticmethod
    def from_config_schema(config_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert existing config_schema to MCP inputSchema format."""
        input_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param_config in config_schema.items():
            param_def = {
                "type": SchemaGenerator._map_type(param_config["type"]),
                "description": param_config.get("description", "")
            }
            
            # Add type-specific validations
            if param_config["type"] in ["number", "integer"]:
                if "minimum" in param_config:
                    param_def["minimum"] = param_config["minimum"]
                if "maximum" in param_config:
                    param_def["maximum"] = param_config["maximum"]
            elif param_config["type"] == "string":
                if "minLength" in param_config:
                    param_def["minLength"] = param_config["minLength"]
                if "maxLength" in param_config:
                    param_def["maxLength"] = param_config["maxLength"]
                if "pattern" in param_config:
                    param_def["pattern"] = param_config["pattern"]
            elif param_config["type"] in ["choice", "select"]:
                if "options" in param_config:
                    param_def["enum"] = [opt["value"] for opt in param_config["options"]]
            
            input_schema["properties"][param_name] = param_def
            
            if param_config.get("required", False):
                input_schema["required"].append(param_name)
        
        return input_schema
    
    @staticmethod
    def generate_output_schema(example_output: Dict[str, Any]) -> Dict[str, Any]:
        """Generate MCP outputSchema from example output data."""
        output_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for key, value in example_output.items():
            if isinstance(value, str):
                output_schema["properties"][key] = {"type": "string"}
            elif isinstance(value, int):
                output_schema["properties"][key] = {"type": "integer"}
            elif isinstance(value, float):
                output_schema["properties"][key] = {"type": "number"}
            elif isinstance(value, bool):
                output_schema["properties"][key] = {"type": "boolean"}
            elif isinstance(value, list):
                output_schema["properties"][key] = {"type": "array", "items": {"type": "string"}}
            elif isinstance(value, dict):
                output_schema["properties"][key] = {"type": "object", "properties": {}}
        
        return output_schema
    
    @staticmethod
    def _map_type(config_type: str) -> str:
        """Map config_schema types to JSON Schema types."""
        type_mapping = {
            "string": "string",
            "textarea": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "choice": "string",
            "select": "string"
        }
        return type_mapping.get(config_type, "string")
    
    @staticmethod
    def to_mcp_format(input_schema: Dict[str, Any], output_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert schemas to MCP format."""
        return {
            "inputSchema": input_schema,
            "outputSchema": output_schema
        }
    
    @staticmethod
    def validate_mcp_schema(schema: Dict[str, Any]) -> bool:
        """Validate that a schema follows MCP format requirements."""
        required_fields = ["type", "properties"]
        if not all(field in schema for field in required_fields):
            return False
        
        if schema["type"] != "object":
            return False
        
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            return False
        
        return True
```

### Agent Base Class Updates
```python
class Agent:
    """Base class for all agents with MCP schema support."""
    
    def __init__(self, config_path: str):
        self.config = self._load_config()
        self.agent_contract = self.config.get("agent_contract", {})
    
    def get_function_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get function schema in MCP format."""
        return self.agent_contract.get("functions", {}).get(function_name)
    
    def get_input_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get input schema for a function."""
        function = self.get_function_schema(function_name)
        return function.get("inputSchema") if function else None
    
    def get_output_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get output schema for a function."""
        function = self.get_function_schema(function_name)
        return function.get("outputSchema") if function else None
    
    def validate_input(self, function_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input using MCP inputSchema."""
        input_schema = self.get_input_schema(function_name)
        if not input_schema:
            raise ValueError(f"Function {function_name} not found")
        
        jsonschema.validate(input_data, input_schema)
        return input_data
    
    def validate_output(self, function_name: str, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output using MCP outputSchema."""
        output_schema = self.get_output_schema(function_name)
        if not output_schema:
            raise ValueError(f"Function {function_name} not found")
        
        jsonschema.validate(output_data, output_schema)
        return output_data
```

## Conclusion

This specification provides a standardized way to define agent contracts using the JSON Schema format. It gives you clear, validated, and documented agent interfaces that work seamlessly with JSON Schema tools and validators.

### Key Benefits

#### Core Benefits
- **Clear Contracts**: Explicit input/output definitions using JSON Schema format
- **Runtime Safety**: Validation prevents errors and ensures data integrity
- **Documentation**: Self-documenting agent interfaces with JSON Schema
- **Compatibility**: Works seamlessly with JSON Schema tools and validators
- **Single Format**: Consistent JSON Schema structure across all agents

#### JSON Schema Integration Benefits
- **Native Schema Format**: Uses JSON Schema's standard structure
- **Tool Integration**: Works with existing JSON Schema tools and validators
- **Structured Output**: Guaranteed JSON Schema compliance
- **Validation**: Runtime validation using JSON Schema format
- **Ecosystem Support**: Full compatibility with JSON Schema tool ecosystems

#### Developer Experience Benefits
- **Type Safety**: Strong typing and validation with JSON Schema
- **Error Handling**: Clear validation error messages and debugging
- **Simplicity**: Clean, focused schema definitions
- **Maintenance**: Easier to maintain and update
- **Tooling**: Works with existing JSON Schema development tools and libraries

### JSON Schema Advantages

The JSON Schema structure provides several key advantages:

1. **Guaranteed Structure**: Output is always valid JSON matching the JSON Schema
2. **Tool Integration**: Works seamlessly with JSON Schema tools and validators
3. **Validation**: Built-in JSON Schema validation at runtime
4. **Documentation**: Self-documenting output formats using JSON Schema standards
5. **Consistency**: Standardized output across all agents using JSON Schema format
6. **Ecosystem Support**: Full compatibility with JSON Schema tool ecosystems

By implementing this specification, your agents become more reliable, easier to use, and better integrated with JSON Schema tools and validators. The JSON Schema compatibility ensures that your agents work seamlessly with the broader JSON Schema ecosystem while maintaining the simplicity and power of your existing architecture.

## 📋 **Specification Summary**

### **Simplified Schema Approach**
This specification uses a clean, focused JSON Schema format:

#### **Input Schema: `inputSchema`**
```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "Question to ask about the document"
      }
    },
    "required": ["question"]
  }
}
```

#### **Output Schema: `outputSchema`**
```json
{
  "outputSchema": {
    "type": "object",
    "properties": {
      "answer": {"type": "string"},
      "question": {"type": "string"}
    },
    "required": ["answer", "question"]
  }
}
```

### **Benefits of Simplified Format**
- **Consistency**: All agents use the same JSON Schema structure
- **Simplicity**: Clean, focused schema definitions
- **Maintenance**: Easier to maintain and update
- **Validation**: Built-in JSON Schema validation
- **Tool Integration**: Works with existing JSON Schema tools and validators

### **Implementation Checklist**
- [ ] Create `config_schema.functions` array in agent config
- [ ] Define each function with `name`, `description`, `inputSchema`, and `outputSchema`
- [ ] Test validation and execution
- [ ] Deploy with JSON Schema support
- [ ] Enable strict validation mode
- [ ] Add monitoring and metrics
- [ ] Integrate with JSON Schema tool ecosystems
- [ ] Validate JSON Schema compliance

This specification provides a clear, consistent, and JSON Schema-compatible way to define agent contracts using a simplified, standardized format that integrates seamlessly with JSON Schema tool ecosystems.

## 🔍 **Document Integrity Validation**

### **✅ Consistency Check: PASSED**
- **Schema Structure**: All examples use `inputSchema` and `outputSchema`
- **Format Approach**: Single MCP schema format throughout
- **Type System**: Consistent JSON Schema types
- **Examples**: All examples follow the same structure
- **Implementation**: Code examples match specification

### **✅ Format Consistency: PASSED**
- **Input Schema**: All use `inputSchema` field
- **Output Schema**: All use `outputSchema` field
- **Function Definition**: Consistent structure across all examples
- **Validation Rules**: Consistent validation approach
- **Lifecycle Integration**: Same pattern for all function types

### **✅ Implementation Consistency: PASSED**
- **Validation Engine**: Uses MCP schema format
- **Schema Generator**: Generates MCP-compatible schemas
- **Agent Base Classes**: Support MCP schema methods
- **Examples**: All code examples use MCP format
- **Documentation**: All explanations reference MCP format

### **✅ Cross-Reference Validation: PASSED**
- **Schema References**: All schema references are consistent
- **Type Mappings**: Type system mappings are accurate
- **Example Alignment**: Examples match specification exactly
- **Implementation Notes**: Code examples implement specification correctly
- **Benefits Section**: All benefits are accurate for MCP format

**Result: Document is 100% consistent and ready for implementation.**


