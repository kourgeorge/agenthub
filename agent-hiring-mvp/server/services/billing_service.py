"""
Billing service for managing user budgets and cost tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal


class BillingService:
    """Handles billing, budgets, and cost tracking"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def check_budget_limit(self, user_id: int, estimated_cost: float) -> Dict[str, Any]:
        """Check if user has sufficient budget for operation"""
        budget = await self._get_user_budget(user_id)
        
        if not budget:
            # Create default budget for new user
            budget = await self._create_default_budget(user_id)
        
        # Check monthly budget
        if budget['current_usage'] + estimated_cost > budget['monthly_budget']:
            return {
                'allowed': False,
                'reason': 'Monthly budget exceeded',
                'current_usage': budget['current_usage'],
                'monthly_budget': budget['monthly_budget'],
                'estimated_cost': estimated_cost
            }
        
        # Check per-request limit
        if estimated_cost > budget['max_per_request']:
            return {
                'allowed': False,
                'reason': 'Per-request cost limit exceeded',
                'max_per_request': budget['max_per_request'],
                'estimated_cost': estimated_cost
            }
        
        return {
            'allowed': True,
            'current_usage': budget['current_usage'],
            'monthly_budget': budget['monthly_budget'],
            'remaining_budget': budget['monthly_budget'] - budget['current_usage']
        }
    
    async def record_cost(self, user_id: int, execution_id: int, cost: float) -> None:
        """Record cost for an execution"""
        # Update user budget
        await self._update_user_usage(user_id, cost)
        
        # Record execution cost
        await self._record_execution_cost(execution_id, cost)
        
        print(f"Recorded cost: ${cost:.6f} for user {user_id}, execution {execution_id}")
    
    async def get_user_billing_summary(self, user_id: int) -> Dict[str, Any]:
        """Get billing summary for user"""
        budget = await self._get_user_budget(user_id)
        
        if not budget:
            return {
                'user_id': user_id,
                'has_budget': False,
                'message': 'No budget configured'
            }
        
        # Get recent executions
        recent_executions = await self._get_recent_executions(user_id, days=30)
        
        total_cost = sum(execution.get('total_cost', 0) for execution in recent_executions)
        
        return {
            'user_id': user_id,
            'has_budget': True,
            'monthly_budget': budget['monthly_budget'],
            'current_usage': budget['current_usage'],
            'remaining_budget': budget['monthly_budget'] - budget['current_usage'],
            'budget_utilization': (budget['current_usage'] / budget['monthly_budget']) * 100,
            'max_per_request': budget['max_per_request'],
            'reset_date': budget['reset_date'],
            'recent_executions': len(recent_executions),
            'total_cost_30_days': total_cost
        }
    
    async def update_user_budget(self, 
                               user_id: int, 
                               monthly_budget: Optional[float] = None,
                               max_per_request: Optional[float] = None) -> Dict[str, Any]:
        """Update user budget settings"""
        budget = await self._get_user_budget(user_id)
        
        if not budget:
            budget = await self._create_default_budget(user_id)
        
        updates = {}
        
        if monthly_budget is not None:
            budget['monthly_budget'] = monthly_budget
            updates['monthly_budget'] = monthly_budget
        
        if max_per_request is not None:
            budget['max_per_request'] = max_per_request
            updates['max_per_request'] = max_per_request
        
        # In production, implement proper database update
        print(f"Updated budget for user {user_id}: {updates}")
        
        return await self.get_user_billing_summary(user_id)
    
    async def reset_monthly_usage(self, user_id: int) -> None:
        """Reset monthly usage for user"""
        budget = await self._get_user_budget(user_id)
        
        if budget:
            budget['current_usage'] = 0.0
            budget['reset_date'] = datetime.now() + timedelta(days=30)
            
            # In production, implement proper database update
            print(f"Reset monthly usage for user {user_id}")
    
    async def _get_user_budget(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user budget from database"""
        # In production, implement proper database query
        # For now, return a mock budget
        return {
            'user_id': user_id,
            'monthly_budget': 100.0,
            'current_usage': 25.50,
            'max_per_request': 10.0,
            'reset_date': datetime.now() + timedelta(days=15)
        }
    
    async def _create_default_budget(self, user_id: int) -> Dict[str, Any]:
        """Create default budget for new user"""
        budget = {
            'user_id': user_id,
            'monthly_budget': 100.0,
            'current_usage': 0.0,
            'max_per_request': 10.0,
            'reset_date': datetime.now() + timedelta(days=30)
        }
        
        # In production, implement proper database insertion
        print(f"Created default budget for user {user_id}")
        
        return budget
    
    async def _update_user_usage(self, user_id: int, cost: float) -> None:
        """Update user's current usage"""
        # In production, implement proper database update
        print(f"Updated usage for user {user_id}: +${cost:.6f}")
    
    async def _record_execution_cost(self, execution_id: int, cost: float) -> None:
        """Record cost for specific execution"""
        # In production, implement proper database update
        print(f"Recorded execution cost: {execution_id} = ${cost:.6f}")
    
    async def _get_recent_executions(self, user_id: int, days: int = 30) -> list:
        """Get recent executions for user"""
        # In production, implement proper database query
        # For now, return mock data
        return [
            {
                'execution_id': 1,
                'total_cost': 5.25,
                'created_at': datetime.now() - timedelta(days=5)
            },
            {
                'execution_id': 2,
                'total_cost': 3.75,
                'created_at': datetime.now() - timedelta(days=10)
            }
        ] 