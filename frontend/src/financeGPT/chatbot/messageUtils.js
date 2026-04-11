function normalizeSource(source, index) {
  if (!source) {
    return null;
  }

  if (Array.isArray(source)) {
    const [chunkText, documentName, pageNumber, startIndex, endIndex] = source;
    return {
      id: `source-${index}`,
      chunk_text: chunkText || "",
      document_name: documentName || "Unknown document",
      page_number: Number.isInteger(pageNumber) ? pageNumber : null,
      start_index: typeof startIndex === "number" ? startIndex : null,
      end_index: typeof endIndex === "number" ? endIndex : null,
      source_type: "document_chunk",
    };
  }

  if (typeof source === "object") {
    return {
      id: source.id || `source-${index}`,
      chunk_text: source.chunk_text || source.chunkText || "",
      document_name:
        source.document_name || source.documentName || "Unknown document",
      page_number:
        Number.isInteger(source.page_number) || Number.isInteger(source.pageNumber)
          ? source.page_number ?? source.pageNumber
          : null,
      start_index:
        typeof source.start_index === "number"
          ? source.start_index
          : typeof source.startIndex === "number"
          ? source.startIndex
          : null,
      end_index:
        typeof source.end_index === "number"
          ? source.end_index
          : typeof source.endIndex === "number"
          ? source.endIndex
          : null,
      source_type: source.source_type || source.sourceType || "document_chunk",
    };
  }

  return null;
}

export function normalizeSources(sources) {
  return (sources || [])
    .map((source, index) => normalizeSource(source, index))
    .filter(Boolean);
}

export function parseRelevantChunks(relevantChunks) {
  if (!relevantChunks || typeof relevantChunks !== "string") {
    return [];
  }

  return relevantChunks
    .split("\n\n")
    .map((entry, index) => {
      const normalized = entry.trim();
      if (!normalized.startsWith("Document: ")) {
        return null;
      }

      const content = normalized.slice("Document: ".length);
      const separatorIndex = content.indexOf(": ");
      if (separatorIndex === -1) {
        return null;
      }

      return {
        id: `stored-source-${index}`,
        document_name: content.slice(0, separatorIndex).trim() || "Unknown document",
        chunk_text: content.slice(separatorIndex + 2).trim(),
        page_number: null,
        start_index: null,
        end_index: null,
        source_type: "stored_relevant_chunk",
      };
    })
    .filter(Boolean);
}

export function formatChatMessages(rawMessages, chatId) {
  return rawMessages.map((message) => ({
    id: message.id,
    chat_id: chatId,
    content: message.message_text,
    role: message.sent_from_user === 1 ? "user" : "assistant",
    relevant_chunks: message.relevant_chunks,
    reasoning: message.reasoning || [],
    sources:
      normalizeSources(message.sources).length > 0
        ? normalizeSources(message.sources)
        : parseRelevantChunks(message.relevant_chunks),
    charts: message.charts || [],
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
    case "tool_registered": {
      const registeredStep = {
        id: `step-${Date.now()}`,
        type: "tool_registered",
        tool_name: eventData.tool_name || "",
        description: eventData.description || "",
        message: `New tool created: ${eventData.tool_name}`,
        timestamp: Date.now(),
      };
      updatedMessage.reasoning = [
        ...(updatedMessage.reasoning || []),
        registeredStep,
      ];
      updatedMessage.currentStep = registeredStep;
      break;
    }
    case "chart_generated": {
      const chart = {
        image_data: eventData.image_data || "",
        title: eventData.title || "Chart",
      };
      updatedMessage.charts = [...(updatedMessage.charts || []), chart];
      break;
    }
    case "complete": {
      updatedMessage.content = eventData.answer || updatedMessage.content || "";
      updatedMessage.sources = normalizeSources(eventData.sources);
      updatedMessage.charts = [
        ...(updatedMessage.charts || []),
        ...(eventData.charts || []),
      ];
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
      updatedMessage.sources = normalizeSources(eventData.sources);
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
