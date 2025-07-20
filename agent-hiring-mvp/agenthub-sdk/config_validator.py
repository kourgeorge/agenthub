#!/usr/bin/env python3
"""
AgentHub Agent Configuration Validator

This module provides utilities to validate agent configuration files
against the AgentHub schema specification.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema
from jsonschema import Draft7Validator, ValidationError


class AgentConfigValidator:
    """Validator for AgentHub agent configuration files."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the validator.
        
        Args:
            schema_path: Path to the JSON schema file. If None, uses the default schema.
        """
        if schema_path is None:
            schema_path = str(Path(__file__).parent / "agent_config_schema.json")
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        self.validator = Draft7Validator(self.schema)
    
    def validate_config(self, config_data: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration dictionary against the schema.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            self.validator.validate(config_data)
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            if e.path:
                errors.append(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")
        
        # Additional custom validations
        custom_errors = self._custom_validations(config_data)
        errors.extend(custom_errors)
        
        return errors
    
    def validate_config_file(self, config_path: str) -> List[str]:
        """
        Validate a configuration file.
        
        Args:
            config_path: Path to the config.json file
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            return [f"Config file not found: {config_path}"]
        except json.JSONDecodeError as e:
            return [f"Invalid JSON in config file: {str(e)}"]
        except Exception as e:
            return [f"Error reading config file: {str(e)}"]
        
        return self.validate_config(config_data)
    
    def _custom_validations(self, config_data: Dict[str, Any]) -> List[str]:
        """
        Perform additional custom validations beyond JSON schema.
        
        Args:
            config_data: The configuration data to validate
            
        Returns:
            List of custom validation error messages
        """
        errors = []
        
        # Validate config_schema if present
        if "config_schema" in config_data:
            schema_errors = self._validate_config_schema(config_data["config_schema"])
            errors.extend(schema_errors)
        
        # Validate entry point file exists (if we have access to the file system)
        if "entry_point" in config_data:
            entry_point = config_data["entry_point"]
            if not entry_point.endswith('.py'):
                errors.append(f"Entry point must be a Python file (.py), got: {entry_point}")
        
        # Validate version format
        if "version" in config_data:
            version = config_data["version"]
            if not self._is_valid_version(version):
                errors.append(f"Invalid version format: {version}. Expected format: X.Y.Z")
        
        # Validate pricing model consistency
        if "pricing_model" in config_data:
            pricing_model = config_data["pricing_model"]
            if pricing_model == "per_use" and "price_per_use" not in config_data:
                errors.append("per_use pricing model requires price_per_use field")
            elif pricing_model == "monthly" and "monthly_price" not in config_data:
                errors.append("monthly pricing model requires monthly_price field")
        
        # Validate ACP server requirements
        if config_data.get("agent_type") == "acp_server":
            if "acp_manifest" not in config_data:
                errors.append("ACP server agents require acp_manifest field")
            else:
                acp_errors = self._validate_acp_manifest(config_data["acp_manifest"])
                errors.extend(acp_errors)
        
        return errors
    
    def _validate_config_schema(self, config_schema: Dict[str, Any]) -> List[str]:
        """
        Validate the config_schema section.
        
        Args:
            config_schema: The config_schema to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not isinstance(config_schema, dict):
            errors.append("config_schema must be a dictionary")
            return errors
        
        # Valid parameter types
        valid_types = {
            "string", "number", "integer", "float", "boolean", 
            "choice", "select", "textarea", "array", "object"
        }
        
        for param_name, param_config in config_schema.items():
            # Validate parameter name
            if not isinstance(param_name, str) or not param_name.strip():
                errors.append(f"Parameter name must be a non-empty string, got: {param_name}")
                continue
            
            # Validate parameter config is a dictionary
            if not isinstance(param_config, dict):
                errors.append(f"Parameter '{param_name}' config must be a dictionary")
                continue
            
            # Validate required fields
            if "type" not in param_config:
                errors.append(f"Parameter '{param_name}' missing required 'type' field")
                continue
            
            param_type = param_config["type"]
            
            # Validate parameter type
            if param_type not in valid_types:
                errors.append(f"Parameter '{param_name}' has invalid type '{param_type}'. Valid types: {', '.join(sorted(valid_types))}")
                continue
            
            # Validate type-specific requirements
            if param_type == "choice":
                # Choice parameters must have either 'options' or 'choices' array
                has_options = "options" in param_config
                has_choices = "choices" in param_config
                
                if not has_options and not has_choices:
                    errors.append(f"Parameter '{param_name}' (choice type) must have either 'options' or 'choices' array")
                elif has_options and has_choices:
                    errors.append(f"Parameter '{param_name}' (choice type) cannot have both 'options' and 'choices' arrays")
                elif has_options:
                    # Validate options format
                    options = param_config["options"]
                    if not isinstance(options, list):
                        errors.append(f"Parameter '{param_name}' options must be a list")
                    else:
                        for i, option in enumerate(options):
                            if not isinstance(option, dict):
                                errors.append(f"Parameter '{param_name}' option {i} must be a dictionary")
                            elif "value" not in option or "label" not in option:
                                errors.append(f"Parameter '{param_name}' option {i} must have 'value' and 'label' fields")
                elif has_choices:
                    # Validate choices format (legacy format)
                    choices = param_config["choices"]
                    if not isinstance(choices, list):
                        errors.append(f"Parameter '{param_name}' choices must be a list")
                    elif not all(isinstance(choice, str) for choice in choices):
                        errors.append(f"Parameter '{param_name}' choices must be a list of strings")
            
            elif param_type == "select":
                # Select parameters must have 'options' array
                if "options" not in param_config:
                    errors.append(f"Parameter '{param_name}' (select type) must have 'options' array")
                else:
                    options = param_config["options"]
                    if not isinstance(options, list):
                        errors.append(f"Parameter '{param_name}' options must be a list")
                    else:
                        for i, option in enumerate(options):
                            if not isinstance(option, dict):
                                errors.append(f"Parameter '{param_name}' option {i} must be a dictionary")
                            elif "value" not in option or "label" not in option:
                                errors.append(f"Parameter '{param_name}' option {i} must have 'value' and 'label' fields")
            
            elif param_type in ["number", "integer", "float"]:
                # Numeric parameters can have min/max constraints
                for constraint in ["min", "max", "minimum", "maximum"]:
                    if constraint in param_config:
                        value = param_config[constraint]
                        if not isinstance(value, (int, float)):
                            errors.append(f"Parameter '{param_name}' {constraint} must be a number")
            
            elif param_type == "string":
                # String parameters can have pattern validation
                if "pattern" in param_config:
                    pattern = param_config["pattern"]
                    if not isinstance(pattern, str):
                        errors.append(f"Parameter '{param_name}' pattern must be a string")
                    else:
                        try:
                            import re
                            re.compile(pattern)
                        except re.error:
                            errors.append(f"Parameter '{param_name}' pattern is not a valid regex")
            
            # Validate default value type matches parameter type
            if "default" in param_config:
                default_value = param_config["default"]
                if param_type == "boolean" and not isinstance(default_value, bool):
                    errors.append(f"Parameter '{param_name}' default value must be boolean for boolean type")
                elif param_type in ["number", "integer", "float"] and not isinstance(default_value, (int, float)):
                    errors.append(f"Parameter '{param_name}' default value must be a number for {param_type} type")
                elif param_type == "string" and not isinstance(default_value, str):
                    errors.append(f"Parameter '{param_name}' default value must be a string for string type")
                elif param_type == "choice" and "options" in param_config:
                    # Check if default value exists in options
                    valid_values = [opt["value"] for opt in param_config["options"]]
                    if default_value not in valid_values:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in options: {valid_values}")
                elif param_type == "choice" and "choices" in param_config:
                    # Check if default value exists in choices (legacy format)
                    if default_value not in param_config["choices"]:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in choices: {param_config['choices']}")
                elif param_type == "select":
                    # Check if default value exists in options
                    valid_values = [opt["value"] for opt in param_config["options"]]
                    if default_value not in valid_values:
                        errors.append(f"Parameter '{param_name}' default value '{default_value}' not found in options: {valid_values}")
        
        return errors
    
    def _validate_acp_manifest(self, acp_manifest: Dict[str, Any]) -> List[str]:
        """
        Validate ACP manifest structure.
        
        Args:
            acp_manifest: The ACP manifest to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        required_fields = ["acp_version", "endpoints", "capabilities", "deployment"]
        for field in required_fields:
            if field not in acp_manifest:
                errors.append(f"ACP manifest missing required field: {field}")
        
        return errors
    
    def _is_valid_version(self, version: str) -> bool:
        """
        Check if version string follows semantic versioning format.
        
        Args:
            version: Version string to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))


def validate_agent_config(config_path: str, schema_path: Optional[str] = None) -> List[str]:
    """
    Convenience function to validate an agent configuration file.
    
    Args:
        config_path: Path to the config.json file
        schema_path: Path to the JSON schema file (optional)
        
    Returns:
        List of validation error messages (empty if valid)
    """
    validator = AgentConfigValidator(schema_path)
    return validator.validate_config_file(config_path)


def main():
    """Command-line interface for the config validator."""
    if len(sys.argv) < 2:
        print("Usage: python config_validator.py <config_file> [schema_file]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    schema_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    errors = validate_agent_config(config_path, schema_path)
    
    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ Configuration is valid!")


if __name__ == "__main__":
    main() 