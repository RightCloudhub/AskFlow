import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CitationSource } from "../../api/types";
import { citationChildren } from "./CitationText";

type MarkdownBodyProps = { content: string; className?: string; sources?: CitationSource[] };

export function MarkdownBody({ content, className, sources = [] }: MarkdownBodyProps) {
  const cite = (children: React.ReactNode) => citationChildren(children, sources);
  return <div className={className ?? "af-md"}>
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
      p: ({ children }) => <p>{cite(children)}</p>,
      li: ({ children }) => <li>{cite(children)}</li>,
      strong: ({ children }) => <strong>{cite(children)}</strong>,
      em: ({ children }) => <em>{cite(children)}</em>,
      blockquote: ({ children }) => <blockquote>{cite(children)}</blockquote>,
      td: ({ children }) => <td>{cite(children)}</td>,
      th: ({ children }) => <th>{cite(children)}</th>,
      h1: ({ children }) => <h2>{cite(children)}</h2>,
      h2: ({ children }) => <h3>{cite(children)}</h3>,
      h3: ({ children }) => <h4>{cite(children)}</h4>,
      a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
    }}>{content}</ReactMarkdown>
  </div>;
}
