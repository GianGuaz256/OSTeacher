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
  const [svgContent, setSvgContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Initialize Mermaid once
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose', // Required for proper rendering
    });
  }, []);

  useEffect(() => {
    if (!code) {
      setSvgContent('');
      setError(null);
      setIsLoading(false);
      return;
    }

    const renderMermaid = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Generate a unique ID for this diagram
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        // Use mermaid.render to get the SVG string without DOM manipulation
        const { svg } = await mermaid.render(id, code);
        setSvgContent(svg);
      } catch (e: any) {
        console.error("Mermaid rendering error:", e);
        setError(e instanceof Error ? e.message : String(e));
        setSvgContent('');
      } finally {
        setIsLoading(false);
      }
    };

    renderMermaid();
  }, [code]);

  if (isLoading) {
    return (
      <div className="mermaid-diagram-container flex justify-center my-6">
        <div className="p-4 text-gray-500">Loading diagram...</div>
      </div>
    );
  }

  return (
    <div ref={mermaidDivRef} className="mermaid-diagram-container flex justify-center my-6">
      {error ? (
        <div className="mermaid-error p-4 my-2 bg-red-100 text-red-700 border border-red-400 rounded-md shadow w-full">
          <p className="font-semibold">Mermaid Diagram Error:</p>
          <p className="text-sm">{error}</p>
          <pre className="mt-2 p-2 bg-red-50 text-xs text-red-600 overflow-auto rounded custom-scrollbar">
            {code}
          </pre>
        </div>
      ) : svgContent ? (
        // Render the SVG content directly without letting Mermaid manipulate the DOM
        <div 
          className="mermaid-svg-container"
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      ) : null}
    </div>
  );
};

export default MermaidBlock; 