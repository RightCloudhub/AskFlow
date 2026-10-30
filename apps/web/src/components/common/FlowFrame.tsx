import { useEffect, useId, useRef, type ReactNode } from "react";
import { CheckOutlined } from "@ant-design/icons";
import "../../styles/form-flow.css";

type FlowFrameProps = {
  titles: string[];
  current: number;
  title?: string;
  description?: string;
  busy?: boolean;
  compact?: boolean;
  backDisabled?: boolean;
  active?: boolean;
  focusOnMount?: boolean;
  onBack: (index: number) => void;
  children: ReactNode;
};

export function FlowFrame(props: FlowFrameProps) {
  const { titles, current, busy, onBack, children } = props;
  const heading = useRef<HTMLHeadingElement>(null);
  const active = props.active !== false;
  const title = props.title ?? titles[current];
  const previous = useRef({ current, active: active && !props.focusOnMount, title });
  const titleId = useId();
  useEffect(() => {
    const changed = previous.current.current !== current || previous.current.title !== title;
    if (active && (changed || !previous.current.active)) heading.current?.focus();
    previous.current = { current, active, title };
  }, [current, active, title]);
  return <div className="af-flow-frame" role="group" aria-labelledby={titleId} aria-busy={busy}>
    {!props.compact && <nav aria-label="操作进度">
      <p className="af-flow-position" aria-live="polite" aria-atomic="true">
        <span>{titles[current]}</span><span>{current + 1} / {titles.length}</span>
      </p>
      <ol className="af-form-progress">{titles.map((title, index) => <li key={title}
        aria-current={current === index ? "step" : undefined} className={index < current ? "complete" : ""}>
        <button type="button" disabled={busy || props.backDisabled || index >= current} onClick={() => onBack(index)}
          aria-label={index < current ? `返回${title}` : title}>
          {index < current && <CheckOutlined aria-hidden="true" />}<span>{title}</span>
        </button>
      </li>)}</ol>
    </nav>}
    <h3 id={titleId} tabIndex={-1} ref={heading} className="af-form-step-title">{title}</h3>
    {props.description && <p className="af-flow-description">{props.description}</p>}
    {children}
  </div>;
}
