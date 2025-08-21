"""JSON Schema Validation Service for Agent Input/Output Validation."""

import jsonschema
from typing import Dict, Any, Optional, List
from server.models.agent import Agent


class JSONSchemaValidationService:
    """Validate inputs and outputs using JSON Schema format from config_schema."""
    
    def __init__(self):
        self.validator = jsonschema.Draft7Validator
    
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
        validator = self.validator(schema)
        errors = []
        for error in validator.iter_errors(data):
            errors.append(f"{error.path}: {error.message}")
        return errors
    
    def validate_json_schema(self, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate that a schema follows JSON Schema format requirements."""
        required_fields = ["type", "properties"]
        if not all(field in schema for field in required_fields):
            return False, f"Missing required fields: {', '.join(required_fields)}"
        
        if schema["type"] != "object":
            return False, "Schema type must be 'object'"
        
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            return False, "Schema must have 'properties' field as an object"
        
        return True, None
    
    def validate_agent_config_schema(self, config_schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate that an agent's config_schema follows JSON Schema format.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not config_schema:
            return False, "config_schema is required but was not provided"
        
        # Check if it's the new functions array format
        if "functions" in config_schema:
            return self._validate_functions_array_format(config_schema)
        
        # Check if it's a simple property-based schema (legacy format)
        if isinstance(config_schema, dict) and "type" in config_schema:
            # This is a simple JSON Schema object, validate it
            return self._validate_simple_json_schema(config_schema)
        
        # Legacy format validation (for backward compatibility)
        return self._validate_legacy_config_schema(config_schema)
    
    def _validate_functions_array_format(self, config_schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate the new config_schema.functions array format.
        
        Args:
            config_schema: The config_schema with functions array
            
        Returns:
            tuple: (is_valid, error_message)
        """
        functions = config_schema.get("functions")
        if not isinstance(functions, list):
            return False, "config_schema.functions must be an array"
        
        if len(functions) == 0:
            return False, "config_schema.functions array cannot be empty"
        
        # Valid function fields - only essential fields
        valid_function_fields = {
            "name", "description", "inputSchema", "outputSchema"
        }
        
        for i, function in enumerate(functions):
            if not isinstance(function, dict):
                return False, f"config_schema.functions[{i}] must be an object"
            
            # Validate required fields
            if "name" not in function:
                return False, f"config_schema.functions[{i}].name is required"
            if "description" not in function:
                return False, f"config_schema.functions[{i}].description is required"
            
            # Validate function name
            function_name = function["name"]
            if not isinstance(function_name, str) or not function_name.strip():
                return False, f"config_schema.functions[{i}].name must be a non-empty string"
            
            # Validate unknown fields
            unknown_fields = set(function.keys()) - valid_function_fields
            if unknown_fields:
                return False, f"config_schema.functions[{i}] contains unknown fields: {', '.join(unknown_fields)}"
            
            # Validate inputSchema if present
            if "inputSchema" in function:
                is_valid, error_msg = self.validate_json_schema(function["inputSchema"])
                if not is_valid:
                    return False, f"config_schema.functions[{i}].inputSchema: {error_msg}"
            
            # Validate outputSchema if present
            if "outputSchema" in function:
                is_valid, error_msg = self.validate_json_schema(function["outputSchema"])
                if not is_valid:
                    return False, f"config_schema.functions[{i}].outputSchema: {error_msg}"
        
        return True, None
    
    def _validate_simple_json_schema(self, config_schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a simple JSON Schema object (property-based format).
        
        Args:
            config_schema: A simple JSON Schema object
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Basic JSON Schema validation
        if not isinstance(config_schema, dict):
            return False, "config_schema must be an object"
        
        if "type" not in config_schema:
            return False, "config_schema must have a 'type' field"
        
        if config_schema["type"] != "object":
            return False, "config_schema type must be 'object'"
        
        if "properties" not in config_schema:
            return False, "config_schema must have a 'properties' field"
        
        if not isinstance(config_schema["properties"], dict):
            return False, "config_schema.properties must be an object"
        
        # Validate each property
        for prop_name, prop_schema in config_schema["properties"].items():
            if not isinstance(prop_schema, dict):
                return False, f"Property '{prop_name}' schema must be an object"
            
            if "type" not in prop_schema:
                return False, f"Property '{prop_name}' must have a 'type' field"
            
            # Basic type validation
            valid_types = ["string", "integer", "number", "boolean", "array", "object"]
            if prop_schema["type"] not in valid_types:
                return False, f"Property '{prop_name}' has invalid type '{prop_schema['type']}'. Valid types: {', '.join(valid_types)}"
        
        return True, None
    
    def _validate_legacy_config_schema(self, config_schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate the legacy config_schema format (for backward compatibility).
        
        Args:
            config_schema: The legacy config_schema format
            
        Returns:
            tuple: (is_valid, error_message)
        """
        required_fields = ["name", "description", "inputSchema", "outputSchema"]
        missing_fields = [field for field in required_fields if field not in config_schema]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Validate inputSchema
        is_valid, error_msg = self.validate_json_schema(config_schema.get("inputSchema", {}))
        if not is_valid:
            return False, f"inputSchema: {error_msg}"
        
        # Validate outputSchema
        is_valid, error_msg = self.validate_json_schema(config_schema.get("outputSchema", {}))
        if not is_valid:
            return False, f"outputSchema: {error_msg}"
        
        return True, None
