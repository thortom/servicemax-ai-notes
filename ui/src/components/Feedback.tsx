import React from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { AgentState } from "@/lib/types";
import { useModelSelectorContext } from "@/lib/model-selector-provider";

type FeedbackProps = {
  onSubmitFeedback: (message: string) => Promise<void>;
};

function Feedback({ onSubmitFeedback }: FeedbackProps) {
  const { agent } = useModelSelectorContext();
  const { state } = useCoAgent<AgentState>({
    name: agent,
  });

  useCoAgentStateRender({
    name: agent,
    render: ({ state }) => null
  });
  
  const handleFeedback = async (isPositive: boolean) => {
    try {
      // Get the current URL parameters
      const urlParams = new URLSearchParams(window.location.search);
      const runId = urlParams.get('runId') || '';
      
      await onSubmitFeedback(JSON.stringify({
        tool: "SubmitFeedback",
        args: {
          isPositive,
          runId,
          checkpointNs: "fresh-servicemax"
        }
      }));
      
      alert(isPositive ? "Thank you for the positive feedback!" : "Thank you for the feedback!");
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    }
  };

  return (
    <div className="flex items-center justify-end space-x-2 p-2 bg-white/50 rounded-lg">
      <button
        onClick={() => handleFeedback(true)}
        className="p-2 hover:bg-blue-50 rounded-full transition-colors"
        aria-label="Thumbs up"
      >
        <ThumbsUp className="w-5 h-5 text-blue-600" />
      </button>
      <button
        onClick={() => handleFeedback(false)}
        className="p-2 hover:bg-red-50 rounded-full transition-colors"
        aria-label="Thumbs down"
      >
        <ThumbsDown className="w-5 h-5 text-red-600" />
      </button>
    </div>
  );
}

export default Feedback;