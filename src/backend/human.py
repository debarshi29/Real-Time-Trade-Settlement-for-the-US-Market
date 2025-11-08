# Import necessary libraries
from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, END

# Define the state of the graph.
# 'messages' will store the conversation history.
# 'next_action' is a flag to indicate if human intervention is needed.
class GraphState(TypedDict):
    """Represents the state of our graph.
    
    Attributes:
        messages: A list of messages in the conversation history.
        human_needed: A boolean flag to indicate if a human review is required.
    """
    messages: List[BaseMessage]
    human_needed: bool = False

# --- Node Functions ---

# Node 1: Simulates an LLM call.
# In a real application, this would be a call to a model like GPT-4, Gemini, etc.
def call_llm(state: GraphState):
    """
    Simulates an LLM's response. It decides whether to proceed directly or
    flag a need for human intervention based on the user's message content.
    """
    messages = state['messages']
    last_message_content = messages[-1].content.lower()
    print(f"LLM Node: Processing user message: '{last_message_content}'")
    
    # Simple logic to trigger human intervention
    if "sensitive topic" in last_message_content or "financial advice" in last_message_content:
        ai_response = "I need human assistance to handle this request. Please wait."
        human_needed = True
    else:
        ai_response = "Hello! I can help with that. This is an automated response."
        human_needed = False

    new_messages = [AIMessage(content=ai_response)]
    print(f"LLM Node: Human needed: {human_needed}")
    
    # Return the updated state
    return {"messages": messages + new_messages, "human_needed": human_needed}

# Node 2: The human intervention node.
# This is where the program would pause and wait for human input in a real UI.
def human_review(state: GraphState):
    """
    This node represents the point where a human takes over.
    It simulates a pause and waits for the human to provide a final response.
    """
    print("\n--- Human Review Needed ---")
    print("The system has flagged this conversation for human intervention.")
    print("Please provide a new response or continue the previous one.")
    
    # In a real application, you would integrate a UI here to capture human input.
    # We will simulate this by getting input from the command line.
    new_response = input("Human's Response: ")

    new_messages = [AIMessage(content=new_response)]
    print("--- Human Review Complete ---\n")
    
    # After human review, the human_needed flag is reset.
    return {"messages": state['messages'] + new_messages, "human_needed": False}

# Node 3: A simple final response node.
def final_response(state: GraphState):
    """
    The final node that concludes the conversation thread.
    """
    print("Final Node: Conversation concluded.")
    return state


# --- Conditional Logic ---

def should_continue(state: GraphState):
    """
    Decides the next step in the graph based on the 'human_needed' flag.
    If 'human_needed' is True, the graph transitions to the 'human_review' node.
    Otherwise, it transitions to the 'final_response' node and ends.
    """
    if state['human_needed']:
        print("Decision: Human review is needed.")
        return "human_review"
    else:
        print("Decision: No human review needed. Proceeding to final response.")
        return "final_response"

# --- Build the Graph ---

# Create the graph instance
workflow = StateGraph(GraphState)

# Add the nodes to the graph
workflow.add_node("llm", call_llm)
workflow.add_node("human_review", human_review)
workflow.add_node("final_response", final_response)

# Set the entry point of the graph
workflow.set_entry_point("llm")

# Add the edges
# The LLM node has a conditional edge based on the `should_continue` function.
workflow.add_edge("human_review", "final_response")
workflow.add_conditional_edges(
    "llm",
    should_continue,
    {"human_review": "human_review", "final_response": "final_response"}
)
workflow.add_edge("final_response", END)

# Compile the graph into a runnable app
app = workflow.compile()

# --- Run the App ---

if __name__ == "__main__":
    print("Starting LangGraph Human-in-the-Loop demonstration.")
    print("Type a message to the AI. Example: 'Tell me about the weather' or 'I need financial advice'.")
    print("Type 'exit' to end the program.")
    
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() == 'exit':
            break

        # Initial state with the user's message
        initial_state = {"messages": [HumanMessage(content=user_input)]}
        
        # Run the graph and print the final output
        final_state = app.invoke(initial_state)

        # Print the final AI response from the graph's output
        print("\nAI:", final_state['messages'][-1].content)
        
