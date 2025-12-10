from typing import List
import json
import os
from app.models import Plan, PlanStep, TicketWebhook
from app.llm import get_llm_provider
from app.tools import validate_tool, is_destructive
from pydantic import ValidationError


class PlannerError(Exception):
    """Exception raised when planning fails"""
    pass


class Planner:
    """Planner that uses LLM to create action plans for tickets"""
    
    def __init__(self):
        self.llm = get_llm_provider()
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the planner prompt template"""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "planner_prompt.txt"
        )
        
        try:
            with open(prompt_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise PlannerError(f"Prompt template not found at {prompt_path}")
    
    def _format_prompt(self, ticket: TicketWebhook) -> str:
        """Format the prompt with ticket information"""
        return self.prompt_template.format(
            ticket_id=ticket.ticket_id,
            user_id=ticket.user_id,
            subject=ticket.subject,
            body=ticket.body
        )
    
    def _parse_llm_response(self, response: str) -> List[dict]:
        """Parse the LLM response to extract plan steps"""
        try:
            # Try to extract JSON from response
            # Sometimes LLM may include extra text, so we look for the array
            response = response.strip()
            
            # Find JSON array in response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = response[start_idx:end_idx]
            steps = json.loads(json_str)
            
            if not isinstance(steps, list):
                raise ValueError("Response is not a list of steps")
            
            return steps
            
        except json.JSONDecodeError as e:
            raise PlannerError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response}")
        except Exception as e:
            raise PlannerError(f"Failed to parse LLM response: {e}")
    
    def _validate_plan_steps(self, steps: List[dict]) -> List[PlanStep]:
        """Validate and convert plan steps to PlanStep objects"""
        validated_steps = []
        
        for step_data in steps:
            try:
                # Validate required fields
                if "step" not in step_data:
                    raise ValueError("Step number is required")
                if "tool" not in step_data:
                    raise ValueError("Tool name is required")
                if "args" not in step_data:
                    raise ValueError("Tool arguments are required")
                
                tool_name = step_data["tool"]
                
                # Validate tool exists
                if not validate_tool(tool_name):
                    raise PlannerError(
                        f"Unknown tool '{tool_name}' in step {step_data['step']}. "
                        f"Plan must be escalated to human."
                    )
                
                # Create PlanStep with destructive flag
                plan_step = PlanStep(
                    step=step_data["step"],
                    tool=tool_name,
                    args=step_data["args"],
                    destructive=is_destructive(tool_name)
                )
                
                validated_steps.append(plan_step)
                
            except ValidationError as e:
                raise PlannerError(f"Invalid step format: {e}")
        
        return validated_steps
    
    def create_plan(self, ticket: TicketWebhook) -> Plan:
        """
        Create an action plan for a ticket
        
        Args:
            ticket: The support ticket
            
        Returns:
            A validated Plan object
            
        Raises:
            PlannerError: If plan creation or validation fails
        """
        try:
            # Format the prompt
            prompt = self._format_prompt(ticket)
            
            # Get LLM response
            response = self.llm.generate(prompt)
            
            # Parse response
            steps_data = self._parse_llm_response(response)
            
            # Validate steps
            validated_steps = self._validate_plan_steps(steps_data)
            
            # Create Plan object
            plan = Plan(
                ticket_id=ticket.ticket_id,
                steps=validated_steps
            )
            
            return plan
            
        except PlannerError:
            raise
        except Exception as e:
            raise PlannerError(f"Unexpected error during planning: {e}")
    
    def requires_approval(self, plan: Plan) -> bool:
        """Check if the plan contains any destructive steps requiring approval"""
        return any(step.destructive for step in plan.steps)
