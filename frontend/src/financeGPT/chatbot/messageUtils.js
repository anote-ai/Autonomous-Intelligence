export function formatChatMessages(rawMessages, chatId) {
  return rawMessages.map((message) => ({
    id: message.id,
    chat_id: chatId,
    content: message.message_text,
    role: message.sent_from_user === 1 ? "user" : "assistant",
    relevant_chunks: message.relevant_chunks,
    reasoning: message.reasoning || [],
    sources: message.sources || [],
    timestamp: new Date(message.created).getTime(),
  }));
}

export function createUploadedDocumentMessages(docInfo, chatId) {
  if (!docInfo || docInfo.length === 0) {
    return [];
  }

  return docInfo.map((doc, index) => ({
    id: `file-system-${doc.id}`,
    chat_id: chatId,
    role: "system",
    content: doc.documents
      ? doc.documents
      : `📎 Uploaded 1 file(s): ${doc.document_name}`,
    isFileUpload: true,
    uploadedFiles: [
      {
        name: doc.document_name,
        size: 0,
        uploadTime: doc.created || new Date().toISOString(),
        id: doc.id,
      },
    ],
    timestamp: doc.created
      ? new Date(doc.created).getTime() + index
      : Date.now() + index,
  }));
}

export function sortMessagesByTimestamp(messages) {
  return [...messages].sort((a, b) => {
    const aTime = a.timestamp || 0;
    const bTime = b.timestamp || 0;
    return aTime - bTime;
  });
}

export function updateMessageWithStreamData(message, eventData) {
  const updatedMessage = { ...message };

  switch (eventData.type) {
    case "tool_start":
    case "tools_start": {
      const toolStartStep = {
        id: `step-${Date.now()}`,
        type: eventData.type,
        tool_name: eventData.tool_name,
        message: `Using ${eventData.tool_name}...`,
        timestamp: Date.now(),
      };
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        toolStartStep,
      ];
      updatedMessage.currentStep = toolStartStep;
      break;
    }
    case "tool_end": {
      const reasoningWithOutput = [...(updatedMessage.reasoning || [])];
      const lastToolIndex = reasoningWithOutput.findLastIndex(
        (step) => step.type === "tool_start" || step.type === "tools_start"
      );
      if (lastToolIndex !== -1) {
        reasoningWithOutput[lastToolIndex] = {
          ...reasoningWithOutput[lastToolIndex],
          tool_output: eventData.output,
          message: "Tool execution completed",
        };
      }
      updatedMessage.reasoning = reasoningWithOutput;
      updatedMessage.currentStep = {
        type: "tool_end",
        message: "Tool execution completed",
      };
      break;
    }
    case "agent_thinking": {
      const thinkingStep = {
        id: `step-${Date.now()}`,
        type: eventData.type,
        agent_thought: eventData.thought,
        planned_action: eventData.action,
        message: "Planning next step...",
        timestamp: Date.now(),
      };
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        thinkingStep,
      ];
      updatedMessage.currentStep = thinkingStep;
      break;
    }
    // Streaming text token — append to content so users see the answer forming
    case "text_token": {
      updatedMessage.content = (updatedMessage.content || "") + (eventData.content || "");
      updatedMessage.isThinking = true; // keep indicator until complete
      break;
    }
    // Extended thinking block from Claude claude-3-7+
    case "thinking": {
      const thinkingContent = eventData.content || "";
      const thinkingStep = {
        id: `step-${Date.now()}`,
        type: "thinking",
        thought: thinkingContent.length > 300
          ? thinkingContent.substring(0, 300) + "…"
          : thinkingContent,
        message: "Thinking deeply…",
        timestamp: Date.now(),
      };
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        thinkingStep,
      ];
      updatedMessage.currentStep = thinkingStep;
      break;
    }
    case "complete": {
      updatedMessage.content = eventData.answer || updatedMessage.content || "";
      updatedMessage.sources = eventData.sources || [];
      updatedMessage.isThinking = false;
      updatedMessage.currentStep = null;
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Response complete",
          timestamp: Date.now(),
        },
      ];
      break;
    }
    case "step-complete": {
      updatedMessage.content = eventData.answer || "";
      updatedMessage.sources = eventData.sources || [];
      updatedMessage.isThinking = false;
      updatedMessage.currentStep = null;
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Query processing completed",
          timestamp: Date.now(),
        },
      ];
      break;
    }
    case "agent_start": {
      const agentStartStep = {
        id: `step-${Date.now()}`,
        type: eventData.type,
        agent_name: eventData.agent_name,
        message: eventData.message || `${eventData.agent_name} started`,
        timestamp: Date.now(),
      };
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        agentStartStep,
      ];
      updatedMessage.currentStep = agentStartStep;
      break;
    }
    case "agent_progress": {
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        {
          id: `step-${Date.now()}`,
          type: eventData.type,
          current_agent: eventData.current_agent,
          completed_agents: eventData.completed_agents,
          message: eventData.message || `${eventData.current_agent} completed`,
          timestamp: Date.now(),
        },
      ];
      break;
    }
    case "agent_reasoning": {
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          reasoning: eventData.reasoning,
          message: `${eventData.agent_name} reasoning`,
          timestamp: Date.now(),
        },
      ];
      break;
    }
    case "agent_tool_use": {
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          tool_name: eventData.tool_name,
          input: eventData.input,
          message:
            eventData.message ||
            `${eventData.agent_name} using ${eventData.tool_name}`,
          timestamp: Date.now(),
        },
      ];
      break;
    }
    case "agent_tool_complete": {
      const reasoningWithOutput = [...(updatedMessage.reasoning || [])];
      const lastAgentToolIndex = reasoningWithOutput.findLastIndex(
        (step) => step.type === "agent_tool_use"
      );
      if (lastAgentToolIndex !== -1) {
        reasoningWithOutput[lastAgentToolIndex] = {
          ...reasoningWithOutput[lastAgentToolIndex],
          tool_output: eventData.output,
          message: eventData.message || "Agent tool execution completed",
        };
      }
      updatedMessage.reasoning = reasoningWithOutput;
      break;
    }
    case "reasoning_step":
      if (eventData.step) {
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          eventData.step,
        ];
      }
      break;
    default:
      break;
  }

  return updatedMessage;
}
