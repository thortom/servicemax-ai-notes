import React from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { AgentState } from "@/lib/types";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import { randomId } from "@copilotkit/shared";

type FeedbackProps = {
  onSubmitFeedback: (message: string) => Promise<void>;
};

function Feedback({ onSubmitFeedback }: FeedbackProps) {
//   const { agent } = useModelSelectorContext();
//   const { state, setState } = useCoAgent<AgentState>({
//     name: agent,
//     initialState: {
//       model: "",
//       research_question: "",
//       report: "",
//       resources: [],
//       logs: []
//     }
//   });
// }

  // Create a ref to track whether we're waiting for IDs
//   const waitingForIds = React.useRef(true);

  // Listen for state updates that might contain the LangSmith IDs
//   useCoAgentStateRender({
//     name: agent,
//     render: ({ state: agentState, nodeName, status }) => {
//       console.log("CoAgentStateRender update:", { agentState, nodeName, status });

//       // Assuming agentState might contain the LangSmith IDs
//       if (waitingForIds.current && agentState?.metadata?.run_id) {
//         console.log("Received LangSmith IDs:", agentState.metadata);
//         waitingForIds.current = false;
        
//         setState((prevState: AgentState | undefined) => {
//           const baseState: AgentState = prevState || {
//             model: "",
//             research_question: "",
//             report: "",
//             resources: [],
//             logs: []
//           };

//           return {
//             ...baseState,
//             metadata: {
//               thread_id: agentState.metadata.thread_id,
//               run_id: agentState.metadata.run_id,
//               checkpoint_ns: Date.now().toString()
//             }
//           };
//         });
//       }
//       return null;
//     },
//   });

  // Only initialize metadata if we haven't received LangSmith IDs after a timeout
//   React.useEffect(() => {
//     const timeoutId = setTimeout(() => {
//       if (waitingForIds.current) {
//         console.log("Timeout reached, initializing with default IDs");
//         const newMetadata: AgentMetadata = {
//           thread_id: randomId(),
//           run_id: randomId(),
//           checkpoint_ns: Date.now().toString()
//         };
        
//         setState((prevState: AgentState | undefined) => {
//           const baseState: AgentState = prevState || {
//             model: "",
//             research_question: "",
//             report: "",
//             resources: [],
//             logs: []
//           };

//           return {
//             ...baseState,
//             metadata: newMetadata
//           };
//         });
//       }
//     }, 5000);

//     return () => clearTimeout(timeoutId);
//   }, [setState]);

  const handleFeedback = async (isPositive: boolean) => {
    try {
    //   // Ensure we have metadata
    //   const currentMetadata = state.metadata || {
    //     thread_id: randomId(),
    //     run_id: randomId(),
    //     checkpoint_ns: Date.now().toString()
    //   };
      
    //   console.log("Submitting feedback with metadata:", currentMetadata);
      
      await onSubmitFeedback(JSON.stringify({
        tool: "SubmitFeedback",
        args: {
          isPositive,
          threadId: "",
          checkpointId: "",
          checkpointNs: ""
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