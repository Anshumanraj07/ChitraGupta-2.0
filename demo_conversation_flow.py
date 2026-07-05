"""
Demo script showing the conversation-to-action flow in ChitraGupta 2.0
This demonstrates how user input flows through the system to generate tiny, actionable tasks.
Uses the new user-scoped architecture via the chat endpoint.
"""

import sys
import os
import asyncio
from datetime import datetime
from unittest.mock import MagicMock

# Add the current directory to the path so we can import core as a package
sys.path.insert(0, os.path.dirname(__file__))

from core.user_registry import get_user_bundle, DEFAULT_USER_ID
from core.conversation_manager import conversation_manager, ConversationState
from core.goal_discovery import goal_discovery
from core.task_generator import task_generator
from core.memory_manager import memory_manager
from core.session_manager import session_manager
from core.endpoints.chat import ChatRequest, _resolve_user_id, _get_session_data, build_policy_context
from core.policy_engine import policy_engine
from core.schemas.policy import PolicyAction

async def demo_conversation_flow():
    """Demonstrate the full conversation-to-action flow using the new architecture."""
    
    print("=" * 60)
    print("ChitraGupta 2.0 - Conversation-to-Action Flow Demo (New Architecture)")
    print("=" * 60)
    
    user_id = DEFAULT_USER_ID
    bundle = get_user_bundle(user_id)
    
    # Create a mock request object for the chat endpoint
    mock_request = MagicMock()
    mock_request.headers = {"x-user-id": user_id}
    
    async def call_chat(message: str, session_id: str = None):
        """Call the chat logic directly."""
        chat_req = ChatRequest(user_id=user_id, message=message, session_id=session_id)
        resolved_user_id = _resolve_user_id(chat_req.user_id, None, mock_request)
        session_data = await _get_session_data(resolved_user_id, chat_req.session_id)
        
        # Build policy context
        policy_context = build_policy_context(resolved_user_id, session_data)
        
        # Get memory
        from core.endpoints.chat import _build_memory_query
        identity_summary = bundle.identity_model.get_profile_summary()
        behavior_summary = bundle.behavioral_inference.get_profile_summary()
        coaching_summary = bundle.coaching_planner.get_plan_summary()
        memory_query = _build_memory_query(resolved_user_id, message, identity_summary, behavior_summary, coaching_summary, session_data)
        memory_result = bundle.adaptive_memory.retrieve(memory_query)
        memory_context = bundle.adaptive_memory.get_context_for_prompt(memory_query)
        policy_context.has_relevant_memory = len(memory_result.entries) > 0
        policy_context.memory_summary = memory_context
        
        # Get policy decision
        policy_decision = policy_engine.decide(policy_context)
        
        # Get LLM response
        from core.endpoints.chat import _generate_llm_response
        llm_response = await _generate_llm_response(
            user_id=resolved_user_id,
            user_message=message,
            policy_decision=policy_decision,
            memory_context=memory_context,
            identity_context=bundle.identity_model.get_context_for_prompt(),
            behavioral_context=bundle.behavioral_inference.get_context_for_prompt(),
            coaching_context=bundle.coaching_planner.get_context_for_prompt(),
            policy_context=policy_context,
        )
        
        # Generate tasks if policy says so
        tasks = []
        if policy_decision.action == PolicyAction.GENERATE_TASK:
            from core.endpoints.chat import _build_task_request
            task_request = _build_task_request(
                resolved_user_id, identity_summary, behavior_summary, coaching_summary, bundle, session_data
            )
            task_result = bundle.task_quality_engine.generate_tasks(task_request)
            from core.endpoints.chat import _serialize_task
            tasks = [_serialize_task(t) for t in task_result.tasks]
            session_data["active_tasks"].extend(tasks)
        
        # Build response dict compatible with old demo expectations
        return {
            "response": llm_response,
            "classification": policy_decision.action.value,
            "use_micro": policy_decision.action.value in ["ask_question", "reflect", "explore_goal"],
            "conversation_state": session_data.get("conversation_state", "onboarding"),
            "discovered_goal": session_data.get("current_goal", ""),
            "discovered_struggle": session_data.get("current_struggle", ""),
            "should_generate_task": policy_decision.action == PolicyAction.GENERATE_TASK,
            "generated_task_title": tasks[0]["title"] if tasks else "",
            "generated_task_sub_tasks": tasks[0]["micro_steps"] if tasks else [],
            "generated_task_execution_tips": [],
            "generated_task_priority": tasks[0].get("priority", "medium") if tasks else "",
            "generated_task_estimated_time": tasks[0].get("estimated_duration_minutes", 0) if tasks else 0,
            "discovered_habit": session_data.get("current_habit", ""),
            "discovered_routine": session_data.get("current_routine", ""),
            "generated_task_discipline": tasks[0].get("discipline", "mental") if tasks else "",
            "task_generation_confidence": policy_decision.confidence,
        }
    
    # Example 1: Initial greeting
    print("\n1. User: 'Hey'")
    print("-" * 40)
    result1 = await call_chat("Hey")
    print(f"Response: {result1.get('response', 'No response')}")
    print(f"Classification: {result1.get('classification', 'N/A')}")
    print(f"Use Micro: {result1.get('use_micro', False)}")
    
    # Example 2: User expresses a goal
    print("\n2. User: 'I want to get fit but I struggle with consistency'")
    print("-" * 40)
    result2 = await call_chat("I want to get fit but I struggle with consistency")
    print(f"Response: {result2.get('response', 'No response')}")
    print(f"Classification: {result2.get('classification', 'N/A')}")
    print(f"Conversation State: {result2.get('conversation_state', 'N/A')}")
    print(f"Discovered Goal: {result2.get('discovered_goal', 'N/A')}")
    print(f"Discovered Struggle: {result2.get('discovered_struggle', 'N/A')}")
    print(f"Should Generate Task: {result2.get('should_generate_task', False)}")
    
    if result2.get('should_generate_task'):
        print(f"Generated Task: {result2.get('generated_task_title', 'N/A')}")
        print(f"Sub-tasks: {result2.get('generated_task_sub_tasks', [])}")
        print(f"Execution Tips: {result2.get('generated_task_execution_tips', [])}")
        print(f"Priority: {result2.get('generated_task_priority', 'N/A')}")
        print(f"Estimated Time: {result2.get('generated_task_estimated_time', 0)} minutes")
    
    # Example 3: User confirms understanding
    print("\n3. User: 'Yes, that's right. I keep starting but stopping after a week.'")
    print("-" * 40)
    result3 = await call_chat("Yes, that's right. I keep starting but stopping after a week.")
    print(f"Response: {result3.get('response', 'No response')}")
    print(f"Conversation State: {result3.get('conversation_state', 'N/A')}")
    print(f"Discovered Habit: {result3.get('discovered_habit', 'N/A')}")
    print(f"Discovered Routine: {result3.get('discovered_routine', 'N/A')}")
    print(f"Should Generate Task: {result3.get('should_generate_task', False)}")
    
    if result3.get('should_generate_task'):
        print(f"Generated Task: {result3.get('generated_task_title', 'N/A')}")
        print(f"Sub-tasks: {result3.get('generated_task_sub_tasks', [])}")
        print(f"Execution Tips: {result3.get('generated_task_execution_tips', [])}")
        print(f"Priority: {result3.get('generated_task_priority', 'N/A')}")
        print(f"Estimated Time: {result3.get('generated_task_estimated_time', 0)} minutes")
    
    # Example 4: User ready for action
    print("\n4. User: 'Sure, give me something small to start with.'")
    print("-" * 40)
    result4 = await call_chat("Sure, give me something small to start with.")
    print(f"Response: {result4.get('response', 'No response')}")
    print(f"Conversation State: {result4.get('conversation_state', 'N/A')}")
    print(f"Should Generate Task: {result4.get('should_generate_task', False)}")
    
    if result4.get('should_generate_task'):
        print(f"Generated Task: {result4.get('generated_task_title', 'N/A')}")
        print(f"Sub-tasks: {result4.get('generated_task_sub_tasks', [])}")
        print(f"Execution Tips: {result4.get('generated_task_execution_tips', [])}")
        print(f"Priority: {result4.get('generated_task_priority', 'N/A')}")
        print(f"Discipline: {result4.get('generated_task_discipline', 'N/A')}")
        print(f"Estimated Time: {result4.get('generated_task_estimated_time', 0)} minutes")
        print(f"Task Confidence: {result4.get('task_generation_confidence', 0.0):.2f}")
    
    # Show session info
    print("\n" + "=" * 60)
    print("Session Information")
    print("=" * 60)
    session_info = session_manager.get_session_info()
    for key, value in session_info.items():
        print(f"{key}: {value}")
    
    # Show conversation manager state
    print("\nConversation Manager State:")
    print(f"State: {conversation_manager.state.value}")
    print(f"Conversation Count: {conversation_manager.context.conversation_count}")
    print(f"Goal: {conversation_manager.context.goal}")
    print(f"Struggle: {conversation_manager.context.struggle}")
    print(f"Habit: {conversation_manager.context.habit}")
    print(f"Routine: {conversation_manager.context.routine}")
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo_conversation_flow())
