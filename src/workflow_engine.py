"""
Workflow Engine.
Loads, validates, and executes user-defined workflows from YAML.
"""

import re
import time
import yaml
from pathlib import Path
from datetime import datetime
from typing import Any, Callable


class WorkflowError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowEngine:
    """
    Executes user-defined workflows from YAML configuration.
    
    Workflows are sequences of actions that map to existing API functions.
    Supports variable substitution and conditional execution.
    """
    
    def __init__(self, workflows_path: str = None):
        # Default to project root (parent of src/)
        if workflows_path is None:
            project_root = Path(__file__).parent.parent
            self.workflows_path = project_root / "workflows.yaml"
        else:
            self.workflows_path = Path(workflows_path)
        self.actions: dict[str, Callable] = {}
    
    def register_action(self, name: str, func: Callable):
        """Register an action that can be used in workflows."""
        self.actions[name] = func
    
    def register_actions(self, actions: dict[str, Callable]):
        """Register multiple actions at once."""
        self.actions.update(actions)
    
    def _load_workflows(self) -> dict:
        """Load workflows from YAML file. Fresh read every time for instant updates."""
        if not self.workflows_path.exists():
            # Auto-copy from example file if it exists
            example_path = self.workflows_path.with_suffix('.example.yaml')
            if example_path.exists():
                import shutil
                shutil.copy(example_path, self.workflows_path)
            else:
                return {"workflows": {}}
        
        try:
            with open(self.workflows_path, "r") as f:
                data = yaml.safe_load(f) or {}
            return data
        except yaml.YAMLError as e:
            raise WorkflowError(f"Invalid YAML in workflows file: {e}")
    
    def _save_workflows(self, data: dict):
        """Save workflows to YAML file."""
        with open(self.workflows_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def list_workflows(self) -> list[dict]:
        """List all defined workflows."""
        data = self._load_workflows()
        workflows = data.get("workflows", {})
        
        result = []
        for name, config in workflows.items():
            result.append({
                "name": name,
                "description": config.get("description", ""),
                "inputs": config.get("inputs", []),
                "steps_count": len(config.get("steps", [])),
            })
        return result
    
    def get_workflow(self, name: str) -> dict | None:
        """Get a specific workflow definition."""
        data = self._load_workflows()
        workflows = data.get("workflows", {})
        
        if name not in workflows:
            return None
        
        return {
            "name": name,
            **workflows[name]
        }
    
    def create_workflow(self, name: str, config: dict) -> dict:
        """Create or update a workflow."""
        data = self._load_workflows()
        if "workflows" not in data:
            data["workflows"] = {}
        
        # Validate the workflow config
        self._validate_workflow_config(config)
        
        data["workflows"][name] = config
        self._save_workflows(data)
        
        return {"name": name, **config}
    
    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow. Returns True if deleted, False if not found."""
        data = self._load_workflows()
        workflows = data.get("workflows", {})
        
        if name not in workflows:
            return False
        
        del workflows[name]
        self._save_workflows(data)
        return True
    
    def _validate_workflow_config(self, config: dict):
        """Validate workflow configuration."""
        if "steps" not in config:
            raise WorkflowError("Workflow must have 'steps'")
        
        if not isinstance(config["steps"], list):
            raise WorkflowError("'steps' must be a list")
        
        for i, step in enumerate(config["steps"]):
            if "action" not in step:
                raise WorkflowError(f"Step {i} missing 'action'")
            
            action_name = step["action"]
            if action_name not in self.actions:
                raise WorkflowError(f"Step {i}: Unknown action '{action_name}'")
    
    def _substitute_variables(self, value: Any, context: dict) -> Any:
        """
        Substitute variables in a value.
        
        Supports:
        - {{ input.name }} - runtime input
        - {{ steps[0].field }} - previous step output
        - {{ timestamp }} - current timestamp
        """
        if isinstance(value, str):
            # Find all {{ ... }} patterns
            pattern = r"\{\{\s*(.+?)\s*\}\}"
            
            def replace(match):
                expr = match.group(1)
                try:
                    return str(self._evaluate_expression(expr, context))
                except Exception:
                    return match.group(0)  # Keep original if evaluation fails
            
            return re.sub(pattern, replace, value)
        
        elif isinstance(value, dict):
            return {k: self._substitute_variables(v, context) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._substitute_variables(item, context) for item in value]
        
        return value
    
    def _evaluate_expression(self, expr: str, context: dict) -> Any:
        """
        Evaluate a simple expression.
        
        Supported:
        - input.name -> context["input"]["name"]
        - steps[0].field -> context["steps"][0]["field"]
        - timestamp -> current ISO timestamp
        """
        expr = expr.strip()
        
        # Built-in variables
        if expr == "timestamp":
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if expr == "date":
            return datetime.now().strftime("%Y-%m-%d")
        
        if expr == "time":
            return datetime.now().strftime("%H:%M:%S")
        
        # input.field
        if expr.startswith("input."):
            field = expr[6:]
            return context.get("input", {}).get(field, "")
        
        # steps[n].field
        steps_match = re.match(r"steps\[(\d+)\]\.(.+)", expr)
        if steps_match:
            index = int(steps_match.group(1))
            field = steps_match.group(2)
            steps = context.get("steps", [])
            if index < len(steps):
                return steps[index].get(field, "")
            return ""
        
        # steps[n] (whole object)
        steps_match = re.match(r"steps\[(\d+)\]$", expr)
        if steps_match:
            index = int(steps_match.group(1))
            steps = context.get("steps", [])
            if index < len(steps):
                return steps[index]
            return {}
        
        return ""
    
    def _check_time_conditions(self, time_after: str | None, time_before: str | None, days: list) -> str | None:
        """
        Check time-based conditions.
        Returns skip reason string if conditions not met, None if OK to run.
        """
        from datetime import datetime
        
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%a").lower()  # mon, tue, wed, etc.
        
        # Check day of week
        if days:
            if current_day not in days:
                return f"not scheduled for {current_day} (only {', '.join(days)})"
        
        # Check time_after (only run after this time)
        if time_after:
            if current_time < time_after:
                return f"too early (runs after {time_after}, now {current_time})"
        
        # Check time_before (only run before this time)
        if time_before:
            if current_time >= time_before:
                return f"too late (runs before {time_before}, now {current_time})"
        
        return None  # All conditions met
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """
        Evaluate a condition string.
        
        Supported operators: ==, !=, >, <, >=, <=
        Supported values: strings, numbers, booleans
        """
        if condition.lower() == "true":
            return True
        if condition.lower() == "false":
            return False
        
        # Parse comparison operators
        operators = ["!=", "==", ">=", "<=", ">", "<"]
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = self._evaluate_expression(parts[0].strip(), context)
                    right_str = parts[1].strip()
                    
                    # Parse right side - could be a variable or literal
                    if right_str.startswith("'") and right_str.endswith("'"):
                        right = right_str[1:-1]
                    elif right_str.startswith('"') and right_str.endswith('"'):
                        right = right_str[1:-1]
                    elif right_str.lower() == "true":
                        right = True
                    elif right_str.lower() == "false":
                        right = False
                    elif right_str == "''":
                        right = ""
                    else:
                        try:
                            right = float(right_str) if "." in right_str else int(right_str)
                        except ValueError:
                            # Treat as variable reference
                            right = self._evaluate_expression(right_str, context)
                    
                    # Compare
                    try:
                        if op == "==":
                            return left == right
                        elif op == "!=":
                            return left != right
                        elif op == ">":
                            return float(left) > float(right)
                        elif op == "<":
                            return float(left) < float(right)
                        elif op == ">=":
                            return float(left) >= float(right)
                        elif op == "<=":
                            return float(left) <= float(right)
                    except (ValueError, TypeError):
                        return False
        
        # If no operator found, treat as truthy check
        value = self._evaluate_expression(condition, context)
        if isinstance(value, str):
            return value != ""
        return bool(value)
    
    def run(self, name: str, inputs: dict | None = None) -> dict:
        """
        Execute a workflow by name.
        
        Args:
            name: Workflow name
            inputs: Optional runtime inputs
        
        Returns:
            Execution result with step details
        """
        workflow = self.get_workflow(name)
        if not workflow:
            raise WorkflowError(f"Workflow '{name}' not found")
        
        # Validate required inputs
        input_defs = workflow.get("inputs", [])
        resolved_inputs = {}
        
        for input_def in input_defs:
            input_name = input_def.get("name") if isinstance(input_def, dict) else input_def
            required = input_def.get("required", False) if isinstance(input_def, dict) else False
            default = input_def.get("default") if isinstance(input_def, dict) else None
            
            if inputs and input_name in inputs:
                resolved_inputs[input_name] = inputs[input_name]
            elif default is not None:
                resolved_inputs[input_name] = default
            elif required:
                raise WorkflowError(f"Missing required input: {input_name}")
        
        # Add any extra inputs passed
        if inputs:
            for key, value in inputs.items():
                if key not in resolved_inputs:
                    resolved_inputs[key] = value
        
        # Execution context
        context = {
            "input": resolved_inputs,
            "steps": [],
        }
        
        results = []
        start_time = time.time()
        
        steps = workflow.get("steps", [])
        
        for i, step in enumerate(steps):
            action_name = step["action"]
            condition = step.get("if")
            delay = step.get("delay")
            time_after = step.get("time_after")
            time_before = step.get("time_before")
            days = step.get("days", [])
            params = step.get("params", {})
            
            # Evaluate time-based conditions
            skip_reason = self._check_time_conditions(time_after, time_before, days)
            if skip_reason:
                results.append({
                    "step": i,
                    "action": action_name,
                    "status": "skipped",
                    "reason": skip_reason,
                })
                context["steps"].append({"skipped": True})
                continue
            
            # Evaluate condition (still supported for YAML power users)
            if condition and not self._evaluate_condition(condition, context):
                results.append({
                    "step": i,
                    "action": action_name,
                    "status": "skipped",
                    "reason": "condition not met",
                })
                context["steps"].append({"skipped": True})
                continue
            
            # Apply delay if specified
            if delay and delay > 0:
                time.sleep(float(delay))
            
            # Substitute variables in params
            resolved_params = self._substitute_variables(params, context)
            
            # Execute action
            action_func = self.actions.get(action_name)
            if not action_func:
                raise WorkflowError(f"Step {i}: Unknown action '{action_name}'")
            
            try:
                output = action_func(**resolved_params) if resolved_params else action_func()
                
                # Normalize output to dict
                if isinstance(output, str):
                    step_output = {"message": output, "success": True}
                elif isinstance(output, dict):
                    step_output = {**output, "success": True}
                else:
                    step_output = {"result": output, "success": True}
                
                context["steps"].append(step_output)
                results.append({
                    "step": i,
                    "action": action_name,
                    "status": "ok",
                    "output": step_output,
                })
                
            except Exception as e:
                # Fail fast on first error
                raise WorkflowError(f"Step {i} ({action_name}) failed: {str(e)}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "workflow": name,
            "steps_executed": len([r for r in results if r["status"] == "ok"]),
            "steps_skipped": len([r for r in results if r["status"] == "skipped"]),
            "results": results,
            "duration_ms": duration_ms,
        }


# Global instance
workflow_engine = WorkflowEngine()


