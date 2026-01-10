"""
Example usage of the multi-agent problem solver.
Demonstrates how to use the system programmatically.
"""

import json
from app.domain.pipeline import solve_problem, get_pipeline_stats
from app.core.logger import setup_logger


logger = setup_logger(__name__)


def demo_basic_problem():
    """Demonstrate solving a basic math problem."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Arithmetic")
    print("="*60)
    
    problem = "What is 15 + 27?"
    
    logger.info(f"Solving: {problem}")
    
    result = solve_problem(problem)
    
    print(f"\n📝 Problem: {problem}")
    print(f"✅ Answer: {result['final_answer']}")
    print(f"📊 Confidence: {result['confidence']:.2%}")
    print(f"🔍 Human Review Needed: {result['requires_human_review']}")
    
    print(f"\n📖 Explanation:")
    print(result['explanation'])
    
    print(f"\n🤖 Agent Trace:")
    for trace in result['agent_trace']:
        status = "✓" if trace['success'] else "✗"
        print(f"  {status} {trace['agent']}: {trace['time_ms']:.1f}ms")


def demo_algebra_problem():
    """Demonstrate solving an algebra problem."""
    print("\n" + "="*60)
    print("DEMO 2: Algebra")
    print("="*60)
    
    problem = "Solve for x: 3x + 7 = 22"
    
    logger.info(f"Solving: {problem}")
    
    result = solve_problem(problem)
    
    print(f"\n📝 Problem: {problem}")
    print(f"✅ Answer: {result['final_answer']}")
    print(f"📊 Confidence: {result['confidence']:.2%}")
    
    print(f"\n📖 Step-by-Step:")
    for trace in result['agent_trace']:
        if trace['agent'] == 'explainer':
            print(trace['output'][:200] + "...")


def demo_guardrail_check():
    """Demonstrate guardrail functionality."""
    print("\n" + "="*60)
    print("DEMO 3: Guardrail Check")
    print("="*60)
    
    # This should pass
    safe_problem = "Calculate the area of a circle with radius 5"
    print(f"\n✅ Safe problem: {safe_problem}")
    
    try:
        result = solve_problem(safe_problem, enable_guardrails=True)
        print(f"   Result: {result['final_answer']}")
    except Exception as e:
        print(f"   Error: {str(e)}")


def show_statistics():
    """Show pipeline execution statistics."""
    print("\n" + "="*60)
    print("PIPELINE STATISTICS")
    print("="*60)
    
    stats = get_pipeline_stats()
    
    print(f"\n📊 Total Executions: {stats['total_executions']}")
    print(f"\n🤖 Agent Statistics:")
    
    for agent_name, agent_stats in stats['agents'].items():
        print(f"  • {agent_name}: {agent_stats['execution_count']} runs")


def main():
    """Run all demos."""
    print("\n" + "🚀 " * 20)
    print("MULTI-AGENT MATH SOLVER - DEMONSTRATION")
    print("🚀 " * 20)
    
    try:
        # Run demos
        demo_basic_problem()
        demo_algebra_problem()
        demo_guardrail_check()
        
        # Show statistics
        show_statistics()
        
        print("\n" + "✅ " * 20)
        print("DEMONSTRATION COMPLETE")
        print("✅ " * 20 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Demo failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
