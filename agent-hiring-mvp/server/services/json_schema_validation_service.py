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
    
    def validate_json_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate that a schema follows JSON Schema format requirements."""
        required_fields = ["type", "properties"]
        if not all(field in schema for field in required_fields):
            return False
        
        if schema["type"] != "object":
            return False
        
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            return False
        
        return True
    
    def validate_agent_config_schema(self, config_schema: Dict[str, Any]) -> bool:
        """Validate that an agent's config_schema follows JSON Schema format."""
        if not config_schema:
            return False
        
        # Check if it's the new functions array format
        if "functions" in config_schema:
            return self._validate_functions_array_format(config_schema)
        
        # Legacy format validation (for backward compatibility)
        return self._validate_legacy_config_schema(config_schema)
    
    def _validate_functions_array_format(self, config_schema: Dict[str, Any]) -> bool:
        """
        Validate the new config_schema.functions array format.
        
        Args:
            config_schema: The config_schema with functions array
            
        Returns:
            True if valid, False otherwise
        """
        functions = config_schema.get("functions")
        if not isinstance(functions, list) or len(functions) == 0:
            return False
        
        # Valid function fields - only essential fields
        valid_function_fields = {
            "name", "description", "inputSchema", "outputSchema"
        }
        
        for function in functions:
            if not isinstance(function, dict):
                return False
            
            # Validate required fields
            if "name" not in function or "description" not in function:
                return False
            
            # Validate function name
            function_name = function["name"]
            if not isinstance(function_name, str) or not function_name.strip():
                return False
            
            # Validate unknown fields
            unknown_fields = set(function.keys()) - valid_function_fields
            if unknown_fields:
                return False
            
            # Validate inputSchema if present
            if "inputSchema" in function:
                if not self.validate_json_schema(function["inputSchema"]):
                    return False
            
            # Validate outputSchema if present
            if "outputSchema" in function:
                if not self.validate_json_schema(function["outputSchema"]):
                    return False
        
        return True
    
    def _validate_legacy_config_schema(self, config_schema: Dict[str, Any]) -> bool:
        """
        Validate the legacy config_schema format (for backward compatibility).
        
        Args:
            config_schema: The legacy config_schema format
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name", "description", "inputSchema", "outputSchema"]
        if not all(field in config_schema for field in required_fields):
            return False
        
        # Validate inputSchema
        if not self.validate_json_schema(config_schema.get("inputSchema", {})):
            return False
        
        # Validate outputSchema
        if not self.validate_json_schema(config_schema.get("outputSchema", {})):
            return False
        
        return True
