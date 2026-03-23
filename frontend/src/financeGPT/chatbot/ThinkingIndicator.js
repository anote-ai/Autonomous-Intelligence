import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faBrain,
  faCheckCircle,
  faCog,
  faInfoCircle,
  faLightbulb,
  faSearch,
  faSitemap,
} from "@fortawesome/free-solid-svg-icons";

function getStepIcon(type) {
  switch (type) {
    case "llm_reasoning":
      return <FontAwesomeIcon icon={faBrain} className="text-accent" />;
    case "tool_start":
    case "tools_start":
    case "tool_end":
      return <FontAwesomeIcon icon={faSearch} className="text-accent" />;
    case "agent_thinking":
      return <FontAwesomeIcon icon={faCog} className="text-accent" />;
    case "complete":
    case "step-complete":
      return <FontAwesomeIcon icon={faCheckCircle} className="text-accent" />;
    case "agent_start":
      return <FontAwesomeIcon icon={faCog} className="text-accent" />;
    case "agent_progress":
      return <FontAwesomeIcon icon={faArrowRight} className="text-accent" />;
    case "agent_reasoning":
      return <FontAwesomeIcon icon={faBrain} className="text-accent" />;
    case "agent_tool_use":
    case "agent_tool_complete":
      return <FontAwesomeIcon icon={faSearch} className="text-accent" />;
    case "agent_completion":
    case "agent_error":
      return <FontAwesomeIcon icon={faInfoCircle} className="text-accent" />;
    case "orchestrator_decision":
    case "orchestrator_synthesis":
      return <FontAwesomeIcon icon={faSitemap} className="text-accent" />;
    case "reasoning_step":
      return <FontAwesomeIcon icon={faLightbulb} className="text-accent" />;
    default:
      return <FontAwesomeIcon icon={faCog} className="text-accent" />;
  }
}

function getStepColor(type) {
  switch (type) {
    case "llm_reasoning":
    case "tool_start":
    case "tools_start":
    case "tool_end":
    case "agent_thinking":
    case "complete":
    case "step-complete":
    case "agent_start":
    case "agent_progress":
    case "agent_reasoning":
    case "agent_tool_use":
    case "agent_tool_complete":
    case "agent_completion":
    case "orchestrator_decision":
    case "orchestrator_synthesis":
    case "reasoning_step":
      return "border-l-accent bg-accent/10";
    case "agent_error":
      return "border-l-red-400 bg-red-950/20";
    default:
      return "border-l-gray-400 bg-gray-800/20";
  }
}

function ThinkingIndicator({ step }) {
  if (!step) return null;

  return (
    <div
      className={`border-l-2 ${getStepColor(step.type)} pl-3 py-2 mb-2 text-sm`}
    >
      <div className="flex items-center gap-2 mb-1">
        {getStepIcon(step.type)}
        <span className="text-gray-300 font-medium">
          {step.message || "Processing..."}
        </span>
      </div>

      {step.thought && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Thought:</strong> {step.thought}
        </div>
      )}

      {step.agent_thought && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Planning:</strong> {step.agent_thought}
        </div>
      )}

      {step.tool_name && (
        <div className="text-gray-500 text-xs">
          <strong>Tool:</strong> {step.tool_name}
        </div>
      )}

      {step.tool_output && (
        <div className="text-gray-500 text-xs mt-1">
          <strong>Result:</strong>{" "}
          {step.tool_output.length > 100
            ? `${step.tool_output.substring(0, 100)}...`
            : step.tool_output}
        </div>
      )}

      {step.agent_name && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Agent:</strong> {step.agent_name}
        </div>
      )}

      {step.reasoning && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Reasoning:</strong>{" "}
          {step.reasoning.length > 150
            ? `${step.reasoning.substring(0, 150)}...`
            : step.reasoning}
        </div>
      )}

      {step.current_agent && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Current Agent:</strong> {step.current_agent}
        </div>
      )}

      {step.completed_agents && step.completed_agents.length > 0 && (
        <div className="text-gray-500 text-xs">
          <strong>Completed:</strong> {step.completed_agents.join(", ")}
        </div>
      )}

      {step.final_thought && (
        <div className="text-gray-400 text-xs mb-1">
          <strong>Final Thought:</strong> {step.final_thought}
        </div>
      )}

      {step.planned_action && (
        <div className="text-gray-500 text-xs">
          <strong>Planned Action:</strong> {step.planned_action}
        </div>
      )}

      {step.confidence && (
        <div className="text-gray-500 text-xs">
          <strong>Confidence:</strong> {Math.round(step.confidence * 100)}%
        </div>
      )}

      {step.error && (
        <div className="text-red-400 text-xs mt-1">
          <strong>Error:</strong> {step.error}
        </div>
      )}
    </div>
  );
}

export default ThinkingIndicator;
