import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
  langGraphPlatformEndpoint, copilotKitEndpoint,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import { NextRequest } from "next/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const llmAdapter = new OpenAIAdapter({ openai } as any);
const langsmithApiKey = process.env.LANGSMITH_API_KEY as string

async function submitFeedbackToLangSmith(feedback: any) {
  const { isPositive, threadId, runId, checkpointNs } = feedback.args;
  const score = isPositive ? 1 : 0;
  
  try {
    const response = await fetch('https://api.smith.langchain.com/runs/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${langsmithApiKey}`
      },
      body: JSON.stringify({
        run_id: runId,
        key: 'user_feedback',
        score: score,
        value: isPositive ? 'thumbs_up' : 'thumbs_down',
        comment: `User gave ${isPositive ? 'positive' : 'negative'} feedback`,
        feedback_source: 'end_user'
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to submit feedback: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error submitting feedback to LangSmith:', error);
    throw error;
  }
}

export const POST = async (req: NextRequest) => {
  const searchParams = req.nextUrl.searchParams
  const deploymentUrl = searchParams.get('lgcDeploymentUrl') || process.env.LGC_DEPLOYMENT_URL;

  // Handle feedback submission
  const body = await req.json();
  if (body.tool === 'SubmitFeedback') {
    try {
      const result = await submitFeedbackToLangSmith(body);
      return new Response(JSON.stringify({ success: true, result }), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      return new Response(JSON.stringify({ success: false, error: errorMessage }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  const remoteEndpoint = deploymentUrl ? langGraphPlatformEndpoint({
    deploymentUrl,
    langsmithApiKey,
    agents: [
      {
        name: "research_agent",
        description: "Research agent",
      },
      {
        name: "research_agent_google_genai",
        description: "Research agent",
        assistantId: "9dc0ca3b-1aa6-547d-93f0-e21597d2011c",
      },
    ],
  }) : copilotKitEndpoint({
    url: process.env.REMOTE_ACTION_URL || "http://localhost:8000/copilotkit",
  })

  const runtime = new CopilotRuntime({
    remoteEndpoints: [remoteEndpoint],
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: llmAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
