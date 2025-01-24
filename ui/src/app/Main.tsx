import { ResearchCanvas } from "@/components/ResearchCanvas";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import { AgentState } from "@/lib/types";
import { useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotChatSuggestions } from "@copilotkit/react-ui";
import Feedback from "@/components/Feedback";

export default function Main() {
  const { model, agent } = useModelSelectorContext();
  const { state, setState } = useCoAgent<AgentState>({
    name: agent,
    initialState: {
      model,
      technical_issue: "",
      resources: [],
      report: "",
      logs: [],
    },
  });

  useCopilotChatSuggestions({
    instructions: "Please assist me with this issue.",
  });

  const handleMessage = async (message: string) => {
    // Clear the logs before starting the new action
    setState({ ...state, logs: [] });
    await new Promise((resolve) => setTimeout(resolve, 30));
  };

  return (
    <>
      <h1 className="flex h-[60px] bg-[#0E103D] text-white items-center px-10 text-2xl font-medium">
        MS2750 Service Support
      </h1>

      <div
        className="flex flex-1 border"
        style={{ height: "calc(100vh - 60px)" }}
      >
        <div className="flex-1 overflow-hidden">
          <ResearchCanvas />
        </div>
        <div
          className="w-[500px] h-full flex-shrink-0 relative"
          style={
            {
              "--copilot-kit-background-color": "#E0E9FD",
              "--copilot-kit-secondary-color": "#6766FC",
              "--copilot-kit-secondary-contrast-color": "#FFFFFF",
              "--copilot-kit-primary-color": "#FFFFFF",
              "--copilot-kit-contrast-color": "#000000",
            } as any
          }
        >
          <div className="absolute top-2 right-2 z-10">
            <Feedback onSubmitFeedback={handleMessage} />
          </div>
          <CopilotChat
            className="h-full"
            onSubmitMessage={handleMessage}
            labels={{
              initial: "Hi! How can I assist you today?",
            }}
          />
        </div>
      </div>
    </>
  );
}
