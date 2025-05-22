'use client';

import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidBlockProps {
  code: string;
  // id: string; // Optional: if you need to uniquely identify mermaid blocks from parent
}

const MermaidBlock: React.FC<MermaidBlockProps> = ({ code }) => {
  const mermaidDivRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  // Use a simple key to force re-render of the div when code changes, 
  // ensuring mermaid processes fresh content.
  const [key, setKey] = useState(0);

  useEffect(() => {
    // Initialize Mermaid. This is safe to call multiple times if needed,
    // but ideally, it's called once.
    mermaid.initialize({
      startOnLoad: false, // We will manually trigger rendering
      theme: 'default',
      // securityLevel: 'loose', // Use with caution
    });

    setKey(prev => prev + 1); // Change key to force re-render of the div below
  }, [code]); // Re-initialize and prepare for re-render if code changes

  useEffect(() => {
    if (mermaidDivRef.current && code) {
      setError(null);
      // Ensure the div is empty before adding new code
      // mermaidDivRef.current.innerHTML = code; 
      // No, we want React to render the code into the div, then mermaid to process it.
      
      try {
        // Validate the Mermaid code before attempting to render
        // mermaid.parse(code); // This throws an error if invalid, which is good.
                                // However, mermaid.run also handles errors internally for specific blocks.

        // Tell Mermaid to render all elements with class "mermaid".
        // Since mermaid.initialize({ startOnLoad: false }) is used,
        // mermaid.run() will process elements with class="mermaid" that have not yet been processed.
        // The key={key} on the parent div ensures the .mermaid div is fresh for processing.
        mermaid.run() // MODIFIED_LINE: No longer passing nodes, let mermaid find .mermaid elements
          .catch(e => {
            console.error("Mermaid run error:", e);
            setError(e instanceof Error ? e.message : String(e));
        });

      } catch (e: any) {
        console.error("Mermaid parsing/running error:", e);
        setError(e instanceof Error ? e.message : String(e));
      }
    } else if (!code) {
      setError(null); // Clear error if code is removed
    }
  }, [code, key]); // Rerun when code or key changes

  // The `key` prop on the div ensures that when the code changes, React replaces the div
  // instead of just updating its content. This helps Mermaid reprocess the diagram correctly.
  // The actual Mermaid code is rendered as a child of this div.
  return (
    <div key={key} ref={mermaidDivRef} className="mermaid-diagram-container flex justify-center my-6">
      {error ? (
        <div className="mermaid-error p-4 my-2 bg-red-100 text-red-700 border border-red-400 rounded-md shadow w-full">
          <p className="font-semibold">Mermaid Diagram Error:</p>
          <p className="text-sm">{error}</p>
          <pre className="mt-2 p-2 bg-red-50 text-xs text-red-600 overflow-auto rounded custom-scrollbar">
            {code}
          </pre>
        </div>
      ) : (
        // This div with class "mermaid" will contain the raw diagram code
        // and will be processed by mermaid.run()
        <div className="mermaid">{code}</div>
      )}
    </div>
  );
};

export default MermaidBlock; 