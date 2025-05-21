'use client';

import ReactMarkdown, { type Options, type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css'; // Or your preferred highlight.js theme
import { type Element } from 'hast';
import type { ReactNode } from 'react'; // Import ReactNode
import MermaidBlock from '@/components/custom/MermaidBlock'; // Import the new MermaidBlock component

interface MarkdownRendererProps {
  markdown: string;
  className?: string;
}

// Explicitly type the props for the custom code renderer
interface CodeComponentProps {
  node?: Element; // Made node optional to align with broader react-markdown types
  inline?: boolean; // This is what react-markdown passes
  className?: string;
  children?: ReactNode;
  [key: string]: any; // Allow other props that might be passed
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ markdown, className }) => {
  const components: Options['components'] = {
    h1: ({node, ...props}) => <h1 className="text-3xl font-bold my-4 border-b pb-2" {...props} />,
    h2: ({node, ...props}) => <h2 className="text-2xl font-semibold my-3 border-b pb-1" {...props} />,
    h3: ({node, ...props}) => <h3 className="text-xl font-semibold my-2" {...props} />,
    h4: ({node, ...props}) => <h4 className="text-lg font-semibold my-1" {...props} />,
    p: ({node, ...props}) => <p className="mb-4 leading-relaxed" {...props} />,
    a: ({node, ...props}) => <a className="text-primary hover:underline" {...props} />,
    ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4" {...props} />,
    ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4" {...props} />,
    li: ({node, ...props}) => <li className="mb-1" {...props} />,
    blockquote: ({node, ...props}) => <blockquote className="pl-4 italic border-l-4 border-muted-foreground/50 text-muted-foreground my-4" {...props} />,
    code: (props: CodeComponentProps) => {
      const { node, inline, className: propClassName, children, ...restProps } = props;
      if (!node) return null; // Guard against node being undefined

      const match = /language-(\w+)/.exec(propClassName || '');
      const lang = match && match[1];

      if (lang === 'mermaid') {
        const mermaidCode = typeof children === 'string' ? children.trim() : '';
        // Use the MermaidBlock component for mermaid code blocks
        return <MermaidBlock code={mermaidCode} />;
      }

      if (inline) {
        return <code className={`px-1 py-0.5 bg-muted text-muted-foreground rounded-sm text-sm ${propClassName || ''}`} {...restProps}>{children}</code>;
      }
      // For block code, rehype-highlight takes care of the <code> element within <pre>
      // The className from react-markdown (e.g., language-js) is passed to the <code> element by default.
      // rehype-highlight will use this to apply syntax highlighting classes.
      return <code className={`${propClassName || ''}`} {...restProps}>{children}</code>;
    },
    pre: ({node, children, ...props}) => {
      // node here would be the <pre> element itself.
      // children will be the <code> element processed by the custom code renderer above.
      return <pre className="bg-gray-900 p-4 rounded-md overflow-x-auto text-sm my-4 custom-scrollbar" {...props}>{children}</pre>;
    },
    table: ({node, ...props}) => <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 my-4 border dark:border-gray-700" {...props} />,
    thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
    tbody: ({node, ...props}) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
    tr: ({node, ...props}) => <tr className="hover:bg-gray-50 dark:hover:bg-gray-800" {...props} />,
    th: ({node, ...props}) => <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider border-b dark:border-gray-700" {...props} />,
    td: ({node, ...props}) => <td className="px-4 py-2 text-sm text-gray-700 dark:text-gray-200 border-b dark:border-gray-700" {...props} />,
  };

  return (
    // Removed prose utility classes from here to allow more granular control via components, 
    // but you can add them back if a base prose styling is desired before custom component styles.
    <div className={`markdown-content w-full ${className || ''}`}>
      <ReactMarkdown
        components={components as Components} // Cast to Components to satisfy stricter checks if necessary
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer; 