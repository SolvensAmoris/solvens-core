import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { context, file } = await request.json();

    // Simulate AI completion (in production, call actual LLM)
    const completion = generateCompletion(context, file);
    
    return NextResponse.json({
      completion,
      line: 5,
      confidence: 0.92,
      type: "completion",
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to generate completion" },
      { status: 500 }
    );
  }
}

function generateCompletion(context: string, file: string): string {
  // Simulate smart completions based on context
  const lowerContext = context.toLowerCase();
  
  if (lowerContext.includes("add") && lowerContext.includes("task")) {
    return `task new_task {
  agent: coder
  depends_on: [previous_task]
}`;
  }
  
  if (lowerContext.includes("error") || lowerContext.includes("handle")) {
    return `task error_handler {
  agent: architect
  system: "Handle errors gracefully and report to monitoring"
}`;
  }
  
  if (lowerContext.includes("test")) {
    return `task write_tests {
  agent: coder
  depends_on: [implement_backend]
  retry: 2
}`;
  }
  
  // Default: suggest a task completion
  return `

task deploy_to_prod {
  agent: architect
  depends_on: [write_tests, implement_frontend]
  timeout: 300
}`;
}
