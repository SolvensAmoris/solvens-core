"use client";

import { useCallback, useRef, useEffect } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import { useStudioStore } from "@/lib/store";

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export default function MonacoEditor({ value, onChange }: MonacoEditorProps) {
  const { getSuggestion } = useStudioStore();
  const editorRef = useRef<any>(null);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Register Cosmos language
    monaco.languages.register({ id: "cosmos" });
    
    monaco.languages.setMonarchTokensProvider("cosmos", {
      tokenizer: {
        root: [
          [/\/\/.*$/, "comment"],
          [/\#.*$/, "comment"],
          [/\b(provider|agent|task|dag)\b/, "keyword"],
          [/\b(type|model|system|depends_on|retry|timeout)\b/, "attribute"],
          [/"[^"]*"/, "string"],
          [/'[^']*'/, "string"],
          [/\b\d+\b/, "number"],
          [/[{}[\]()->]/, "delimiter"],
          [/[a-zA-Z_]\w*/, "identifier"],
        ],
      },
    });

    monaco.editor.defineTheme("solvens-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "keyword", foreground: "6366f1", fontStyle: "bold" },
        { token: "attribute", foreground: "22d3ee" },
        { token: "string", foreground: "22c55e" },
        { token: "comment", foreground: "4b5563" },
        { token: "number", foreground: "f59e0b" },
        { token: "identifier", foreground: "e2e8f0" },
      ],
      colors: {
        "editor.background": "#0a0a0f",
        "editor.foreground": "#ffffff",
        "editor.lineHighlightBackground": "#1a1a24",
        "editor.selectionBackground": "#6366f140",
        "editorLineNumber.foreground": "#4b5563",
        "editorLineNumber.activeForeground": "#6366f1",
      },
    });

    monaco.editor.setTheme("solvens-dark");

    // Keyboard shortcut for Copilot
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyK, () => {
      const selection = editor.getSelection();
      const selectedText = editor.getModel()?.getValueInRange(selection);
      getSuggestion(selectedText || editor.getValue());
    });
  };

  const handleChange = useCallback(
    (value: string | undefined) => {
      onChange(value || "");
    },
    [onChange]
  );

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language="cosmos"
        value={value}
        onChange={handleChange}
        onMount={handleEditorMount}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: "'JetBrains Mono', monospace",
          lineNumbers: "on",
          renderLineHighlight: "all",
          scrollBeyondLastLine: false,
          padding: { top: 16 },
          automaticLayout: true,
          tabSize: 2,
          wordWrap: "on",
        }}
      />
    </div>
  );
}
