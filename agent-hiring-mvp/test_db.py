#!/usr/bin/env python3
"""Test database connection and models."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.database import get_session
from server.models.agent import Agent
from server.models.user import User
from server.models.hiring import Hiring, HiringStatus
from server.services.hiring_service import HiringService, HiringCreateRequest

def test_database():
    """Test database connection and basic operations."""
    print("Testing database connection...")
    
    try:
        # Get database session
        db = get_session()
        print("✅ Database session created successfully")
        
        # Test querying agents
        agents = db.query(Agent).all()
        print(f"✅ Found {len(agents)} agents in database")
        
        # Test querying users
        users = db.query(User).all()
        print(f"✅ Found {len(users)} users in database")
        
        # Test querying hirings
        hirings = db.query(Hiring).all()
        print(f"✅ Found {len(hirings)} hirings in database")
        
        # Test creating a hiring
        if users and agents:
            hiring_service = HiringService(db)
            hiring_data = HiringCreateRequest(
                agent_id=agents[0].id,
                user_id=users[0].id,
                requirements={"task_type": "test"},
                budget=10.0,
                duration_hours=1
            )
            
            try:
                hiring = hiring_service.create_hiring(hiring_data)
                print(f"✅ Created hiring with ID: {hiring.id}")
                
                # Clean up
                db.delete(hiring)
                db.commit()
                print("✅ Cleaned up test hiring")
                
            except Exception as e:
                print(f"❌ Failed to create hiring: {e}")
                import traceback
                traceback.print_exc()
        
        db.close()
        print("✅ Database test completed successfully")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database() 